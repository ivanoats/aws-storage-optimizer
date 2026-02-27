import os

import pytest
from click.testing import CliRunner

from aws_storage_optimizer.cli import cli


pytestmark = pytest.mark.integration


def _sandbox_ready() -> bool:
    return (
        os.getenv("ASO_RUN_SANDBOX_TESTS", "").lower() in {"1", "true", "yes"}
        and bool(os.getenv("AWS_PROFILE"))
        and bool(os.getenv("AWS_REGION"))
    )


@pytest.mark.skipif(not _sandbox_ready(), reason="Set ASO_RUN_SANDBOX_TESTS=1 with AWS_PROFILE/AWS_REGION")
def test_sandbox_analyze_smoke():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--profile",
            os.environ["AWS_PROFILE"],
            "--region",
            os.environ["AWS_REGION"],
            "analyze",
            "--services",
            "ebs",
            "--output-format",
            "json",
        ],
    )

    assert result.exit_code == 0
