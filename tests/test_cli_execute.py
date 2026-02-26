from click.testing import CliRunner

import aws_storage_optimizer.cli as cli_module


class DummyFactory:
    def s3(self):
        return object()

    def ec2(self):
        return object()

    def rds(self):
        return object()


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
