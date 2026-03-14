from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


class FileService:
    def __init__(self, allowed_root: str | None = None) -> None:
        root = Path(allowed_root) if allowed_root else Path.cwd()
        self._root = root.resolve()

    def _resolve_under_root(self, user_path: str) -> Path:
        p = Path(user_path)
        if not p.is_absolute():
            p = self._root / p
        resolved = p.resolve()
        if self._root not in resolved.parents and resolved != self._root:
            raise PermissionError("Path is outside allowed root")
        return resolved

    def create_folder(self, folder_path: str) -> dict[str, Any]:
        p = self._resolve_under_root(folder_path)
        p.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(p)}

    def rename_path(self, src_path: str, new_name: str) -> dict[str, Any]:
        src = self._resolve_under_root(src_path)
        if not src.exists():
            return {"ok": False, "error": "Source not found"}
        dst = src.with_name(new_name)
        dst = self._resolve_under_root(str(dst))
        src.rename(dst)
        return {"ok": True, "from": str(src), "to": str(dst)}

    def move_path(self, src_path: str, dst_path: str) -> dict[str, Any]:
        src = self._resolve_under_root(src_path)
        if not src.exists():
            return {"ok": False, "error": "Source not found"}
        dst = self._resolve_under_root(dst_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        out = shutil.move(str(src), str(dst))
        return {"ok": True, "from": str(src), "to": str(Path(out).resolve())}

    def delete_path(self, target_path: str) -> dict[str, Any]:
        p = self._resolve_under_root(target_path)
        if not p.exists():
            return {"ok": False, "error": "Target not found"}
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"ok": True, "path": str(p)}

    def find_files(self, query: str, max_results: int = 25) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return {"ok": False, "error": "Query is required"}

        results: list[str] = []
        # Simple name contains match (case-insensitive)
        q_lower = q.lower()
        for path in self._root.rglob("*"):
            try:
                name = path.name.lower()
                if q_lower in name:
                    results.append(str(path.resolve()))
                    if len(results) >= max_results:
                        break
            except Exception:
                continue

        return {"ok": True, "query": q, "results": results}
