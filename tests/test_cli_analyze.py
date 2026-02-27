import json

from click.testing import CliRunner

import aws_storage_optimizer.cli as cli_module
from aws_storage_optimizer.models import Finding


class DummyFactory:
    @staticmethod
    def s3():
        return object()

    @staticmethod
    def ec2():
        return object()

    @staticmethod
    def rds():
        return object()

    @staticmethod
    def cloudwatch():
        return object()


def test_analyze_json_output_for_s3(monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "AWSClientFactory",
        lambda profile, region, config=None: DummyFactory(),
    )
    monkeypatch.setattr(
        cli_module,
        "analyze_s3",
        lambda s3_client, config, top_n: [
            Finding(
                service="s3",
                resource_id="example-bucket",
                region=None,
                recommendation="Review lifecycle policy",
                estimated_monthly_savings_usd=0.0,
                risk_level="medium",
                details={"approx_size_gib": 12.5},
            )
        ],
    )
    monkeypatch.setattr(cli_module, "analyze_ebs", lambda ec2_client, config, region: [])
    monkeypatch.setattr(
        cli_module,
        "analyze_rds",
        lambda rds_client, cloudwatch_client, config, region: [],
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        ["analyze", "--services", "s3", "--output-format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["findings"][0]["service"] == "s3"
    assert payload["findings"][0]["resource_id"] == "example-bucket"


def test_analyse_is_alias_for_analyze(monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "AWSClientFactory",
        lambda profile, region, config=None: DummyFactory(),
    )
    monkeypatch.setattr(
        cli_module,
        "analyze_s3",
        lambda s3_client, config, top_n: [
            Finding(
                service="s3",
                resource_id="example-bucket",
                region=None,
                recommendation="Review lifecycle policy",
                estimated_monthly_savings_usd=0.0,
                risk_level="medium",
                details={"approx_size_gib": 12.5},
            )
        ],
    )
def test_analyze_uses_aso_region_env_var(monkeypatch):
    monkeypatch.setenv("ASO_REGION", "ap-southeast-1")

    captured = {}

    def fake_factory(profile, region, config=None):
        captured["region"] = region
        return DummyFactory()

    monkeypatch.setattr(cli_module, "AWSClientFactory", fake_factory)
    monkeypatch.setattr(cli_module, "analyze_s3", lambda s3_client, config, top_n: [])
    monkeypatch.setattr(cli_module, "analyze_ebs", lambda ec2_client, config, region: [])
    monkeypatch.setattr(
        cli_module,
        "analyze_rds",
        lambda rds_client, cloudwatch_client, config, region: [],
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        ["analyze", "--services", "s3", "--output-format", "json"],
    )

    assert result.exit_code == 0
    assert captured["region"] == "ap-southeast-1"


def test_analyze_cli_region_flag_overrides_aso_region_env_var(monkeypatch):
    monkeypatch.setenv("ASO_REGION", "ap-southeast-1")

    captured = {}

    def fake_factory(profile, region, config=None):
        captured["region"] = region
        return DummyFactory()

    monkeypatch.setattr(cli_module, "AWSClientFactory", fake_factory)
    monkeypatch.setattr(cli_module, "analyze_s3", lambda s3_client, config, top_n: [])
    monkeypatch.setattr(cli_module, "analyze_ebs", lambda ec2_client, config, region: [])
    monkeypatch.setattr(
        cli_module,
        "analyze_rds",
        lambda rds_client, cloudwatch_client, config, region: [],
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        ["analyse", "--services", "s3", "--output-format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["findings"][0]["service"] == "s3"
    assert payload["findings"][0]["resource_id"] == "example-bucket"
        ["--region", "us-west-2", "analyze", "--services", "s3", "--output-format", "json"],
    )

    assert result.exit_code == 0
    assert captured["region"] == "us-west-2"
