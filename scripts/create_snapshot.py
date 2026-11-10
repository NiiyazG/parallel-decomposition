#!/usr/bin/env python3
"""Create an immutable, content-addressed input snapshot."""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--input", action="append", required=True, type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"REFUSE: snapshot directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for source in args.input:
        source = source.resolve()
        if not source.is_file():
            raise SystemExit(f"MISSING_INPUT: {source}")
        target = out / source.name
        if target.exists():
            raise SystemExit(f"NAME_COLLISION: {target.name}")
        shutil.copy2(source, target)
        entries.append({"name": target.name, "sha256": sha256(target), "size": target.stat().st_size})
    manifest = {"format": 1, "files": sorted(entries, key=lambda x: x["name"])}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "snapshot": str(out), "files": len(entries)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
