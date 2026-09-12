#!/usr/bin/env python3
"""Precise scanner replicating sabotage_verifier.py logic for two patterns only.

PYTHON_FUNCTION_COVERAGE (regex-based, mirrors check_python_coverage):
  - Uses _FUNC_RE regex to find def/async def functions
  - Skips: test files, sabotage_verifier.py, private funcs (starts with _ except __init__)
  - Checks: docstring (forward 5 lines), type hints, test reference (forward 8 lines)
  - Skips if line has nosec

FUNCTION_NO_DOCUMENTATION (regex-based, mirrors check_function_comments for Python):
  - Uses same def regex
  - Checks: docstring after colon OR comment before/after def
"""
import re
import os
import sys
import json

PROJECT_ROOT = "/Users/albertstarfield/Documents/misc/AdaptiveSystem/sorachio-sts"

# Exact regex from sabotage_verifier.py line 17712
_FUNC_RE = re.compile(
    r"^[^\S\n]*(?:async[^\S\n]+)?def[^\S\n]+(\w+)[^\S\n]*\(", re.MULTILINE
)

# Exact regex from sabotage_verifier.py line 15833
_FUNC_RE_DOC = re.compile(
    r"^[^\S\n]*(?:async[^\S\n]+)?def[^\S\n]+\w+[^\S\n]*\(", re.MULTILINE
)


def is_excluded(filepath):
    """Check if file should be excluded from scanning."""
    rel = os.path.relpath(filepath, PROJECT_ROOT)
    basename = os.path.basename(filepath)
    
    # Skip test files
    if "/tests/" in rel or rel.startswith("tests/"):
        return True
    if basename.startswith("test_") or basename.endswith("_test.py"):
        return True
    if "/test_" in rel:
        return True
    
    # Skip sabotage_verifier.py
    if basename == "sabotage_verifier.py":
        return True
    
    # Skip this script
    if basename == "precise_scan.py":
        return True
    
    return False


def has_nosec(lines, line_num_1based):
    """Check if line has nosec annotation."""
    if line_num_1based < 1 or line_num_1based > len(lines):
        return False
    return "nosec" in lines[line_num_1based - 1].lower()


def check_python_coverage_violations(filepath, lines):
    """Find PYTHON_FUNCTION_COVERAGE violations (mirrors check_python_coverage)."""
    violations = []
    source = "\n".join(lines)
    
    for match in _FUNC_RE.finditer(source):
        func_name = match.group(1)
        func_line = source[:match.start()].count("\n") + 1  # 1-based
        line_idx = func_line - 1  # 0-based
        
        # Skip private/dunder methods (except __init__)
        if func_name.startswith("_") and func_name != "__init__":
            continue
        
        # Skip if nosec
        if has_nosec(lines, func_line):
            continue
        
        # Check 1: Docstring
        has_docstring = False
        for j in range(line_idx + 1, min(line_idx + 5, len(lines))):
            if j >= len(lines):
                break
            stripped = lines[j].strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                has_docstring = True
                break
            if stripped and not stripped.startswith("#"):
                break
        
        # Check 2: Type hints
        has_type_hints = False
        func_sig = lines[line_idx] if line_idx < len(lines) else ""
        if "->" in func_sig or ": " in func_sig:
            has_type_hints = True
        if not has_type_hints:
            for j in range(line_idx, min(line_idx + 3, len(lines))):
                if j >= len(lines):
                    break
                if "->" in lines[j]:
                    has_type_hints = True
                    break
        
        # Check 3: Test reference
        has_test_ref = False
        for j in range(line_idx, min(line_idx + 8, len(lines))):
            if j >= len(lines):
                break
            check_line = lines[j].lower()
            if ("test:" in check_line or "test_ref:" in check_line
                    or "coverage:" in check_line or "tested by" in check_line
                    or "unit test" in check_line or "pytest" in check_line):
                has_test_ref = True
                break
        
        # Report
        issues = []
        if not has_docstring:
            issues.append("NO_DOCSTRING")
        if not has_type_hints:
            issues.append("NO_TYPE_HINTS")
        if not has_test_ref:
            issues.append("NO_TEST_REF")
        
        if issues:
            violations.append({
                "file": filepath,
                "func_name": func_name,
                "line": func_line,
                "category": "PYTHON_FUNCTION_COVERAGE",
                "issues": issues,
                "has_docstring": has_docstring,
                "has_type_hints": has_type_hints,
                "has_test_ref": has_test_ref,
            })
    
    return violations


