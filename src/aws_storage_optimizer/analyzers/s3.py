from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from aws_storage_optimizer.config import AppConfig
from aws_storage_optimizer.estimation import estimate_s3_monthly_savings
from aws_storage_optimizer.models import Finding
from aws_storage_optimizer.utils import has_protection_tag


def _is_protected_bucket(s3_client, bucket_name: str, key: str, value: str) -> bool:
    try:
        tagging = s3_client.get_bucket_tagging(Bucket=bucket_name)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"NoSuchTagSet", "NoSuchBucket"}:
            return False
        return True
    except BotoCoreError:
        return True

    return has_protection_tag(tagging.get("TagSet", []), key, value)


def analyze_s3(s3_client, config: AppConfig, top_n: int) -> list[Finding]:
    findings: list[Finding] = []
    try:
        buckets = s3_client.list_buckets().get("Buckets", [])
    except (BotoCoreError, ClientError):
        return findings

    bucket_sizes: list[tuple[str, int]] = []
    for bucket in buckets:
        bucket_name = bucket.get("Name")
        if not bucket_name:
            continue
        if _is_protected_bucket(
            s3_client,
            bucket_name=bucket_name,
            key=config.protection.tag_key,
            value=config.protection.tag_value,
        ):
            continue

        total_size = 0
        continuation_token = None
        page_count = 0
        while True:
            kwargs = {"Bucket": bucket_name, "MaxKeys": 1000}
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            try:
                page = s3_client.list_objects_v2(**kwargs)
            except (BotoCoreError, ClientError):
                break

            for obj in page.get("Contents", []):
                total_size += int(obj.get("Size", 0))

            continuation_token = page.get("NextContinuationToken")
            page_count += 1
            if not continuation_token or page_count >= 5:
                break

        bucket_sizes.append((bucket_name, total_size))

    bucket_sizes.sort(key=lambda item: item[1], reverse=True)
    for bucket_name, size_bytes in bucket_sizes[:top_n]:
        size_gib = round(size_bytes / (1024**3), 2)
        estimated_savings = estimate_s3_monthly_savings(size_gib=size_gib, config=config)
        findings.append(
            Finding(
                service="s3",
                resource_id=bucket_name,
                region=None,
                recommendation="Review lifecycle policy, archive infrequently accessed objects",
                estimated_monthly_savings_usd=estimated_savings,
                risk_level="medium",
                details={
                    "approx_size_gib": size_gib,
                    "sample_limit_note": "Size estimated from up to 5 pages of objects",
                    "stale_days_threshold": config.thresholds.s3_stale_days,
                    "estimated_optimization_ratio": config.rates.s3_estimated_optimization_ratio,
                },
            )
        )

    return findings
