from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from aws_storage_optimizer.models import AnalysisResult


def print_analysis_table(result: AnalysisResult) -> None:
    console = Console()
    table = Table(title="AWS Storage Optimization Findings")
    table.add_column("Service")
    table.add_column("Resource")
    table.add_column("Region")
    table.add_column("Recommendation")
    table.add_column("Est. $/mo", justify="right")
    table.add_column("Risk")

    for finding in result.findings:
        table.add_row(
            finding.service,
            finding.resource_id,
            finding.region or "-",
            finding.recommendation,
            f"{finding.estimated_monthly_savings_usd:.2f}",
            finding.risk_level,
        )

    console.print(table)


def print_analysis_json(result: AnalysisResult) -> None:
    print(json.dumps(result.to_dict(), indent=2))


def save_analysis(result: AnalysisResult, path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def load_analysis(path: str) -> AnalysisResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    generated_at = payload.get("generated_at", "")
    findings = payload.get("findings", [])

    from aws_storage_optimizer.models import Finding

    parsed_findings = [
        Finding(
            service=item.get("service", "unknown"),
            resource_id=item.get("resource_id", "unknown"),
            region=item.get("region"),
            recommendation=item.get("recommendation", ""),
            estimated_monthly_savings_usd=float(item.get("estimated_monthly_savings_usd", 0.0)),
            risk_level=item.get("risk_level", "medium"),
            details=item.get("details", {}),
        )
        for item in findings
    ]

    return AnalysisResult(generated_at=generated_at, findings=parsed_findings)
