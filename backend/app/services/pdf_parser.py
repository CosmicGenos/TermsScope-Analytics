from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


async def extract_text_from_pdf(file_bytes: bytes, filename: str = "upload.pdf") -> dict:
    
    try:
        import fitz  # PyMuPDF

        # Write to a temp file (fitz works best with file paths)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        doc = fitz.open(tmp_path)
        pages_text = []
        title = None

        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                pages_text.append(text)

            # Try to extract title from first page
            if page_num == 0 and not title:
                lines = text.strip().split("\n")
                for line in lines[:5]:  # Check first 5 lines
                    clean = line.strip()
                    if 10 < len(clean) < 200:
                        title = clean
                        break

        doc.close()

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        content = "\n\n".join(pages_text).strip()

        if not content:
            return {
                "success": False,
                "content": None,
                "title": None,
                "error": "Could not extract text from PDF. The file may be image-based.",
            }

        return {
            "success": True,
            "content": content,
            "title": title,
            "error": None,
        }

    except Exception as exc:
        logger.error("PDF extraction failed for %s: %s", filename, exc)
        return {
            "success": False,
            "content": None,
            "title": None,
            "error": f"Failed to process PDF: {str(exc)}",
        }
