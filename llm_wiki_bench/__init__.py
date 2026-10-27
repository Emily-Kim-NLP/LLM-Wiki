"""LLM-Wiki benchmark package.

Offline wiki construction pipeline + Retrieval-as-Reasoning agent +
answer-quality evaluation for multi-hop QA datasets
(HotpotQA / MuSiQue / 2WikiMultiHopQA).
"""

import sys as _sys
from pathlib import Path as _Path

# Ensure the package directory is on sys.path so that sibling modules
# (bench_config, llm_client, bench_ingest, etc.) can import each other
# with plain `import <name>` statements.
_PKG_DIR = _Path(__file__).parent
if str(_PKG_DIR) not in _sys.path:
    _sys.path.insert(0, str(_PKG_DIR))

# [국회 시연] 시연 순서대로 파일 이름 앞에 번호를 붙였다 (1_preprocess_assembly.py … 10_evaluate.py).
# 숫자로 시작하는 이름은 import 문에 쓸 수 없으므로, 원본 코드의 `import bench_config` 같은 문장이
# 그대로 동작하도록 원래 이름 → 번호 붙은 파일로 연결한다.
import importlib.util as _ilu
import re as _re


class _NumberedModuleFinder:
    _files = {_re.sub(r"^\d+_", "", p.stem): p for p in _PKG_DIR.glob("[0-9]*_*.py")}

    def find_spec(self, name, path=None, target=None):
        if name in self._files:
            return _ilu.spec_from_file_location(name, self._files[name])
        return None


_sys.meta_path.insert(0, _NumberedModuleFinder())

__all__ = [
    # Compilation pipeline
    "bench_config",
    "llm_client",
    "bench_ingest",
    "bench_error_book",
    "preprocess_bench",
    "download_datasets",
    "run",
    # Retrieval & evaluation
    "wiki_retriever",
    "wiki_agent",
    "run_qa",
    "evaluate",
]
