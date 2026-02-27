from botocore.exceptions import ClientError

from aws_storage_optimizer.actions import execute_action
from aws_storage_optimizer.analyzers.ebs import analyze_ebs
from aws_storage_optimizer.analyzers.rds import analyze_rds
from aws_storage_optimizer.analyzers.s3 import analyze_s3
from aws_storage_optimizer.config import load_config


class ProtectedEC2Client:
    def describe_volumes(self, **kwargs):
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

    def delete_volume(self, **kwargs):
        raise AssertionError("Protected volume should not be deleted")


class ProtectedS3Client:
    def list_buckets(self):
        return {"Buckets": [{"Name": "protected-bucket"}]}

    def get_bucket_tagging(self, **_kwargs):
        return {"TagSet": [{"Key": "DoNotTouch", "Value": "true"}]}

    def list_objects_v2(self, **_kwargs):
        return {"Contents": [{"Size": 1024}], "NextContinuationToken": None}

    def delete_object(self, **kwargs):
        raise AssertionError("Protected bucket object should not be deleted")


class ProtectedRDSClient:
    def describe_db_instances(self, **kwargs):
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

    def list_tags_for_resource(self, **_kwargs):
        return {"TagList": [{"Key": "DoNotTouch", "Value": "true"}]}

    def modify_db_instance(self, **_kwargs):
        raise AssertionError("Protected RDS instance should not be modified")


class DummyCloudWatchClient:
    def get_metric_statistics(self, **_kwargs):
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


def test_protection_allows_missing_tagset_for_s3():
    class UntaggedS3Client(ProtectedS3Client):
        def get_bucket_tagging(self, **kwargs):
            raise ClientError(
                error_response={"Error": {"Code": "NoSuchTagSet", "Message": "No tags"}},
                operation_name="GetBucketTagging",
            )

    findings = analyze_s3(UntaggedS3Client(), config=load_config(), top_n=10)
    assert len(findings) == 1
