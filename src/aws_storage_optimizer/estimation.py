from __future__ import annotations

from aws_storage_optimizer.config import AppConfig

RDS_CLASS_MONTHLY_BASELINE_USD = {
    "db.t3.micro": 13.0,
    "db.t3.small": 26.0,
    "db.t3.medium": 52.0,
    "db.t4g.micro": 12.0,
    "db.t4g.small": 24.0,
    "db.t4g.medium": 48.0,
    "db.m5.large": 140.0,
    "db.m5.xlarge": 280.0,
}


def estimate_s3_monthly_savings(size_gib: float, config: AppConfig) -> float:
    estimate = (
        size_gib
        * config.rates.s3_standard_per_gib_month_usd
        * config.rates.s3_estimated_optimization_ratio
    )
    return round(max(estimate, 0.0), 2)


def estimate_rds_monthly_savings(db_instance_class: str | None, config: AppConfig) -> float:
    baseline = RDS_CLASS_MONTHLY_BASELINE_USD.get(
        db_instance_class,
        config.rates.rds_default_monthly_cost_usd,
    )
    estimate = baseline * config.rates.rds_estimated_downsize_ratio
    return round(max(estimate, 0.0), 2)
