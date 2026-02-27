from __future__ import annotations

import boto3
from botocore.config import Config as BotoConfig

from aws_storage_optimizer.config import AppConfig


class AWSClientFactory:
    def __init__(self, profile: str | None, region: str | None, config: AppConfig | None = None):
        session_args: dict[str, str] = {}
        if profile:
            session_args["profile_name"] = profile
        resolved_region = region or (config.region if config else None) or "us-west-2"
        session_args["region_name"] = resolved_region
        self.session = boto3.Session(**session_args)
        retry_mode = "standard"
        retry_max_attempts = 5
        if config:
            retry_mode = config.retry.mode
            retry_max_attempts = config.retry.max_attempts
        self.client_config = BotoConfig(retries={"mode": retry_mode, "max_attempts": retry_max_attempts})

    def s3(self):
        return self.session.client("s3", config=self.client_config)

    def ec2(self):
        return self.session.client("ec2", config=self.client_config)

    def rds(self):
        return self.session.client("rds", config=self.client_config)

    def cloudwatch(self):
        return self.session.client("cloudwatch", config=self.client_config)
