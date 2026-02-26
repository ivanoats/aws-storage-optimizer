from __future__ import annotations

import boto3


class AWSClientFactory:
    def __init__(self, profile: str | None, region: str | None):
        session_args: dict[str, str] = {}
        if profile:
            session_args["profile_name"] = profile
        if region:
            session_args["region_name"] = region
        self.session = boto3.Session(**session_args)

    def s3(self):
        return self.session.client("s3")

    def ec2(self):
        return self.session.client("ec2")

    def rds(self):
        return self.session.client("rds")

    def cloudwatch(self):
        return self.session.client("cloudwatch")
