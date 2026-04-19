import hashlib
import logging
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import yaml
from ats_checker import ATSComplianceChecker

from api import db
from api.config import repo_root
from api.docx_converter import html_to_docx
from api.paths_helper import resume_stem_from_yaml, suffix_from_data_file
from api.preview_store import EphemeralArtifacts, preview_store
from discovery import discover_data_files, discover_templates
from resume_builder import render_resume

logger = logging.getLogger(__name__)

ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def resolve_paths(template_id: str, data_file_id: str) -> tuple[str, str]:
    root = repo_root()
    if not ID_RE.match(template_id) or not ID_RE.match(data_file_id):
        raise ValueError("invalid_id")
    _, tp = discover_templates(root)
    _, dp = discover_data_files(root)
    if template_id not in tp or data_file_id not in dp:
        raise ValueError("unknown_id")
    return tp[template_id], dp[data_file_id]


def _ats_structured(data: dict, html: str) -> tuple[dict[str, list[str]], int, int, int]:
    checker = ATSComplianceChecker()
    di = checker.check_resume_data(data)
    hi = checker.check_html_compliance(html)
    errors = di["errors"] + hi["errors"]
    warnings = di["warnings"] + hi["warnings"]
    suggestions = di["suggestions"] + hi["suggestions"]
    return (
        {"errors": errors, "warnings": warnings, "suggestions": suggestions},
        len(errors),
        len(warnings),
        len(suggestions),
    )


def execute_generate(
    *,
    template_id: str,
    data_file_id: str,
    formats: list[str],
    pdf_variant: str,
    run_ats_check: bool,
    preview_only: bool,
    role_id: Optional[str],
) -> dict[str, Any]:
    root = repo_root()
    template_path, data_path = resolve_paths(template_id, data_file_id)
    suffix = suffix_from_data_file(data_file_id)
    if not re.match(r"^[a-zA-Z0-9_-]+$", suffix):
        raise ValueError("invalid_suffix")

    _, _, stem = resume_stem_from_yaml(data_path)
    with open(data_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    submission_uuid = str(uuid.uuid4())
    want_pdf = "pdf" in formats
    want_html = "html" in formats
    want_docx = "docx" in formats

    tmp_dir: str | None = None
    if preview_only:
        tmp_dir = tempfile.mkdtemp(prefix="rb_preview_")
        html_out = os.path.join(tmp_dir, f"{stem}.html")
        pdf_out = os.path.join(tmp_dir, f"{stem}.pdf") if want_pdf else None
    else:
        out_dir = os.path.join(root, "outputs", suffix)
        os.makedirs(out_dir, exist_ok=True)
        html_out = os.path.join(out_dir, f"{stem}.html")
        pdf_out = os.path.join(out_dir, f"{stem}.pdf") if want_pdf else None

    try:
        try:
            render_resume(
                template_path=template_path,
                data_path=data_path,
                html_output_path=html_out,
                pdf_output_path=pdf_out,
                validate_ats=run_ats_check,
                pdf_variant=pdf_variant if want_pdf else None,
            )
        except Exception as e:
            logger.exception("render_resume failed")
            raise ValueError(f"generation_failed:{e}") from e

        if want_pdf and pdf_out and not os.path.isfile(pdf_out):
            raise ValueError("generation_failed:pdf_not_created")

        with open(html_out, encoding="utf-8") as f:
            html_content = f.read()

        ats_report: Optional[dict[str, list[str]]] = None
        ats_e = ats_w = ats_s = None
        if run_ats_check:
            ats_report, ats_e, ats_w, ats_s = _ats_structured(data, html_content)

        pdf_bytes: Optional[bytes] = None
        output_hash: Optional[str] = None
        if want_pdf and pdf_out:
            with open(pdf_out, "rb") as f:
                pdf_bytes = f.read()
            output_hash = hashlib.sha256(pdf_bytes).hexdigest()

        docx_bytes: Optional[bytes] = None
        if want_docx:
            try:
                docx_bytes = html_to_docx(html_content)
            except Exception as e:
                logger.exception("docx conversion failed")
                raise ValueError(f"generation_failed:docx:{e}") from e
            if not preview_only:
                docx_path = os.path.join(os.path.dirname(html_out), f"{stem}.docx")
                with open(docx_path, "wb") as f:
                    f.write(docx_bytes)

        if preview_only:
            preview_store.set(
                submission_uuid,
                EphemeralArtifacts(
                    pdf_bytes=pdf_bytes,
                    html_str=html_content if want_html else None,
                    docx_bytes=docx_bytes,
                ),
            )

        created = datetime.now(timezone.utc).isoformat()
        db.insert_submission(
            submission_uuid=submission_uuid,
            template_name=template_id,
            data_file=data_file_id,
            pdf_variant=pdf_variant if want_pdf else None,
            ats_check_run=run_ats_check,
            ats_errors=ats_e,
            ats_warnings=ats_w,
            ats_suggestions=ats_s,
            output_formats=formats,
            output_hash=output_hash,
            role_id=role_id,
            notes=None,
            created_at_iso=created,
        )

        base = "/api"
        artifacts: dict[str, str] = {}
        if want_pdf:
            artifacts["pdf"] = f"{base}/download/{submission_uuid}/pdf"
        if want_docx:
            artifacts["docx"] = f"{base}/download/{submission_uuid}/docx"
        if want_html:
            artifacts["html"] = f"{base}/download/{submission_uuid}/html"

        return {
            "submission_id": submission_uuid,
            "artifacts": artifacts,
            "ats_report": ats_report,
        }
    finally:
        if preview_only and tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
