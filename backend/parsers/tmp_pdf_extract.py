from pathlib import Path
import fitz

def extract_text(path, max_pages=20):
    try:
        doc = fitz.open(path)
        text = []
        for i, page in enumerate(doc, start=1):
            if i > max_pages:
                break
            text.append(f"--- PAGE {i} ---\n")
            text.append(page.get_text())
        return "\n".join(text)
    except Exception as e:
        return f"ERROR opening {path}: {e}"

pdf_files = sorted(Path('.').glob('*.pdf'))
print(f"FOUND {len(pdf_files)} PDFs")
for p in pdf_files:
    print('\nFILE:', p)
    print(extract_text(p, max_pages=20))
