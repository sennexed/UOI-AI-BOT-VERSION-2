"""Utilities for extracting text from PDFs and turning it into speech."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

from gtts import gTTS
from pypdf import PdfReader


PdfMode = Literal["text", "ocr", "hybrid"]


@dataclass
class PdfExtractionResult:
    mode_used: str
    text: str
    total_pages: int
    extracted_pages: int


class PdfTtsService:
    """PDF text extraction and TTS generation service."""

    def extract_text(self, pdf_bytes: bytes, mode: PdfMode = "hybrid", max_pages: int = 8) -> PdfExtractionResult:
        mode = (mode or "hybrid").lower()  # type: ignore[assignment]
        if mode not in {"text", "ocr", "hybrid"}:
            raise ValueError("Invalid mode. Use one of: text, ocr, hybrid.")

        if mode == "text":
            return self._extract_embedded_text(pdf_bytes, max_pages)
        if mode == "ocr":
            return self._extract_ocr_text(pdf_bytes, max_pages)

        text_result = self._extract_embedded_text(pdf_bytes, max_pages)
        if len(text_result.text.strip()) >= 200:
            return PdfExtractionResult(
                mode_used="hybrid(text)",
                text=text_result.text,
                total_pages=text_result.total_pages,
                extracted_pages=text_result.extracted_pages,
            )

        ocr_result = self._extract_ocr_text(pdf_bytes, max_pages)
        return PdfExtractionResult(
            mode_used="hybrid(ocr)",
            text=ocr_result.text,
            total_pages=ocr_result.total_pages,
            extracted_pages=ocr_result.extracted_pages,
        )

    def text_to_mp3(self, text: str, output_path: str, lang: str = "en", slow: bool = False) -> None:
        if not text.strip():
            raise ValueError("No readable text found to synthesize.")
        tts = gTTS(text=text[:4500], lang=lang, slow=slow)
        tts.save(output_path)

    def _extract_embedded_text(self, pdf_bytes: bytes, max_pages: int) -> PdfExtractionResult:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)

        collected: list[str] = []
        for index in range(pages_to_read):
            raw = reader.pages[index].extract_text() or ""
            cleaned = " ".join(raw.split())
            if cleaned:
                collected.append(f"Page {index + 1}: {cleaned}")

        return PdfExtractionResult(
            mode_used="text",
            text="\n\n".join(collected),
            total_pages=total_pages,
            extracted_pages=pages_to_read,
        )

    def _extract_ocr_text(self, pdf_bytes: bytes, max_pages: int) -> PdfExtractionResult:
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image
        except Exception as exc:  # pragma: no cover - dependency/runtime guard
            raise RuntimeError(
                "OCR mode requires additional dependencies (PyMuPDF, pillow, pytesseract) "
                "and a tesseract binary installed in the host environment."
            ) from exc

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        pages_to_read = min(total_pages, max_pages)

        collected: list[str] = []
        for index in range(pages_to_read):
            page = doc[index]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            raw = pytesseract.image_to_string(image) or ""
            cleaned = " ".join(raw.split())
            if cleaned:
                collected.append(f"Page {index + 1}: {cleaned}")

        return PdfExtractionResult(
            mode_used="ocr",
            text="\n\n".join(collected),
            total_pages=total_pages,
            extracted_pages=pages_to_read,
        )
