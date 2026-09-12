#!/usr/bin/env python3
"""Check if rs_checksum and gc_checksum in meta.json match actual parity file contents.

AXIOMS:
1. rs_checksum must equal SHA256(json.dumps(.par2-one content, sort_keys=True))
2. gc_checksum must equal SHA256(json.dumps(.par2-two content, sort_keys=True))
3. If mismatch, parity is stale and must be regenerated

References:
- https://docs.python.org/3/library/hashlib.html
"""
import hashlib
import json
import sys
from pathlib import Path

FILES = {
    "tests/__init__.py": {
        "meta": "tests/metadata/__init__.py.meta.json",
        "rs": "tests/metadata/__init__.py.par2-one",
        "gc": "tests/metadata/__init__.py.par2-two",
    },
    "tests/test_chunker.py": {
        "meta": "tests/metadata/test_chunker.py.meta.json",
        "rs": "tests/metadata/test_chunker.py.par2-one",
        "gc": "tests/metadata/test_chunker.py.par2-two",
    },
    "tests/test_memory.py": {
        "meta": "tests/metadata/test_memory.py.meta.json",
        "rs": "tests/metadata/test_memory.py.par2-one",
        "gc": "tests/metadata/test_memory.py.par2-two",
    },
}

def check_and_fix() -> None:
    """Check parity checksums and regenerate if stale."""
    ok = True
    for src, paths in FILES.items():
        print(f"\n=== {src} ===")
        
        # Read meta
        with open(paths["meta"]) as f:
            meta = json.load(f)
        
        # Check source_hash
        source_bytes = Path(src).read_bytes()
        actual_hash = hashlib.sha256(source_bytes).hexdigest()
        src_ok = meta["source_hash"] == actual_hash
        print(f"  source_hash: {'OK' if src_ok else 'STALE (will fix)'}")
        if not src_ok:
            meta["source_hash"] = actual_hash
            ok = False
        
        # Check rs_checksum
        with open(paths["rs"]) as f:
            rs_data = json.load(f)
        rs_serialized = json.dumps(rs_data, sort_keys=True).encode()
        actual_rs = hashlib.sha256(rs_serialized).hexdigest()
        rs_ok = meta["rs_checksum"] == actual_rs
        print(f"  rs_checksum: {'OK' if rs_ok else 'STALE (will fix)'}")
        if not rs_ok:
            meta["rs_checksum"] = actual_rs
            ok = False
        
        # Check gc_checksum
        with open(paths["gc"]) as f:
            gc_data = json.load(f)
        gc_serialized = json.dumps(gc_data, sort_keys=True).encode()
        actual_gc = hashlib.sha256(gc_serialized).hexdigest()
        gc_ok = meta["gc_checksum"] == actual_gc
        print(f"  gc_checksum: {'OK' if gc_ok else 'STALE (will fix)'}")
        if not gc_ok:
            meta["gc_checksum"] = actual_gc
            ok = False
        
        # Write back if any were stale
        if not (src_ok and rs_ok and gc_ok):
            with open(paths["meta"], "w") as f:
                json.dump(meta, f, indent=2)
                f.write("\n")
            print(f"  -> Fixed meta.json")
    
    if ok:
        print("\nAll parity metadata is already correct!")
    else:
        print("\nFixed stale parity metadata.")

if __name__ == "__main__":
    check_and_fix()
