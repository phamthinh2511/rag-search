import json
import os
import re
import unicodedata

import pymupdf

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR = os.path.join(ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")

BODY_MIN_SIZE = 13.0
BAD_OCR_FONT = "Times-Roman"


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)  # thống nhất dạng dựng sẵn của tiếng Việt
    text = text.replace(" ", " ").replace("­", "")
    return re.sub(r"\s+", " ", text).strip()


def is_bold(span: dict) -> bool:
    return bool(span["flags"] & 16)


def extract_page_lines(page: pymupdf.Page) -> list[dict]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if not s["flags"] & 1 and s["size"] >= 10]
            body = [s for s in spans if s["text"].strip()]
            if not body:
                continue
            if max(s["size"] for s in body) < BODY_MIN_SIZE:
                continue
            text = clean_text("".join(s["text"] for s in spans))
            if not text:
                continue
            if text.isdigit() and line["bbox"][1] < 50:
                continue
            lines.append({"text": text, "bold": all(is_bold(s) for s in body)})
    return lines


def is_bad_ocr_page(page: pymupdf.Page) -> bool:
    total = bad = 0
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for s in line["spans"]:
                total += len(s["text"])
                if s["font"] == BAD_OCR_FONT:
                    bad += len(s["text"])
    return total > 0 and bad / total > 0.5


def extract_pdf(pdf_path: str) -> dict:
    doc = pymupdf.open(pdf_path)
    pages, skipped = [], []
    for i, page in enumerate(doc, start=1):
        if is_bad_ocr_page(page):
            skipped.append(i)
            continue
        pages.append({"page": i, "lines": extract_page_lines(page)})
    return {"file": os.path.basename(pdf_path), "num_pages": len(doc),
            "skipped_pages": skipped, "pages": pages}


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    for name in sorted(os.listdir(RAW_DIR)):
        if not name.lower().endswith(".pdf"):
            continue
        result = extract_pdf(os.path.join(RAW_DIR, name))
        out = os.path.join(PROCESSED_DIR, os.path.splitext(name)[0] + ".pages.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        n_lines = sum(len(p["lines"]) for p in result["pages"])
        print(f"{name}: {result['num_pages']} trang, {n_lines} dòng -> {os.path.relpath(out, ROOT)}")
        if result["skipped_pages"]:
            print(f"  ⚠️ Bỏ qua trang lỗi OCR: {result['skipped_pages']}")


if __name__ == "__main__":
    main()
