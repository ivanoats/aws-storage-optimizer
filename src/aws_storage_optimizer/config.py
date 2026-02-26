from __future__ import annotations

from dataclasses import dataclass
import os
import re


@dataclass
class Thresholds:
    rds_cpu_underutilized_pct: float = 15.0
    rds_lookback_days: int = 7
    s3_stale_days: int = 90


@dataclass
class EstimationRates:
    ebs_gp3_per_gib_month_usd: float = 0.08
    s3_standard_per_gib_month_usd: float = 0.023
    s3_estimated_optimization_ratio: float = 0.3
    rds_default_monthly_cost_usd: float = 120.0
    rds_estimated_downsize_ratio: float = 0.25


@dataclass
class AppConfig:
    thresholds: Thresholds
    rates: EstimationRates


def _profile_env_key(profile: str | None, name: str) -> str | None:
    if not profile:
        return None
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", profile).upper()
    return f"ASO_PROFILE_{normalized}_{name}"


def _get_env(name: str, default: str, profile: str | None = None) -> str:
    profile_key = _profile_env_key(profile, name)
    if profile_key and (value := os.getenv(profile_key)) is not None:
        return value
    return os.getenv(f"ASO_{name}", default)


def load_config(profile: str | None = None) -> AppConfig:
    thresholds = Thresholds(
        rds_cpu_underutilized_pct=float(_get_env("RDS_CPU_UNDERUTILIZED_PCT", "15", profile)),
        rds_lookback_days=int(_get_env("RDS_LOOKBACK_DAYS", "7", profile)),
        s3_stale_days=int(_get_env("S3_STALE_DAYS", "90", profile)),
    )
    rates = EstimationRates(
        ebs_gp3_per_gib_month_usd=float(_get_env("EBS_GP3_PER_GIB_MONTH_USD", "0.08", profile)),
        s3_standard_per_gib_month_usd=float(
            _get_env("S3_STANDARD_PER_GIB_MONTH_USD", "0.023", profile)
        ),
        s3_estimated_optimization_ratio=float(
            _get_env("S3_ESTIMATED_OPTIMIZATION_RATIO", "0.3", profile)
        ),
        rds_default_monthly_cost_usd=float(_get_env("RDS_DEFAULT_MONTHLY_COST_USD", "120", profile)),
        rds_estimated_downsize_ratio=float(_get_env("RDS_ESTIMATED_DOWNSIZE_RATIO", "0.25", profile)),
    )
    return AppConfig(thresholds=thresholds, rates=rates)
