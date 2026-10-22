"""Dependency-free helpers that map explicit missing-PPE classes to alerts."""
from __future__ import annotations


def violation_label(class_name: str) -> str | None:
    """Only explicit missing-equipment model classes may produce alerts."""
    normalized = str(class_name).strip().lower().replace("_", "-")
    normalized = " ".join(normalized.replace("-", " ").split())
    compact = normalized.replace(" ", "")
    if compact in {"nomask", "withoutmask", "maskmissing", "no-mask"}:
        return "ماسک شناسایی نشد"
    if compact in {"nohardhat", "nohelmet", "withouthelmet", "helmetmissing", "hardhatmissing"}:
        return "کلاه ایمنی شناسایی نشد"
    return None
