import ast
import json
import pathlib
import re
from typing import Dict, List, Tuple, Any

IGNORED_DIRS = {'.git', 'venv', '__pycache__', '.cswarm'}


def iter_python_files(root: pathlib.Path):
    """Yield python files under *root* ignoring virtualenvs and git dirs."""
    for path in root.rglob('*.py'):
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS or part.startswith('.') for part in rel_parts[:-1]):
            continue
        yield path


def parse_file(path: pathlib.Path) -> Dict[str, Any]:
    """Return summary information for a python source file."""
    source = path.read_text(encoding='utf-8', errors='ignore')
    try:
        tree = ast.parse(source)
    except Exception:
        tree = ast.parse(compile(source, str(path), 'exec'))

    # file level docstring
    summary = ast.get_docstring(tree) or ''

    symbols = []
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append({
                'name': node.name,
                'lineno': node.lineno,
                'doc': ast.get_docstring(node) or ''
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])

    # naive term frequency as lightweight "embedding"
    terms: Dict[str, int] = {}
    for tok in re.findall(r"[A-Za-z_]{3,}", source.lower()):
        terms[tok] = terms.get(tok, 0) + 1

    return {
        'summary': summary,
        'symbols': symbols,
        'imports': sorted(imports),
        'terms': terms,
    }


def build_index(project_root: str, output: str | None = None) -> Dict[str, Any]:
    """
    Traverse *project_root*, parse python files and build a lightweight
    dependency and term index. The index is written to ``.cswarm/index.json``
    unless *output* is provided. Returns the in-memory index dictionary.
    """
    root = pathlib.Path(project_root)
    data: Dict[str, Any] = {'files': {}}
    for path in iter_python_files(root):
        rel = str(path.relative_to(root))
        data['files'][rel] = parse_file(path)

    out_path = pathlib.Path(output) if output else root / '.cswarm' / 'index.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


if __name__ == '__main__':
    import sys
    build_index(sys.argv[1] if len(sys.argv) > 1 else '.')
