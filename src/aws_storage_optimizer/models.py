from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Finding:
    service: str
    resource_id: str
    region: str | None
    recommendation: str
    estimated_monthly_savings_usd: float
    risk_level: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    generated_at: str
    findings: list[Finding]

    @classmethod
    def empty(cls) -> "AnalysisResult":
        return cls(generated_at=datetime.now(timezone.utc).isoformat(), findings=[])

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass
class ActionResult:
    action_type: str
    resource_id: str
    status: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
