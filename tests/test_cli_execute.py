import json

from botocore.exceptions import ClientError
from click.testing import CliRunner

import aws_storage_optimizer.cli as cli_module


class DummyFactory:
    @staticmethod
    def s3():
        return object()

    @staticmethod
    def ec2():
        return object()

    @staticmethod
    def rds():
        return object()


class SuccessEC2Client:
    @staticmethod
    def describe_volumes(**kwargs):
        return {"Volumes": [{"VolumeId": kwargs.get("VolumeIds", [""])[0], "Tags": []}]}

    @staticmethod
    def delete_volume(**kwargs):
        volume_id = kwargs.get("VolumeId")
        return {"VolumeId": volume_id}


class SuccessFactory:
    @staticmethod
    def s3():
        return object()

    @staticmethod
    def ec2():
        return SuccessEC2Client()

    @staticmethod
    def rds():
        return object()


class FailingEC2Client:
    @staticmethod
    def describe_volumes(**kwargs):
        return {"Volumes": [{"VolumeId": kwargs.get("VolumeIds", [""])[0], "Tags": []}]}

    @staticmethod
    def delete_volume(**kwargs):
        raise ClientError(
            error_response={
                "Error": {
                    "Code": "UnauthorizedOperation",
                    "Message": "You are not authorized to perform this operation.",
                }
            },
            operation_name="DeleteVolume",
        )


class FailingFactory:
    @staticmethod
    def s3():
        return object()

    @staticmethod
    def ec2():
        return FailingEC2Client()

    @staticmethod
    def rds():
        return object()


class FailingS3Client:
    @staticmethod
    def get_bucket_tagging(**_kwargs):
        raise ClientError(
            error_response={"Error": {"Code": "NoSuchTagSet", "Message": "No tags"}},
            operation_name="GetBucketTagging",
        )

    @staticmethod
    def delete_object(**kwargs):
        raise ClientError(
            error_response={
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "Access denied for S3 delete.",
                }
            },
            operation_name="DeleteObject",
        )


class FailingS3Factory:
    @staticmethod
    def s3():
        return FailingS3Client()

    @staticmethod
    def ec2():
        return object()

    @staticmethod
    def rds():
        return object()


class FailingRDSClient:
    @staticmethod
    def describe_db_instances(**kwargs):
        db_instance_identifier = kwargs.get("DBInstanceIdentifier", "db-instance-1")
        return {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": db_instance_identifier,
                    "DBInstanceArn": f"arn:aws:rds:us-east-1:123456789012:db:{db_instance_identifier}",
                }
            ]
        }

    @staticmethod
    def list_tags_for_resource(**_kwargs):
        return {"TagList": []}

    @staticmethod
    def modify_db_instance(**kwargs):
        raise ClientError(
            error_response={
                "Error": {
                    "Code": "InvalidParameterCombination",
                    "Message": "Invalid DB instance class for this engine.",
                }
            },
            operation_name="ModifyDBInstance",
        )


class FailingRDSFactory:
    @staticmethod
    def s3():
        return object()

    @staticmethod
    def ec2():
        return object()

    @staticmethod
    def rds():
        return FailingRDSClient()


def test_execute_dry_run_succeeds(monkeypatch):
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region, config=None: DummyFactory())

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "delete-ebs-volume",
            "--resource-id",
            "vol-0123456789abcdef0",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "No AWS changes applied" in result.output


def test_execute_delete_s3_object_requires_bucket_and_key(monkeypatch):
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region, config=None: DummyFactory())

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "delete-s3-object",
            "--resource-id",
            "s3://example-bucket/path/to/file.txt",
            "--dry-run",
        ],
    )

    assert result.exit_code != 0
    assert "--bucket and --key are required" in result.output


def test_execute_dry_run_writes_action_log(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region, config=None: DummyFactory())

    runner = CliRunner()
    log_path = tmp_path / "action-results.jsonl"
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "delete-ebs-volume",
            "--resource-id",
            "vol-0123456789abcdef0",
            "--dry-run",
            "--log-path",
            str(log_path),
        ],
    )

    assert result.exit_code == 0
    assert log_path.exists()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["status"] == "dry-run"
    assert payload["action_type"] == "delete-ebs-volume"


def test_execute_no_dry_run_requires_yes(monkeypatch):
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region, config=None: DummyFactory())

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "delete-ebs-volume",
            "--resource-id",
            "vol-0123456789abcdef0",
            "--no-dry-run",
        ],
    )

    assert result.exit_code != 0
    assert "without --yes" in result.output


def test_execute_no_dry_run_with_yes_succeeds(monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "AWSClientFactory",
        lambda profile, region, config=None: SuccessFactory(),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "delete-ebs-volume",
            "--resource-id",
            "vol-0123456789abcdef0",
            "--no-dry-run",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "[success]" in result.output
    assert "EBS volume deleted" in result.output


def test_execute_no_dry_run_with_yes_handles_aws_error(monkeypatch):
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region, config=None: FailingFactory())

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "delete-ebs-volume",
            "--resource-id",
            "vol-0123456789abcdef0",
            "--no-dry-run",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "[failed]" in result.output
    assert "UnauthorizedOperation" in result.output


def test_execute_delete_s3_object_handles_aws_error(monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "AWSClientFactory",
        lambda profile, region, config=None: FailingS3Factory(),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "delete-s3-object",
            "--resource-id",
            "s3://example-bucket/path/to/file.txt",
            "--bucket",
            "example-bucket",
            "--key",
            "path/to/file.txt",
            "--no-dry-run",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "[failed]" in result.output
    assert "AccessDenied" in result.output


def test_execute_resize_rds_instance_handles_aws_error(monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "AWSClientFactory",
        lambda profile, region, config=None: FailingRDSFactory(),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "execute",
            "--action-type",
            "resize-rds-instance",
            "--resource-id",
            "db-instance-1",
            "--target-class",
            "db.t3.micro",
            "--no-dry-run",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "[failed]" in result.output
    assert "InvalidParameterCombination" in result.output
