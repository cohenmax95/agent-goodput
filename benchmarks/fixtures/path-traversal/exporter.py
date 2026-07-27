from pathlib import Path


def export_report(root: Path, export_name: str, content: str) -> Path:
    destination = root / export_name
    destination.write_text(content, encoding="utf-8")
    return destination
