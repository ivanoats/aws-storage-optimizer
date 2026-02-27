from botocore.exceptions import ClientError

from aws_storage_optimizer.actions import execute_action
from aws_storage_optimizer.analyzers.ebs import analyze_ebs
from aws_storage_optimizer.analyzers.rds import analyze_rds
from aws_storage_optimizer.analyzers.s3 import analyze_s3
from aws_storage_optimizer.config import load_config


class ProtectedEC2Client:
    @staticmethod
    def describe_volumes(**kwargs):
        volume_ids = kwargs.get("VolumeIds")
        if volume_ids:
            return {
                "Volumes": [
                    {
                        "VolumeId": volume_ids[0],
                        "Tags": [{"Key": "DoNotTouch", "Value": "true"}],
                    }
                ]
            }
        return {
            "Volumes": [
                {
                    "VolumeId": "vol-protected",
                    "Size": 100,
                    "VolumeType": "gp3",
                    "Tags": [{"Key": "DoNotTouch", "Value": "true"}],
                }
            ]
        }

    @staticmethod
    def delete_volume(**kwargs):
        raise AssertionError("Protected volume should not be deleted")


class ProtectedS3Client:
    @staticmethod
    def list_buckets():
        return {"Buckets": [{"Name": "protected-bucket"}]}

    @staticmethod
    def get_bucket_tagging(**_kwargs):
        return {"TagSet": [{"Key": "DoNotTouch", "Value": "true"}]}

    @staticmethod
    def list_objects_v2(**_kwargs):
        return {"Contents": [{"Size": 1024}], "NextContinuationToken": None}

    @staticmethod
    def delete_object(**kwargs):
        raise AssertionError("Protected bucket object should not be deleted")


class ProtectedRDSClient:
    @staticmethod
    def describe_db_instances(**kwargs):
        db_instance_identifier = kwargs.get("DBInstanceIdentifier", "db-protected")
        return {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": db_instance_identifier,
                    "DBInstanceArn": f"arn:aws:rds:us-east-1:123456789012:db:{db_instance_identifier}",
                    "DBInstanceClass": "db.t3.micro",
                }
            ]
        }

    @staticmethod
    def list_tags_for_resource(**_kwargs):
        return {"TagList": [{"Key": "DoNotTouch", "Value": "true"}]}

    @staticmethod
    def modify_db_instance(**_kwargs):
        raise AssertionError("Protected RDS instance should not be modified")


class DummyCloudWatchClient:
    @staticmethod
    def get_metric_statistics(**_kwargs):
        return {"Datapoints": [{"Average": 5.0}]}


def test_analyze_ebs_skips_protected_resources():
    findings = analyze_ebs(ProtectedEC2Client(), config=load_config(), region="us-east-1")
    assert not findings


def test_analyze_s3_skips_protected_buckets():
    findings = analyze_s3(ProtectedS3Client(), config=load_config(), top_n=10)
    assert not findings


def test_analyze_rds_skips_protected_instances():
    findings = analyze_rds(
        rds_client=ProtectedRDSClient(),
        cloudwatch_client=DummyCloudWatchClient(),
        config=load_config(),
        region="us-east-1",
    )
    assert not findings


def test_execute_action_skips_protected_ebs_resource():
    result = execute_action(
        action_type="delete-ebs-volume",
        resource_id="vol-protected",
        dry_run=False,
        yes=True,
        ec2_client=ProtectedEC2Client(),
        s3_client=ProtectedS3Client(),
        rds_client=ProtectedRDSClient(),
    )

    assert result.status == "skipped"
    assert "protected" in result.message.lower()


def test_execute_action_skips_protected_rds_resource():
    result = execute_action(
        action_type="resize-rds-instance",
        resource_id="db-protected",
        dry_run=False,
        yes=True,
        ec2_client=ProtectedEC2Client(),
        s3_client=ProtectedS3Client(),
        rds_client=ProtectedRDSClient(),
        target_class="db.t3.small",
    )

    assert result.status == "skipped"
    assert "protected" in result.message.lower()


def test_execute_action_skips_protected_s3_resource():
    result = execute_action(
        action_type="delete-s3-object",
        resource_id="protected-bucket/some-key",
        dry_run=False,
        yes=True,
        ec2_client=ProtectedEC2Client(),
        s3_client=ProtectedS3Client(),
        rds_client=ProtectedRDSClient(),
        bucket="protected-bucket",
        key="some-key",
    )

    assert result.status == "skipped"
    assert "protected" in result.message.lower()


def test_protection_allows_missing_tagset_for_s3():
    class UntaggedS3Client(ProtectedS3Client):
        @staticmethod
        def get_bucket_tagging(**kwargs):
            raise ClientError(
                error_response={"Error": {"Code": "NoSuchTagSet", "Message": "No tags"}},
                operation_name="GetBucketTagging",
            )

    findings = analyze_s3(UntaggedS3Client(), config=load_config(), top_n=10)
    assert len(findings) == 1


def test_s3_access_denied_on_tags_treated_as_protected():
    class AccessDeniedS3Client(ProtectedS3Client):
        @staticmethod
        def get_bucket_tagging(**kwargs):
            raise ClientError(
                error_response={"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                operation_name="GetBucketTagging",
            )

    result = execute_action(
        action_type="delete-s3-object",
        resource_id="protected-bucket/some-key",
        dry_run=False,
        yes=True,
        ec2_client=ProtectedEC2Client(),
        s3_client=AccessDeniedS3Client(),
        rds_client=ProtectedRDSClient(),
        bucket="protected-bucket",
        key="some-key",
    )

    assert result.status == "skipped"
    assert "protected" in result.message.lower()
