import json

import pytest

from aws_storage_optimizer.models import AnalysisResult, Finding
from aws_storage_optimizer.reporting import (
    load_analysis,
    print_analysis_json,
    print_analysis_table,
    save_analysis,
)


def _sample_result() -> AnalysisResult:
    return AnalysisResult(
        generated_at="2026-02-26T00:00:00Z",
        findings=[
            Finding(
                service="ebs",
                resource_id="vol-123",
                region="us-east-1",
                recommendation="Delete unattached EBS volume",
                estimated_monthly_savings_usd=8.5,
                risk_level="low",
                details={"size_gib": 100},
            )
        ],
    )


def test_save_and_load_analysis_roundtrip(tmp_path):
    result = _sample_result()
    file_path = tmp_path / "reports" / "findings.json"

    save_analysis(result, str(file_path))
    loaded = load_analysis(str(file_path))

    assert loaded.generated_at == result.generated_at
    assert len(loaded.findings) == 1
    assert loaded.findings[0].resource_id == "vol-123"
    assert loaded.findings[0].estimated_monthly_savings_usd == pytest.approx(8.5)


def test_print_analysis_json_outputs_valid_json(capsys):
    result = _sample_result()

    print_analysis_json(result)
    captured = capsys.readouterr()

    payload = json.loads(captured.out)
    assert payload["generated_at"] == "2026-02-26T00:00:00Z"
    assert payload["findings"][0]["service"] == "ebs"


def test_print_analysis_table_emits_summary(capsys):
    result = _sample_result()

    print_analysis_table(result)
    captured = capsys.readouterr()

    assert "AWS Storage Optimization Findings" in captured.out
    assert "vol-123" in captured.out
    assert "ebs" in captured.out.lower()