def check_function_no_doc_violations(filepath, lines):
    """Find FUNCTION_NO_DOCUMENTATION violations (mirrors check_function_comments for Python)."""
    violations = []
    
    for i, line in enumerate(lines):
        m = re.match(r"^[^\S\n]*(?:async[^\S\n]+)?def[^\S\n]+\w+[^\S\n]*\(", line)
        if not m:
            continue
        
        # Find the colon ending the signature
        colon_idx = line.find(":")
        if colon_idx == -1:
            continue
        
        # Find the actual colon (skip colons in type annotations)
        actual_colon = i
        for scan in range(i, min(i + 10, len(lines))):
            if lines[scan].rstrip().endswith(":") or ": #" in lines[scan]:
                actual_colon = scan
                break
        
        # Check lines right after the signature for docstring or comment
        has_doc = False
        j = actual_colon + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j < len(lines):
            stripped = lines[j].strip()
            if stripped.startswith(('"""', "'''")):
                has_doc = True
        
        # Check lines before def for comment
        for k in range(max(0, i - 3), i):
            if k < 0 or k >= len(lines):
                continue
            if lines[k].strip().startswith("#"):
                has_doc = True
                break
        
        # Check same line after colon for comment
        if "#" in line[line.find(":"):]:
            has_doc = True
        
        # Check line right after def for comment
        if not has_doc and j < len(lines) and lines[j].strip().startswith("#"):
            has_doc = True
        
        if not has_doc:
            func_name = re.search(r"def\s+(\w+)", line)
            fname = func_name.group(1) if func_name else "unknown"
            violations.append({
                "file": filepath,
                "func_name": fname,
                "line": i + 1,
                "category": "FUNCTION_NO_DOCUMENTATION",
            })
    
    return violations


def main():
    all_pfc = []  # PYTHON_FUNCTION_COVERAGE
    all_fnd = []  # FUNCTION_NO_DOCUMENTATION
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".") 
                   and d not in ("__pycache__", "node_modules", "venv", ".venv", "venv_runtime")]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(root, fname)
            if is_excluded(filepath):
                continue
            
            try:
                with open(filepath, "r") as f:
                    source = f.read()
                lines = source.split("\n")
            except Exception as e:
                print(f"ERROR reading {filepath}: {e}", file=sys.stderr)
                continue
            
            pfc = check_python_coverage_violations(filepath, lines)
            fnd = check_function_no_doc_violations(filepath, lines)
            all_pfc.extend(pfc)
            all_fnd.extend(fnd)
    
    # Deduplicate FND: if a function is already in PFC, skip FND for it
    pfc_keys = {(v["file"], v["func_name"], v["line"]) for v in all_pfc}
    fnd_filtered = [v for v in all_fnd if (v["file"], v["func_name"], v["line"]) not in pfc_keys]
    
    # Print summary
    print(f"=== PYTHON_FUNCTION_COVERAGE violations: {len(all_pfc)} ===")
    by_file_pfc = {}
    for v in all_pfc:
        rel = os.path.relpath(v["file"], PROJECT_ROOT)
        if rel not in by_file_pfc:
            by_file_pfc[rel] = []
        by_file_pfc[rel].append(v)
    
    for fpath, violations in sorted(by_file_pfc.items()):
        print(f"\n  {fpath} ({len(violations)} violations):")
        for v in violations:
            print(f"    Line {v['line']}: {v['func_name']} — {', '.join(v['issues'])}")
    
    print(f"\n=== FUNCTION_NO_DOCUMENTATION violations: {len(fnd_filtered)} ===")
    by_file_fnd = {}
    for v in fnd_filtered:
        rel = os.path.relpath(v["file"], PROJECT_ROOT)
        if rel not in by_file_fnd:
            by_file_fnd[rel] = []
        by_file_fnd[rel].append(v)
    
    for fpath, violations in sorted(by_file_fnd.items()):
        print(f"\n  {fpath} ({len(violations)} violations):")
        for v in violations:
            print(f"    Line {v['line']}: {v['func_name']}")
    
    # Combined total
    # A function can appear in both PFC and FND
    all_violations = all_pfc + fnd_filtered
    # Deduplicate by (file, func_name, line)
    seen = set()
    unique = []
    for v in all_violations:
        key = (v["file"], v["func_name"], v["line"])
        if key not in seen:
            seen.add(key)
            unique.append(v)
    
    print(f"\n=== TOTAL UNIQUE VIOLATIONS: {len(unique)} ===")
    
    # Save for fix script
    with open(os.path.join(PROJECT_ROOT, ".tmp_violations.json"), "w") as f:
        json.dump({"pfc": all_pfc, "fnd": fnd_filtered, "unique": unique}, f, indent=2)
    
    print(f"Details saved to .tmp_violations.json")


if __name__ == "__main__":
    main()
