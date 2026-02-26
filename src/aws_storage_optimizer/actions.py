from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from aws_storage_optimizer.models import ActionResult


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
            ec2_client.delete_volume(VolumeId=resource_id)
            return ActionResult(action_type, resource_id, "success", "EBS volume deleted")

        if action_type == "delete-s3-object":
            if not bucket or not key:
                return ActionResult(action_type, resource_id, "failed", "--bucket and --key are required")
            s3_client.delete_object(Bucket=bucket, Key=key)
            return ActionResult(action_type, resource_id, "success", "S3 object deleted")

        if action_type == "resize-rds-instance":
            if not target_class:
                return ActionResult(action_type, resource_id, "failed", "--target-class is required")
            rds_client.modify_db_instance(
                DBInstanceIdentifier=resource_id,
                DBInstanceClass=target_class,
                ApplyImmediately=False,
            )
            return ActionResult(action_type, resource_id, "success", "RDS resize requested")

        return ActionResult(action_type, resource_id, "failed", "Unsupported action type")

    except (BotoCoreError, ClientError) as exc:
        return ActionResult(action_type, resource_id, "failed", str(exc))
