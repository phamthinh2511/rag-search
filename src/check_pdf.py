import pymupdf
import os

pdf_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "luat-ttatgt-duongbo.pdf")
doc = pymupdf.open(pdf_path)
text = doc[0].get_text()
print(text[:501] if text.strip() else "⚠️ Không trích được text — có thể PDF là bản scan.")