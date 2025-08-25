import json
import pathlib
import re
from typing import Any, Dict, List


class ProjectIndex:
    """Simple helper around the index produced by :mod:`analysis.indexer`."""

    def __init__(self, project_root: str):
        self.root = pathlib.Path(project_root)
        idx_path = self.root / '.cswarm' / 'index.json'
        if idx_path.exists():
            self.data: Dict[str, Any] = json.loads(idx_path.read_text(encoding='utf-8'))
        else:
            self.data = {'files': {}}

    def _file_source(self, rel: str) -> List[str]:
        try:
            return (self.root / rel).read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            return []

    def by_symbol(self, name: str) -> List[Dict[str, Any]]:
        results = []
        for rel, info in self.data.get('files', {}).items():
            for sym in info.get('symbols', []):
                if sym['name'] == name:
                    src = self._file_source(rel)
                    start = max(sym['lineno'] - 5, 0)
                    snippet = '\n'.join(src[start:start + 20])
                    results.append({'path': rel, 'symbol': sym, 'snippet': snippet})
        return results

    def by_path(self, rel: str) -> List[Dict[str, Any]]:
        info = self.data.get('files', {}).get(rel)
        if not info:
            return []
        src = self._file_source(rel)[:200]
        return [{'path': rel, 'summary': info.get('summary', ''), 'snippet': '\n'.join(src)}]

    def by_text(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
        tokens = re.findall(r"[A-Za-z_]{3,}", text.lower())
        scored = []
        for rel, info in self.data.get('files', {}).items():
            score = sum(info.get('terms', {}).get(tok, 0) for tok in tokens)
            if score:
                src = self._file_source(rel)[:40]
                scored.append((score, {
                    'path': rel,
                    'summary': info.get('summary', ''),
                    'snippet': '\n'.join(src)
                }))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]
