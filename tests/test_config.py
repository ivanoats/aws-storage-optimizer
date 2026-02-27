from aws_storage_optimizer.config import load_config


def test_load_config_uses_profile_specific_override(monkeypatch):
    monkeypatch.setenv("ASO_RDS_CPU_UNDERUTILIZED_PCT", "15")
    monkeypatch.setenv("ASO_PROFILE_FINOPS_PROD_RDS_CPU_UNDERUTILIZED_PCT", "6")

    config = load_config(profile="finops-prod")

    assert config.thresholds.rds_cpu_underutilized_pct == 6.0


def test_load_config_falls_back_to_global_override(monkeypatch):
    monkeypatch.setenv("ASO_S3_STALE_DAYS", "120")

    config = load_config(profile="dev")

    assert config.thresholds.s3_stale_days == 120


def test_load_config_reads_region_from_aso_region(monkeypatch):
    monkeypatch.setenv("ASO_REGION", "eu-west-1")

    config = load_config()

    assert config.region == "eu-west-1"


def test_load_config_region_defaults_to_us_west_2(monkeypatch):
    monkeypatch.delenv("ASO_REGION", raising=False)

    config = load_config()

    assert config.region == "us-west-2"
