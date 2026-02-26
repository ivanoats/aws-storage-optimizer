from click.testing import CliRunner
from botocore.exceptions import ClientError

import aws_storage_optimizer.cli as cli_module


class DummyFactory:
    def s3(self):
        return object()

    def ec2(self):
        return object()

    def rds(self):
        return object()


class SuccessEC2Client:
    def delete_volume(self, VolumeId):
        return {"VolumeId": VolumeId}


class SuccessFactory:
    def s3(self):
        return object()

    def ec2(self):
        return SuccessEC2Client()

    def rds(self):
        return object()


class FailingEC2Client:
    def delete_volume(self, VolumeId):
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
    def s3(self):
        return object()

    def ec2(self):
        return FailingEC2Client()

    def rds(self):
        return object()


class FailingS3Client:
    def delete_object(self, Bucket, Key):
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
    def s3(self):
        return FailingS3Client()

    def ec2(self):
        return object()

    def rds(self):
        return object()


class FailingRDSClient:
    def modify_db_instance(self, DBInstanceIdentifier, DBInstanceClass, ApplyImmediately):
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
    def s3(self):
        return object()

    def ec2(self):
        return object()

    def rds(self):
        return FailingRDSClient()


def test_execute_dry_run_succeeds(monkeypatch):
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region: DummyFactory())

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


def test_execute_no_dry_run_requires_yes(monkeypatch):
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region: DummyFactory())

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
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region: SuccessFactory())

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
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region: FailingFactory())

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
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region: FailingS3Factory())

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
    monkeypatch.setattr(cli_module, "AWSClientFactory", lambda profile, region: FailingRDSFactory())

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
