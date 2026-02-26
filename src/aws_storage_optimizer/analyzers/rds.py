from __future__ import annotations

from datetime import datetime, timedelta, timezone

from botocore.exceptions import BotoCoreError, ClientError

from aws_storage_optimizer.config import AppConfig
from aws_storage_optimizer.estimation import estimate_rds_monthly_savings
from aws_storage_optimizer.models import Finding


def _avg_cpu(cloudwatch_client, db_instance_identifier: str, lookback_days: int) -> float | None:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=lookback_days)
    try:
        metrics = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_instance_identifier}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=["Average"],
        )
    except (BotoCoreError, ClientError):
        return None

    datapoints = metrics.get("Datapoints", [])
    if not datapoints:
        return None
    values = [float(point.get("Average", 0.0)) for point in datapoints]
    return sum(values) / len(values)


def analyze_rds(rds_client, cloudwatch_client, config: AppConfig, region: str | None) -> list[Finding]:
    findings: list[Finding] = []
    try:
        response = rds_client.describe_db_instances()
    except (BotoCoreError, ClientError):
        return findings

    for instance in response.get("DBInstances", []):
        db_identifier = str(instance.get("DBInstanceIdentifier"))
        avg_cpu = _avg_cpu(
            cloudwatch_client=cloudwatch_client,
            db_instance_identifier=db_identifier,
            lookback_days=config.thresholds.rds_lookback_days,
        )
        if avg_cpu is None:
            continue

        if avg_cpu < config.thresholds.rds_cpu_underutilized_pct:
            db_instance_class = instance.get("DBInstanceClass")
            estimated_savings = estimate_rds_monthly_savings(
                db_instance_class=str(db_instance_class),
                config=config,
            )
            findings.append(
                Finding(
                    service="rds",
                    resource_id=db_identifier,
                    region=region,
                    recommendation="Consider downsizing DB instance class after workload validation",
                    estimated_monthly_savings_usd=estimated_savings,
                    risk_level="medium",
                    details={
                        "db_instance_class": db_instance_class,
                        "avg_cpu_pct": round(avg_cpu, 2),
                        "lookback_days": config.thresholds.rds_lookback_days,
                        "estimated_downsize_ratio": config.rates.rds_estimated_downsize_ratio,
                    },
                )
            )

    return findings
