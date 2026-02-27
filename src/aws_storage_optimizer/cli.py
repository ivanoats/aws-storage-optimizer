from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import click

from aws_storage_optimizer.actions import execute_action
from aws_storage_optimizer.analyzers import analyze_ebs, analyze_rds, analyze_s3
from aws_storage_optimizer.aws_clients import AWSClientFactory
from aws_storage_optimizer.config import load_config
from aws_storage_optimizer.models import AnalysisResult
from aws_storage_optimizer.recommender import prioritize_findings
from aws_storage_optimizer.reporting import (
    load_analysis,
    print_analysis_json,
    print_analysis_table,
    save_analysis,
)


def _append_action_log(action_result, log_path: str) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **action_result.to_dict(),
    }
    target = Path(log_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload) + "\n")


@click.group()
@click.option("--profile", default=None, help="AWS profile to use")
@click.option("--region", default=None, help="AWS region override")
@click.pass_context
def cli(ctx: click.Context, profile: str | None, region: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["region"] = region
    ctx.obj["config"] = load_config(profile=profile)


@cli.command()
@click.option(
    "--services",
    type=click.Choice(["s3", "ebs", "rds"]),
    multiple=True,
    help="Services to analyze. Default analyzes all.",
)
@click.option("--output-format", type=click.Choice(["table", "json"]), default="table")
@click.option("--top-n-s3", type=int, default=10, show_default=True)
@click.option("--save", "save_path", default=None, help="Optional path to save findings JSON")
@click.option("--rds-cpu-threshold", type=float, default=None)
@click.option("--rds-lookback-days", type=int, default=None)
@click.option("--s3-stale-days", type=int, default=None)
@click.pass_context
def analyze(
    ctx: click.Context,
    services: tuple[str, ...],
    output_format: str,
    top_n_s3: int,
    save_path: str | None,
    rds_cpu_threshold: float | None,
    rds_lookback_days: int | None,
    s3_stale_days: int | None,
) -> None:
    profile = ctx.obj["profile"]
    region = ctx.obj["region"]
    config = ctx.obj["config"]

    if rds_cpu_threshold is not None:
        config.thresholds.rds_cpu_underutilized_pct = rds_cpu_threshold
    if rds_lookback_days is not None:
        config.thresholds.rds_lookback_days = rds_lookback_days
    if s3_stale_days is not None:
        config.thresholds.s3_stale_days = s3_stale_days

    selected = set(services) if services else {"s3", "ebs", "rds"}
    client_factory = AWSClientFactory(profile=profile, region=region, config=config)

    findings = []
    if "s3" in selected:
        findings.extend(analyze_s3(client_factory.s3(), config=config, top_n=top_n_s3))
    if "ebs" in selected:
        findings.extend(analyze_ebs(client_factory.ec2(), config=config, region=region))
    if "rds" in selected:
        findings.extend(
            analyze_rds(
                rds_client=client_factory.rds(),
                cloudwatch_client=client_factory.cloudwatch(),
                config=config,
                region=region,
            )
        )

    ordered_findings = prioritize_findings(findings)
    result = AnalysisResult(
        generated_at=datetime.now(timezone.utc).isoformat(),
        findings=ordered_findings,
    )

    if output_format == "json":
        print_analysis_json(result)
    else:
        print_analysis_table(result)

    if save_path:
        save_analysis(result, save_path)
        click.echo(f"Saved findings to {save_path}")


cli.add_command(analyze, name="analyse")


@cli.command()
@click.option("--input", "input_path", required=True, help="Path to findings JSON")
@click.option("--output-format", type=click.Choice(["table", "json"]), default="table")
def report(input_path: str, output_format: str) -> None:
    result = load_analysis(input_path)
    if output_format == "json":
        print_analysis_json(result)
    else:
        print_analysis_table(result)


@cli.command()
@click.option(
    "--action-type",
    type=click.Choice(["delete-ebs-volume", "delete-s3-object", "resize-rds-instance"]),
    required=True,
)
@click.option("--resource-id", required=True)
@click.option("--bucket", default=None)
@click.option("--key", default=None)
@click.option("--target-class", default=None)
@click.option("--dry-run/--no-dry-run", default=True, show_default=True)
@click.option("--yes", is_flag=True, default=False, help="Required for non-dry-run mutations")
@click.option(
    "--log-path",
    default="artifacts/action-results.jsonl",
    show_default=True,
    help="Path for append-only action result logs",
)
@click.pass_context
def execute(
    ctx: click.Context,
    action_type: str,
    resource_id: str,
    bucket: str | None,
    key: str | None,
    target_class: str | None,
    dry_run: bool,
    yes: bool,
    log_path: str,
) -> None:
    profile = ctx.obj["profile"]
    region = ctx.obj["region"]

    if action_type == "delete-s3-object" and (not bucket or not key):
        raise click.ClickException("--bucket and --key are required for delete-s3-object")

    if action_type == "resize-rds-instance" and not target_class:
        raise click.ClickException("--target-class is required for resize-rds-instance")

    config = ctx.obj["config"]
    clients = AWSClientFactory(profile=profile, region=region, config=config)

    result = execute_action(
        action_type=action_type,
        resource_id=resource_id,
        dry_run=dry_run,
        yes=yes,
        ec2_client=clients.ec2(),
        s3_client=clients.s3(),
        rds_client=clients.rds(),
        bucket=bucket,
        key=key,
        target_class=target_class,
        protection_tag_key=config.protection.tag_key,
        protection_tag_value=config.protection.tag_value,
    )
    _append_action_log(result, log_path)
    click.echo(f"[{result.status}] {result.action_type} {result.resource_id}: {result.message}")
    if result.status == "failed":
        raise click.ClickException(result.message)


if __name__ == "__main__":
    cli()
