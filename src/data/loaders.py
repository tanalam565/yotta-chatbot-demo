from pathlib import Path
from typing import List, Tuple


SUPPORTED_EXTS = {".txt", ".md"}


try:
    import pypdf # optional for pdf
    SUPPORTED_EXTS.add(".pdf")
except Exception:
    pypdf = None

def load_documents(docs_dir: str) -> List[Tuple[str, str]]:
    """Return list of (path, text)."""
    texts = []
    for p in Path(docs_dir).rglob("*"):
        if p.suffix.lower() in SUPPORTED_EXTS and p.is_file():
            if p.suffix.lower() == ".pdf" and pypdf is not None:
                texts.append((str(p), _read_pdf(p)))
            else:
                texts.append((str(p), p.read_text(encoding="utf-8", errors="ignore")))
    return texts

def _read_pdf(p: Path) -> str:
    reader = pypdf.PdfReader(str(p))
    return "\n".join(page.extract_text() or "" for page in reader.pages)