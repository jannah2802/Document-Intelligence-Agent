import io
from pathlib import Path
from typing import TypedDict

import pymupdf
import pytesseract
from PIL import Image
from pypdf import PdfReader


class ExtractionResult(TypedDict):
    document_id: str
    raw_text: str


def _ocr_image(image: Image.Image) -> str:
    return pytesseract.image_to_string(image).strip()


def _extract_pdf(document_path: Path) -> str:
    reader = PdfReader(str(document_path))
    pages: list[str] = []

    with pymupdf.open(document_path) as rendered_pdf:
        for page_number, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if not text:
                pixmap = rendered_pdf[page_number].get_pixmap(dpi=200, alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                text = _ocr_image(image)
            pages.append(text)

    return "\n\n".join(text for text in pages if text)


def extract_text(document_id: str, document_path: Path) -> ExtractionResult:
    """Extract text from a PDF or image and return it with its document ID."""
    suffix = document_path.suffix.lower()
    if suffix == ".pdf":
        raw_text = _extract_pdf(document_path)
    elif suffix in {".jpg", ".jpeg", ".png"}:
        with Image.open(document_path) as image:
            raw_text = _ocr_image(image)
    else:
        raise ValueError(f"Unsupported document type: {suffix or 'unknown'}")

    return {"document_id": document_id, "raw_text": raw_text}