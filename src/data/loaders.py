# src/data/loaders.py

from pathlib import Path
from typing import List
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.schema import Document

# -------- Optional OCR deps (graceful if missing) --------
try:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore
    OCR_IMAGE_OK = True
except Exception:
    OCR_IMAGE_OK = False

try:
    from pdf2image import convert_from_path  # type: ignore
    OCR_PDF_OK = True
except Exception:
    OCR_PDF_OK = False

# Which file types we handle
TEXT_EXTS = {".txt", ".md"}
PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def _set_common_metadata(doc: Document, src_path: Path, extra: dict | None = None) -> None:
    """Set standard metadata keys for consistent citations/debug."""
    doc.metadata["source"] = src_path.name
    doc.metadata["fullpath"] = str(src_path.resolve())
    if extra:
        doc.metadata.update(extra)


def _ocr_image_path(img_path: Path) -> str:
    """Run OCR on a single image file. Returns extracted text (may be '')."""
    if not OCR_IMAGE_OK:
        print(f"[loaders] OCR skipped: Pillow/pytesseract not installed for image {img_path.name}")
        return ""
    try:
        with Image.open(str(img_path)) as im:
            return pytesseract.image_to_string(im) or ""
    except Exception as e:
        print(f"[loaders] OCR image error on {img_path.name}: {e}")
        return ""


def _ocr_pdf_path(pdf_path: Path) -> List[Document]:
    """Convert a PDF to images and OCR each page. Returns a list of page Documents."""
    if not (OCR_IMAGE_OK and OCR_PDF_OK):
        print(f"[loaders] OCR skipped: Missing deps (pytesseract/Pillow/pdf2image) for {pdf_path.name}")
        return []

    docs: List[Document] = []
    try:
        # Higher DPI improves OCR accuracy (trade-off: speed/memory)
        pages = convert_from_path(str(pdf_path), dpi=300)
    except Exception as e:
        print(f"[loaders] pdf2image failed on {pdf_path.name}: {e}")
        return []

    for idx, img in enumerate(pages, start=1):
        try:
            text = pytesseract.image_to_string(img) or ""
        except Exception as e:
            print(f"[loaders] OCR page {idx} failed for {pdf_path.name}: {e}")
            text = ""

        if text.strip():
            d = Document(page_content=text, metadata={})
            _set_common_metadata(d, pdf_path, {"page": idx, "ocr": True})
            docs.append(d)

    if not docs:
        print(f"[loaders] OCR produced no text for {pdf_path.name}")
    return docs


def load_documents(docs_dir: str) -> List[Document]:
    """
    Load documents from a directory (recursively).

    - .txt/.md via TextLoader
    - .pdf via PyPDFLoader; if no text found, fall back to OCR (if available)
    - images (.png/.jpg/.jpeg/.tif/.tiff/.bmp/.webp) via OCR (if available)

    Every Document gets metadata:
      - source: filename (shown in chatbot citations)
      - fullpath: absolute path (helpful for debugging)
      - page: only for PDFs (and OCR pages) when available
      - ocr: True when the text came from OCR
    """
    base = Path(docs_dir)
    if not base.exists():
        print(f"[loaders] docs_dir does not exist: {docs_dir}")
        return []

    all_docs: List[Document] = []

    for p in base.rglob("*"):
        if not p.is_file():
            continue

        ext = p.suffix.lower()

        # ---------- Plain text / markdown ----------
        if ext in TEXT_EXTS:
            try:
                loader = TextLoader(str(p), encoding="utf-8")
                loaded = loader.load()
                for d in loaded:
                    _set_common_metadata(d, p)
                all_docs.extend(loaded)
            except Exception as e:
                print(f"[loaders] Text load failed for {p.name}: {e}")
            continue

        # ---------- PDF (digital text first, then OCR fallback) ----------
        if ext in PDF_EXTS:
            try:
                loader = PyPDFLoader(str(p))
                loaded = loader.load()  # one Document per page w/ metadata["page"]
            except Exception as e:
                print(f"[loaders] PyPDFLoader failed for {p.name}: {e}")
                loaded = []

            # Set metadata for digital pages
            for d in loaded:
                page_no = d.metadata.get("page") or d.metadata.get("page_number")
                extra = {"page": page_no} if page_no is not None else {}
                _set_common_metadata(d, p, extra)

            # If digital text is effectively empty, try OCR fallback
            has_text = any((d.page_content or "").strip() for d in loaded)
            if not has_text:
                ocr_docs = _ocr_pdf_path(p)
                if ocr_docs:
                    all_docs.extend(ocr_docs)
                else:
                    # If OCR not available or also empty, keep the (empty) digital docs
                    # so the system still indexes filenames for future updates.
                    all_docs.extend(loaded)
            else:
                all_docs.extend(loaded)
            continue

        # ---------- Image files via OCR ----------
        if ext in IMAGE_EXTS:
            text = _ocr_image_path(p)
            if text.strip():
                d = Document(page_content=text, metadata={})
                _set_common_metadata(d, p, {"ocr": True})
                all_docs.append(d)
            else:
                # keep a stub doc with empty content? Usually better to skip entirely.
                print(f"[loaders] No OCR text extracted from image {p.name}")
            continue

        # ---------- Unhandled extension ----------
        # Silently skip other file types
        # print(f"[loaders] Skipping unsupported file: {p.name}")

    print(f"[loaders] Loaded {len(all_docs)} documents from {docs_dir}")
    return all_docs
