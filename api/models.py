from typing import Literal, Optional

from pydantic import BaseModel, Field


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=500)


class GenerateBody(BaseModel):
    template_id: str = Field(..., min_length=1, max_length=255)
    data_file_id: str = Field(..., min_length=1, max_length=255)
    formats: list[Literal["pdf", "docx", "html"]] = Field(
        default_factory=lambda: ["pdf"],
        min_length=1,
    )
    pdf_variant: Literal["pdf/a-1b", "pdf/a-2b", "pdf/a-3b", "pdf/a-4b"] = "pdf/a-2b"
    run_ats_check: bool = False
    preview_only: bool = False
    role_id: Optional[str] = Field(default=None, max_length=256)


class NotesBody(BaseModel):
    notes: str = Field(..., max_length=2000)
