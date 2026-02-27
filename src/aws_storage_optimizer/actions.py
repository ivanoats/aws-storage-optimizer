from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from aws_storage_optimizer.models import ActionResult


def _has_protection_tag(tags: list[dict], tag_key: str, tag_value: str) -> bool:
    expected_value = tag_value.strip().lower()
    for tag in tags:
        if str(tag.get("Key", "")) == tag_key and str(tag.get("Value", "")).strip().lower() == expected_value:
            return True
    return False


def _is_protected_ebs_volume(ec2_client, volume_id: str, tag_key: str, tag_value: str) -> bool:
    response = ec2_client.describe_volumes(VolumeIds=[volume_id])
    volumes = response.get("Volumes", [])
    if not volumes:
        return False
    return _has_protection_tag(volumes[0].get("Tags", []), tag_key, tag_value)


def _is_protected_s3_bucket(s3_client, bucket: str, tag_key: str, tag_value: str) -> bool:
    try:
        tagging = s3_client.get_bucket_tagging(Bucket=bucket)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"NoSuchTagSet", "NoSuchBucket", "AccessDenied"}:
            return False
        raise
    return _has_protection_tag(tagging.get("TagSet", []), tag_key, tag_value)


def _is_protected_rds_instance(rds_client, db_instance_id: str, tag_key: str, tag_value: str) -> bool:
    details = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
    instances = details.get("DBInstances", [])
    if not instances:
        return False
    db_arn = str(instances[0].get("DBInstanceArn", ""))
    if not db_arn:
        return False
    tags = rds_client.list_tags_for_resource(ResourceName=db_arn).get("TagList", [])
    return _has_protection_tag(tags, tag_key, tag_value)


def execute_action(
    action_type: str,
    resource_id: str,
    dry_run: bool,
    yes: bool,
    ec2_client,
    s3_client,
    rds_client,
    bucket: str | None = None,
    key: str | None = None,
    target_class: str | None = None,
    protection_tag_key: str = "DoNotTouch",
    protection_tag_value: str = "true",
) -> ActionResult:
    if not dry_run and not yes:
        return ActionResult(
            action_type=action_type,
            resource_id=resource_id,
            status="failed",
            message="Refusing to execute without --yes when --no-dry-run is used",
        )

    if dry_run:
        return ActionResult(
            action_type=action_type,
            resource_id=resource_id,
            status="dry-run",
            message="Dry-run only. No AWS changes applied.",
        )

    try:
        if action_type == "delete-ebs-volume":
            if _is_protected_ebs_volume(
                ec2_client,
                volume_id=resource_id,
                tag_key=protection_tag_key,
                tag_value=protection_tag_value,
            ):
                return ActionResult(action_type, resource_id, "skipped", "Resource protected by tag")
            ec2_client.delete_volume(VolumeId=resource_id)
            return ActionResult(action_type, resource_id, "success", "EBS volume deleted")

        if action_type == "delete-s3-object":
            if not bucket or not key:
                return ActionResult(action_type, resource_id, "failed", "--bucket and --key are required")
            if _is_protected_s3_bucket(
                s3_client,
                bucket=bucket,
                tag_key=protection_tag_key,
                tag_value=protection_tag_value,
            ):
                return ActionResult(action_type, resource_id, "skipped", "Resource protected by tag")
            s3_client.delete_object(Bucket=bucket, Key=key)
            return ActionResult(action_type, resource_id, "success", "S3 object deleted")

        if action_type == "resize-rds-instance":
            if not target_class:
                return ActionResult(action_type, resource_id, "failed", "--target-class is required")
            if _is_protected_rds_instance(
                rds_client,
                db_instance_id=resource_id,
                tag_key=protection_tag_key,
                tag_value=protection_tag_value,
            ):
                return ActionResult(action_type, resource_id, "skipped", "Resource protected by tag")
            rds_client.modify_db_instance(
                DBInstanceIdentifier=resource_id,
                DBInstanceClass=target_class,
                ApplyImmediately=False,
            )
            return ActionResult(action_type, resource_id, "success", "RDS resize requested")

        return ActionResult(action_type, resource_id, "failed", "Unsupported action type")

    except (BotoCoreError, ClientError) as exc:
        return ActionResult(action_type, resource_id, "failed", str(exc))
