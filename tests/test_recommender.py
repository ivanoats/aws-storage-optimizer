from aws_storage_optimizer.models import Finding
from aws_storage_optimizer.recommender import prioritize_findings


def test_prioritize_findings_prefers_higher_weighted_score():
    rds_candidate = Finding(
        service="rds",
        resource_id="db-1",
        region="us-east-1",
        recommendation="Downsize",
        estimated_monthly_savings_usd=30.0,
        risk_level="medium",
        details={"avg_cpu_pct": 3.0},
    )
    ebs_candidate = Finding(
        service="ebs",
        resource_id="vol-1",
        region="us-east-1",
        recommendation="Delete unattached EBS volume",
        estimated_monthly_savings_usd=24.0,
        risk_level="low",
        details={},
    )

    prioritized = prioritize_findings([rds_candidate, ebs_candidate])

    assert prioritized[0].resource_id == "db-1"


def test_prioritize_findings_does_not_promote_negative_savings():
    negative_candidate = Finding(
        service="ebs",
        resource_id="vol-neg",
        region="us-east-1",
        recommendation="Bad estimate",
        estimated_monthly_savings_usd=-5.0,
        risk_level="low",
        details={},
    )
    zero_candidate = Finding(
        service="ebs",
        resource_id="vol-zero",
        region="us-east-1",
        recommendation="Neutral",
        estimated_monthly_savings_usd=0.0,
        risk_level="low",
        details={},
    )

    prioritized = prioritize_findings([zero_candidate, negative_candidate])

    assert prioritized[0].resource_id == "vol-zero"
