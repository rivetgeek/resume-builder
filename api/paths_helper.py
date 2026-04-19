import os
import re

import yaml

from api.config import repo_root
from discovery import discover_data_files


def suffix_from_data_file(data_file_id: str) -> str:
    base = os.path.splitext(data_file_id)[0]
    if base.startswith("resume-"):
        return base.replace("resume-", "")
    return base


def resume_stem_from_yaml(data_path: str) -> tuple[str, str, str]:
    with open(data_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "name" not in data:
        raise ValueError("invalid_yaml")
    name = data.get("name", "Resume")
    parts = str(name).split()
    first, last = parts[0], parts[-1] if len(parts) > 1 else name
    stem = f"{first}_{last}_Resume"
    return first, last, stem


def disk_artifact_path(data_file: str, fmt: str) -> str | None:
    root = repo_root()
    _, dp = discover_data_files(root)
    if data_file not in dp:
        return None
    data_path = dp[data_file]
    try:
        _, _, stem = resume_stem_from_yaml(data_path)
    except ValueError:
        return None
    suf = suffix_from_data_file(data_file)
    if not re.match(r"^[a-zA-Z0-9_-]+$", suf):
        return None
    out_dir = os.path.join(root, "outputs", suf)
    ext = {"pdf": "pdf", "docx": "docx", "html": "html"}[fmt]
    path = os.path.join(out_dir, f"{stem}.{ext}")
    return path if os.path.isfile(path) else None
