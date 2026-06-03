from pathlib import Path
import fitz

pdf_files = sorted(Path('.').glob('*.pdf'))
print(f'FOUND {len(pdf_files)} PDF files')

# Simple PDF extraction utility used during guideline ingestion.
# - Opens each PDF and extracts plain text for downstream processing.
# - This is a lightweight helper for local use; for robust extraction
#   consider OCR and noise-handling for scanned PDFs.
for p in pdf_files:
    try:
        doc = fitz.open(str(p))
        text_lines = []
        for page in doc:
            text_lines.append(page.get_text())
        out = Path(p.stem + '.txt')
        out.write_text('\n'.join(text_lines), encoding='utf-8')
        print(f'WROTE {out} pages={len(doc)}')
    except Exception as e:
        print(f'ERROR {p}: {e}')
