"""Filesystem discovery for templates and resume YAML files (matches CLI logic)."""

import os
from typing import Dict, List, Tuple


def repo_root_from_here(path: str | None = None) -> str:
    """Root of resume-builder repo (directory containing discovery.py's parent)."""
    base = path or os.path.dirname(os.path.abspath(__file__))
    return base


def discover_templates(root: str | None = None) -> Tuple[List[str], Dict[str, str]]:
    """
    Returns (ordered_ids, id_to_absolute_path).
    Same rules as resume_builder CLI: templates/html and templates/html/personal, *.html.j2, not dotfiles.
    """
    root = repo_root_from_here(root)
    template_dirs = [
        os.path.join(root, "templates", "html"),
        os.path.join(root, "templates", "html", "personal"),
    ]
    template_files: List[str] = []
    template_paths: Dict[str, str] = {}

    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for f in os.listdir(template_dir):
                if f.endswith(".html.j2") and not f.startswith("."):
                    full_path = os.path.join(template_dir, f)
                    if os.path.isfile(full_path):
                        if f not in template_files:
                            template_files.append(f)
                            template_paths[f] = full_path

    return template_files, template_paths


def discover_data_files(root: str | None = None) -> Tuple[List[str], Dict[str, str]]:
    """Returns (ordered_ids, id_to_absolute_path). data/ and data/personal/, *.yml / *.yaml."""
    root = repo_root_from_here(root)
    data_dirs = [os.path.join(root, "data"), os.path.join(root, "data", "personal")]
    yml_files: List[str] = []
    yml_paths: Dict[str, str] = {}

    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.endswith(".yml") or f.endswith(".yaml"):
                    if f not in yml_files:
                        yml_files.append(f)
                        yml_paths[f] = os.path.join(data_dir, f)

    return yml_files, yml_paths


def template_display_name(filename: str) -> str:
    return filename.replace(".html.j2", "").replace("-", " ").title()


def data_display_name(filename: str) -> str:
    base = os.path.splitext(filename)[0]
    if base.startswith("resume-"):
        return base.replace("resume-", "")
    return base


def template_origin(path: str) -> str:
    return "personal" if "personal" in path.replace("\\", "/") else "public"


def data_origin(path: str) -> str:
    return "personal" if "personal" in path.replace("\\", "/") else "public"
