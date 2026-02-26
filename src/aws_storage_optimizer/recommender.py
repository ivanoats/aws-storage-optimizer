from __future__ import annotations

from aws_storage_optimizer.models import Finding


RISK_MULTIPLIER = {"low": 1.0, "medium": 0.85, "high": 0.7}
SERVICE_MULTIPLIER = {"ebs": 1.0, "s3": 0.95, "rds": 0.9}


def _utilization_bonus(finding: Finding) -> float:
    avg_cpu = finding.details.get("avg_cpu_pct")
    if avg_cpu is None:
        return 1.0
    try:
        cpu_pct = float(avg_cpu)
    except (TypeError, ValueError):
        return 1.0
    return max(0.6, min(1.2, (100.0 - cpu_pct) / 100.0 + 0.2))


def _priority_score(finding: Finding) -> float:
    savings_component = max(finding.estimated_monthly_savings_usd, 0.0)
    risk_component = RISK_MULTIPLIER.get(finding.risk_level, 0.85)
    service_component = SERVICE_MULTIPLIER.get(finding.service, 0.9)
    usage_component = _utilization_bonus(finding)
    return round(savings_component * risk_component * service_component * usage_component, 4)


def prioritize_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda item: (
            -_priority_score(item),
            -item.estimated_monthly_savings_usd,
            item.service,
        ),
    )
