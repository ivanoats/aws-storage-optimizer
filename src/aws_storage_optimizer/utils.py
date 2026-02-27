from __future__ import annotations


def has_protection_tag(tags: list[dict], tag_key: str, tag_value: str) -> bool:
    expected_value = tag_value.strip().lower()
    for tag in tags:
        if str(tag.get("Key", "")) == tag_key and str(tag.get("Value", "")).strip().lower() == expected_value:
            return True
    return False
