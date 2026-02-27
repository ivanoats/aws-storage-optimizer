from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from aws_storage_optimizer.models import ActionResult
from aws_storage_optimizer.utils import has_protection_tag


RESOURCE_PROTECTED_MESSAGE = "Resource protected by tag"


def _is_protected_ebs_volume(ec2_client, volume_id: str, tag_key: str, tag_value: str) -> bool:
    response = ec2_client.describe_volumes(VolumeIds=[volume_id])
    volumes = response.get("Volumes", [])
    if not volumes:
        return False
    return has_protection_tag(volumes[0].get("Tags", []), tag_key, tag_value)


def _is_protected_s3_bucket(s3_client, bucket: str, tag_key: str, tag_value: str) -> bool:
    try:
        tagging = s3_client.get_bucket_tagging(Bucket=bucket)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"NoSuchTagSet", "NoSuchBucket"}:
            return False
        if error_code == "AccessDenied":
            return True
        raise
    return has_protection_tag(tagging.get("TagSet", []), tag_key, tag_value)


def _is_protected_rds_instance(rds_client, db_instance_id: str, tag_key: str, tag_value: str) -> bool:
    details = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
    instances = details.get("DBInstances", [])
    if not instances:
        return False
    db_arn = str(instances[0].get("DBInstanceArn", ""))
    if not db_arn:
        return False
    tags = rds_client.list_tags_for_resource(ResourceName=db_arn).get("TagList", [])
    return has_protection_tag(tags, tag_key, tag_value)


def _handle_delete_ebs_volume(
    action_type: str,
    resource_id: str,
    ec2_client,
    protection_tag_key: str,
    protection_tag_value: str,
) -> ActionResult:
    if _is_protected_ebs_volume(
        ec2_client,
        volume_id=resource_id,
        tag_key=protection_tag_key,
        tag_value=protection_tag_value,
    ):
        return ActionResult(action_type, resource_id, "skipped", RESOURCE_PROTECTED_MESSAGE)
    ec2_client.delete_volume(VolumeId=resource_id)
    return ActionResult(action_type, resource_id, "success", "EBS volume deleted")


def _handle_delete_s3_object(
    action_type: str,
    resource_id: str,
    s3_client,
    bucket: str | None,
    key: str | None,
    protection_tag_key: str,
    protection_tag_value: str,
) -> ActionResult:
    if not bucket or not key:
        return ActionResult(action_type, resource_id, "failed", "--bucket and --key are required")
    if _is_protected_s3_bucket(
        s3_client,
        bucket=bucket,
        tag_key=protection_tag_key,
        tag_value=protection_tag_value,
    ):
        return ActionResult(action_type, resource_id, "skipped", RESOURCE_PROTECTED_MESSAGE)
    s3_client.delete_object(Bucket=bucket, Key=key)
    return ActionResult(action_type, resource_id, "success", "S3 object deleted")


def _handle_resize_rds_instance(
    action_type: str,
    resource_id: str,
    rds_client,
    target_class: str | None,
    protection_tag_key: str,
    protection_tag_value: str,
) -> ActionResult:
    if not target_class:
        return ActionResult(action_type, resource_id, "failed", "--target-class is required")
    if _is_protected_rds_instance(
        rds_client,
        db_instance_id=resource_id,
        tag_key=protection_tag_key,
        tag_value=protection_tag_value,
    ):
        return ActionResult(action_type, resource_id, "skipped", RESOURCE_PROTECTED_MESSAGE)
    rds_client.modify_db_instance(
        DBInstanceIdentifier=resource_id,
        DBInstanceClass=target_class,
        ApplyImmediately=False,
    )
    return ActionResult(action_type, resource_id, "success", "RDS resize requested")


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

    handlers = {
        "delete-ebs-volume": lambda: _handle_delete_ebs_volume(
            action_type=action_type,
            resource_id=resource_id,
            ec2_client=ec2_client,
            protection_tag_key=protection_tag_key,
            protection_tag_value=protection_tag_value,
        ),
        "delete-s3-object": lambda: _handle_delete_s3_object(
            action_type=action_type,
            resource_id=resource_id,
            s3_client=s3_client,
            bucket=bucket,
            key=key,
            protection_tag_key=protection_tag_key,
            protection_tag_value=protection_tag_value,
        ),
        "resize-rds-instance": lambda: _handle_resize_rds_instance(
            action_type=action_type,
            resource_id=resource_id,
            rds_client=rds_client,
            target_class=target_class,
            protection_tag_key=protection_tag_key,
            protection_tag_value=protection_tag_value,
        ),
    }

    handler = handlers.get(action_type)
    if handler is None:
        return ActionResult(action_type, resource_id, "failed", "Unsupported action type")

    try:
        return handler()

    except (BotoCoreError, ClientError) as exc:
        return ActionResult(action_type, resource_id, "failed", str(exc))
