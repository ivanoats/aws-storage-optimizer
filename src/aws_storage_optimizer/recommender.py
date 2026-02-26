from __future__ import annotations

from aws_storage_optimizer.models import Finding


RISK_RANK = {"low": 0, "medium": 1, "high": 2}


def prioritize_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda item: (
            -item.estimated_monthly_savings_usd,
            RISK_RANK.get(item.risk_level, 1),
            item.service,
        ),
    )
