from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from aws_storage_optimizer.config import AppConfig
from aws_storage_optimizer.models import Finding
from aws_storage_optimizer.utils import has_protection_tag


def analyze_ebs(ec2_client, config: AppConfig, region: str | None) -> list[Finding]:
    findings: list[Finding] = []
    try:
        response = ec2_client.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
    except (BotoCoreError, ClientError):
        return findings

    for volume in response.get("Volumes", []):
        tags = volume.get("Tags", [])
        if has_protection_tag(tags, config.protection.tag_key, config.protection.tag_value):
            continue

        size_gib = int(volume.get("Size", 0))
        volume_type = str(volume.get("VolumeType", "gp3"))
        estimated_savings = round(size_gib * config.rates.ebs_gp3_per_gib_month_usd, 2)
        findings.append(
            Finding(
                service="ebs",
                resource_id=str(volume.get("VolumeId")),
                region=region,
                recommendation="Delete unattached EBS volume",
                estimated_monthly_savings_usd=estimated_savings,
                risk_level="low",
                details={"size_gib": size_gib, "volume_type": volume_type},
            )
        )

    return findings
