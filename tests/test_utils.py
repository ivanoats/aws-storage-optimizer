from aws_storage_optimizer.utils import has_protection_tag


def test_has_protection_tag_matches_case_insensitive_value():
    tags = [{"Key": "DoNotTouch", "Value": "TRUE"}]
    assert has_protection_tag(tags, "DoNotTouch", "true")


def test_has_protection_tag_returns_false_when_key_missing():
    tags = [{"Key": "Owner", "Value": "platform"}]
    assert not has_protection_tag(tags, "DoNotTouch", "true")


def test_has_protection_tag_returns_false_for_empty_input():
    assert not has_protection_tag([], "DoNotTouch", "true")
