"""
main.py
-------
Runs the full pipeline:
    1. pdf2txt.py  — OCR all PDFs in ./raw-data  -> ./raw-txt
    2. extractor.py — extract fields from all .txt files in ./raw-txt

Results are printed and saved to ./output/results.json

Usage:
    python main.py                    # full pipeline
    python main.py --skip-ocr         # skip OCR, only run extractor
    python main.py --file W28557      # process a single file (no .pdf/.txt extension)
    python main.py --dpi 200          # lower DPI for faster OCR
"""

import argparse
import json
from pathlib import Path

from pdf2txt import convert_all
from extractor import Extractor

OUTPUT_DIR = Path("./output")


def run(skip_ocr: bool = False, single_file: str = None, dpi: int = 300):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Step 1: OCR -------------------------------------------------- #
    if not skip_ocr:
        print("=" * 60)
        print("STEP 1: Converting PDFs to text")
        print("=" * 60)
        convert_all(dpi=dpi, single_file=f"{single_file}.pdf" if single_file else None)
    else:
        print("Skipping OCR step.\n")

    # ---- Step 2: Extract ---------------------------------------------- #
    print()
    print("=" * 60)
    print("STEP 2: Extracting fields from text files")
    print("=" * 60)

    extractor = Extractor("./raw-txt")

    if single_file:
        txt_path = Path("./raw-txt") / f"{single_file}.txt"
        if not txt_path.exists():
            print(f"Text file not found: {txt_path}")
            return
        results = [extractor.extract_txt(txt_path)]
    else:
        results = extractor.extract_all()

    # ---- Output -------------------------------------------------------- #
    print()
    print("=" * 60)
    print("EXTRACTION COMPLETE.")
    print("=" * 60)

    out_file = OUTPUT_DIR / ("result.json" if single_file else "results.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved to: {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF well data extraction pipeline.")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR, run extractor only")
    parser.add_argument("--file",     type=str, default=None, help="Process a single file (no extension)")
    parser.add_argument("--dpi",      type=int, default=300,  help="OCR resolution (default 300)")
    args = parser.parse_args()

    run(skip_ocr=args.skip_ocr, single_file=args.file, dpi=args.dpi)