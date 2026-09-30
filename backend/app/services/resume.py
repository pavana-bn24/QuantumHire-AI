"""Resume validation and PDF text extraction (PyMuPDF).

Every failure mode has its own exception carrying an HTTP status, so the API can
return a precise, actionable error instead of a 500:

======================  =====  ============================================
Failure                 HTTP   Exception
======================  =====  ============================================
no file / empty upload  400    ``EmptyUploadError``
wrong format / MIME     415    ``UnsupportedResumeTypeError``
too large               413    ``ResumeTooLargeError``
corrupt / unreadable    422    ``CorruptResumeError``
password protected      422    ``EncryptedResumeError``
PDF has no pages        422    ``EmptyResumeError``
scanned / image only    422    ``ScannedResumeError``
unexpected fitz failure 422    ``ResumeExtractionError``
======================  =====  ============================================

Uploaded bytes are processed **in memory only**: they are never written to disk
and never exposed through a static route, so a resume URL cannot leak. Only the
extracted text is persisted.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import fitz  # PyMuPDF

from app.core.config import settings

PDF_MAGIC = b"%PDF-"
PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}
#: Browsers occasionally send this for PDFs; we still require real PDF magic bytes.
GENERIC_MIME_TYPES = {"application/octet-stream", "binary/octet-stream"}

#: Patterns that suggest the resume is trying to talk to the model.
INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts)", "override instructions"),
    (r"disregard\s+(all\s+)?(previous|prior|above)", "override instructions"),
    (r"you\s+are\s+now\s+(a|an)\b", "role reassignment attempt"),
    (r"system\s+prompt", "system prompt reference"),
    (r"(rate|score|rank)\s+(this|the)\s+candidate", "score manipulation attempt"),
    (r"give\s+(me|this\s+candidate)\s+(a\s+)?(perfect|full|10/10|highest)", "score inflation"),
    (r"output\s+(only\s+)?(the\s+)?(following\s+)?json", "output hijack attempt"),
    (r"do\s+not\s+(mention|reveal|report)", "suppression attempt"),
]

_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


class ResumeError(Exception):
    """Base class for every resume ingestion failure."""

    code = "resume_error"
    http_status = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmptyUploadError(ResumeError):
    code = "empty_upload"
    http_status = 400


class UnsupportedResumeTypeError(ResumeError):
    code = "unsupported_file_type"
    http_status = 415


class ResumeTooLargeError(ResumeError):
    code = "resume_too_large"
    http_status = 413


class CorruptResumeError(ResumeError):
    code = "corrupt_pdf"
    http_status = 422


class EncryptedResumeError(ResumeError):
    code = "encrypted_pdf"
    http_status = 422


class EmptyResumeError(ResumeError):
    code = "empty_pdf"
    http_status = 422


class ScannedResumeError(ResumeError):
    code = "scanned_pdf"
    http_status = 422


class ResumeExtractionError(ResumeError):
    code = "extraction_failed"
    http_status = 422


@dataclass
class PdfTextResult:
    """Result of a successful text extraction."""

    text: str
    page_count: int
    char_count: int
    word_count: int


def content_hash(data: bytes) -> str:
    """SHA-256 of the uploaded bytes (used for traceability / exact-duplicate checks)."""
    return hashlib.sha256(data).hexdigest()


def clean_text(raw: str) -> str:
    """Normalise whitespace so downstream prompts and storage stay tidy."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def validate_resume_upload(filename: str | None, content_type: str | None, data: bytes) -> str:
    """Validate an upload and return a safe display filename.

    Checks (in order): presence, size, declared type, extension, magic bytes.
    """
    if not data:
        raise EmptyUploadError("The uploaded file is empty. Choose a PDF resume and try again.")

    if len(data) > settings.max_resume_size_bytes:
        raise ResumeTooLargeError(
            f"Resume is {len(data) / 1024 / 1024:.1f} MB, which exceeds the "
            f"{settings.max_resume_size_mb} MB limit."
        )

    display_name = (filename or "").strip().replace("\\", "/").split("/")[-1]
    extension = display_name.lower().rsplit(".", 1)[-1] if "." in display_name else ""
    declared_type = (content_type or "").split(";")[0].strip().lower()

    if not display_name:
        raise UnsupportedResumeTypeError("No filename was provided. Upload a .pdf resume.")

    if extension != settings.allowed_resume_extension.lstrip("."):
        raise UnsupportedResumeTypeError(
            f"'.{extension or 'unknown'}' files are not supported. Only PDF resumes "
            f"({settings.allowed_resume_extension}) can be uploaded."
        )

    if declared_type and declared_type not in PDF_MIME_TYPES | GENERIC_MIME_TYPES:
        raise UnsupportedResumeTypeError(
            f"Unsupported content type '{declared_type}'. Only PDF resumes are accepted. "
            "Convert the document to PDF and upload it again."
        )

    # A correct extension and Content-Type are easy to fake - verify the real header.
    if not data.startswith(PDF_MAGIC):
        raise UnsupportedResumeTypeError(
            "The file does not look like a real PDF (missing '%PDF-' header). "
            "Only genuine PDF resumes are accepted."
        )

    return display_name


def extract_text_from_pdf(data: bytes) -> PdfTextResult:
    """Extract text from PDF bytes, raising a precise error on every failure mode."""
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # fitz raises a variety of low-level errors
        raise CorruptResumeError(
            "This PDF could not be read - it may be corrupted or truncated. "
            "Try re-exporting the resume as a new PDF."
        ) from exc

    try:
        if document.needs_pass:
            raise EncryptedResumeError(
                "This PDF is password protected. Remove the password and upload it again."
            )

        page_count = document.page_count
        if page_count == 0:
            raise EmptyResumeError("The PDF contains no pages.")

        chunks: list[str] = []
        for page in document:
            try:
                chunks.append(page.get_text("text"))
            except Exception:  # a single bad page must not kill the upload
                chunks.append("")
    except ResumeError:
        raise
    except Exception as exc:
        raise ResumeExtractionError(f"Text extraction failed: {exc}") from exc
    finally:
        document.close()

    text = clean_text("\n".join(chunks))

    if not text:
        raise ScannedResumeError(
            "No text could be extracted - this PDF looks like a scanned image or contains "
            "only graphics. Upload a text-based PDF, or run OCR on it first."
        )

    if len(text) < settings.resume_min_chars:
        raise ScannedResumeError(
            f"Only {len(text)} characters of text were found (minimum "
            f"{settings.resume_min_chars}). The PDF is probably a scan or image export, so "
            "there is no reliable evidence to extract. Please upload a text-based PDF."
        )

    return PdfTextResult(
        text=text,
        page_count=page_count,
        char_count=len(text),
        word_count=len(text.split()),
    )


def detect_prompt_injection(text: str) -> list[str]:
    """Return human-readable warnings for instruction-like text in the resume.

    This never blocks the upload - the extraction prompt already treats resume
    content as data. It simply tells the recruiter what was found.
    """
    found: list[str] = []
    lowered = text.lower()

    for pattern, label in INJECTION_PATTERNS:
        if re.search(pattern, lowered) and label not in found:
            found.append(label)

    return found
