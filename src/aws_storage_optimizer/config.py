from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class Thresholds:
    rds_cpu_underutilized_pct: float = 15.0
    rds_lookback_days: int = 7
    s3_stale_days: int = 90


@dataclass
class EstimationRates:
    ebs_gp3_per_gib_month_usd: float = 0.08


@dataclass
class AppConfig:
    thresholds: Thresholds
    rates: EstimationRates


def load_config() -> AppConfig:
    thresholds = Thresholds(
        rds_cpu_underutilized_pct=float(os.getenv("ASO_RDS_CPU_UNDERUTILIZED_PCT", "15")),
        rds_lookback_days=int(os.getenv("ASO_RDS_LOOKBACK_DAYS", "7")),
        s3_stale_days=int(os.getenv("ASO_S3_STALE_DAYS", "90")),
    )
    rates = EstimationRates(
        ebs_gp3_per_gib_month_usd=float(os.getenv("ASO_EBS_GP3_PER_GIB_MONTH_USD", "0.08"))
    )
    return AppConfig(thresholds=thresholds, rates=rates)
