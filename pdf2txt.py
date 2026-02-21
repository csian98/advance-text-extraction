"""
pdf2txt.py
----------
Converts all PDFs in ./raw-data to .txt files in ./raw-txt using a hybrid
extraction strategy:
    - If a page has fewer than MIN_CHARS characters via pdfplumber (i.e. it is likely a scanned / image-only page)
        -> fall back to Tesseract OCR.
    - Otherwise use pdfplumber's native text extraction (faster, more accurate).

Each page is separated by a clear page marker so the extractor can
reference page boundaries later.

Usage:
    python pdf2txt.py                  # converts all PDFs
    python pdf2txt.py --dpi 200        # set OCR DPI
    python pdf2txt.py --file W28557.pdf  # single file
    python pdf2txt.py --min-chars 50   # tune the OCR fallback threshold
"""

import argparse
import pdf2image
import pdfplumber
import pytesseract
from pathlib import Path


RAW_DATA  = Path("./raw-data")
RAW_TXT   = Path("./raw-txt")
PAGE_SEP  = "=== PAGE {page} ==="
MIN_CHARS = 100   # pages with fewer native chars than this trigger OCR


def extract_page(
    pdf_path: Path,
    page_num: int,
    plumber_page, # pdfplumber page object (already open)
    dpi: int,
    min_chars: int,
) -> tuple[str, str]:
    """
    Return (text, method) for a single page.
    method is 'native' or 'ocr'.
    """
    native_text = plumber_page.extract_text() or ""

    if len(native_text.strip()) >= min_chars:
        return native_text, "native "

    # Too little text, likely a scanned page - use OCR
    images = pdf2image.convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=page_num,
        last_page=page_num,
    )
    ocr_text = pytesseract.image_to_string(images[0])
    return ocr_text, "  ocr  "


def pdf_to_txt(pdf_path: Path, dpi: int = 300, min_chars: int = MIN_CHARS) -> str:
    """Hybrid-extract a single PDF and return full text with page markers."""
    parts = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)

        for page_num, plumber_page in enumerate(pdf.pages, start=1):
            text, method = extract_page(
                pdf_path, page_num, plumber_page, dpi, min_chars
            )
            parts.append(f"{PAGE_SEP.format(page=page_num)}\n\n{text}")
            print(f"  Page {page_num}/{total} [{method}]", end="\r")

    print()
    return "\n\n".join(parts)


def convert_all(dpi: int = 300, single_file: str = None, min_chars: int = MIN_CHARS):
    RAW_TXT.mkdir(parents=True, exist_ok=True)

    if single_file:
        pdfs = [RAW_DATA / single_file]
    else:
        pdfs = sorted(RAW_DATA.glob("*.pdf"))

    if not pdfs:
        print("No PDFs found in", RAW_DATA)
        return

    for pdf_path in pdfs:
        out_path = RAW_TXT / (pdf_path.stem + ".txt")

        if out_path.exists():
            print(f"Skipping (already converted): {pdf_path.name}")
            continue

        print(f"Converting: {pdf_path.name}")
        try:
            text = pdf_to_txt(pdf_path, dpi=dpi, min_chars=min_chars)
            out_path.write_text(text, encoding="utf-8")
            print(f"  Saved: {out_path}")
        except Exception as e:
            print(f"  Failed: {pdf_path.name} | {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDFs to text (hybrid native+OCR).")
    parser.add_argument("--dpi",       type=int, default=300,      help="OCR resolution (default 300)")
    parser.add_argument("--file",      type=str, default=None,     help="Convert a single PDF by filename")
    parser.add_argument("--min-chars", type=int, default=MIN_CHARS, help="Native-text threshold before OCR fallback (default 100)")
    args = parser.parse_args()

    convert_all(dpi=args.dpi, single_file=args.file, min_chars=args.min_chars)