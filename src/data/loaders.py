from pathlib import Path
from typing import List, Tuple

def load_folder(folder: str) -> List[Tuple[str, dict]]:
    texts, metas = [], []
    for p in Path(folder).rglob("*"):
        if p.suffix.lower() in {".txt", ".md"}:
            content = p.read_text(encoding="utf-8", errors="ignore")
            texts.append(content)
            metas.append({"path": str(p)})
    return list(zip(texts, metas))
