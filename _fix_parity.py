#!/usr/bin/env python3
"""Regenerate parity hashes for stale test files.

AXIOMS:
1. Source file SHA256 is the canonical content hash
2. meta.json source_hash must match the current file bytes
3. When source changes, parity metadata becomes stale

References:
- https://docs.python.org/3/library/hashlib.html
- https://docs.python.org/3/library/json.html
"""
import hashlib
import json
import sys
from pathlib import Path

# Files to regenerate parity for (source -> meta.json)
FILES = {
    "tests/__init__.py": "tests/metadata/__init__.py.meta.json",
    "tests/test_chunker.py": "tests/metadata/test_chunker.py.meta.json",
    "tests/test_memory.py": "tests/metadata/test_memory.py.meta.json",
}

def regenerate_all() -> None:
    """Recompute SHA256 hashes and update all meta.json files."""
    ok = True
    for src, meta_path in FILES.items():
        src_path = Path(src)
        meta_file = Path(meta_path)

        if not src_path.exists():
            print(f"ERROR: {src} not found", file=sys.stderr)
            ok = False
            continue

        if not meta_file.exists():
            print(f"ERROR: {meta_path} not found", file=sys.stderr)
            ok = False
            continue

        # Read source and compute hash
        source_bytes = src_path.read_bytes()
        new_hash = hashlib.sha256(source_bytes).hexdigest()

        # Read existing meta
        with open(meta_file) as f:
            meta = json.load(f)

        old_hash = meta.get("source_hash", "N/A")
        meta["source_hash"] = new_hash

        # Write updated meta
        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")

        changed = old_hash != new_hash
        status = "UPDATED" if changed else "UNCHANGED"
        print(f"{status}: {src}")
        print(f"  old: {old_hash[:16]}...")
        print(f"  new: {new_hash[:16]}...")

    if ok:
        print("\nAll parity hashes regenerated successfully.")
    else:
        print("\nSome files failed!", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    regenerate_all()
