from aws_storage_optimizer.aws_clients import AWSClientFactory
from aws_storage_optimizer.config import (
    AppConfig,
    EstimationRates,
    ProtectionSettings,
    RetrySettings,
    Thresholds,
)


class SessionSpy:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    def client(self, service_name, config=None):
        self.calls.append((service_name, config))
        return {"service": service_name, "config": config}


def test_client_factory_passes_profile_region_to_session(monkeypatch):
    captured = {}

    def fake_session(**kwargs):
        captured["session"] = SessionSpy(**kwargs)
        return captured["session"]

    monkeypatch.setattr("aws_storage_optimizer.aws_clients.boto3.Session", fake_session)

    factory = AWSClientFactory(profile="finops-prod", region="us-east-1")
    session_spy = captured["session"]

    assert session_spy.kwargs["profile_name"] == "finops-prod"
    assert session_spy.kwargs["region_name"] == "us-east-1"

    response = factory.s3()
    assert response["service"] == "s3"


def test_client_factory_uses_retry_config_from_app_config(monkeypatch):
    captured = {}

    def fake_session(**kwargs):
        captured["session"] = SessionSpy(**kwargs)
        return captured["session"]

    monkeypatch.setattr("aws_storage_optimizer.aws_clients.boto3.Session", fake_session)

    app_config = AppConfig(
        thresholds=Thresholds(),
        rates=EstimationRates(),
        protection=ProtectionSettings(),
        retry=RetrySettings(mode="adaptive", max_attempts=9),
    )

    factory = AWSClientFactory(profile=None, region=None, config=app_config)

    ec2_client = factory.ec2()
    assert ec2_client["service"] == "ec2"
    retry_cfg = ec2_client["config"].retries
    assert retry_cfg["mode"] == "adaptive"
    assert retry_cfg["max_attempts"] == 9


def test_client_factory_defaults_retry_config_when_no_app_config(monkeypatch):
    captured = {}

    def fake_session(**kwargs):
        captured["session"] = SessionSpy(**kwargs)
        return captured["session"]

    monkeypatch.setattr("aws_storage_optimizer.aws_clients.boto3.Session", fake_session)

    factory = AWSClientFactory(profile=None, region=None)
    session_spy = captured["session"]
    assert session_spy.kwargs["region_name"] == "us-west-2"

    cloudwatch_client = factory.cloudwatch()

    retry_cfg = cloudwatch_client["config"].retries
    assert retry_cfg["mode"] == "standard"
    assert retry_cfg["max_attempts"] == 5
