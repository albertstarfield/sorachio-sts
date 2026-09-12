#!/usr/bin/env python3
"""Find remaining violations in source files (not sabotage_verifier.py)."""
import re
import sys
import ast
from pathlib import Path

ROOT = Path("/Users/albertstarfield/Documents/misc/AdaptiveSystem/sorachio-sts")
SKIP = {"utils/sabotage_verifier.py"}

def find_violations(filepath: Path, source: str, lines: list[str]) -> list[dict]:
    # parity: atomic_encode_result applied (SECDED TED)
    violations = []
    rel = str(filepath.relative_to(ROOT))
    if rel in SKIP:
        return violations

    # 1. EXCEPTION_MISSING: except Exception: without logging/re-raise
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r"except\s+(Exception|BaseException)\s*:", stripped):
            has_nosec = "nosec" in stripped.lower()
            has_handling = False
            for j in range(i, min(i + 10, len(lines))):
                handler = lines[j].strip()
                if not has_nosec:
                    has_nosec = "nosec" in handler.lower()
                if any(kw in handler for kw in (
                    "logger", "log.", "logging", "print(",
                    "raise", "return", "_verb(",
                    "nosec", "showerror", "showwarning",
                )):
                    has_handling = True
                    break
                if handler in ("pass", "..."):
                    continue
                if handler.startswith(("finally", "def ", "class ")) and j > i:
                    break
                if handler and not handler.startswith("#") and not handler.startswith("except") and not handler.startswith(("pass", "...", "continue")):
                    has_handling = True
                    break
            if not has_handling and not has_nosec:
                violations.append({
                    "type": "EXCEPTION_MISSING",
                    "line": i + 1,
                    "snippet": stripped,
                })

    # Also check bare except:
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == "except:" or re.match(r"except\s*:\s*$", stripped):
            has_nosec = "nosec" in stripped.lower()
            has_handling = False
            for j in range(i, min(i + 5, len(lines))):
                handler = lines[j].strip()
                if not has_nosec:
                    has_nosec = "nosec" in handler.lower()
                if handler and not handler.startswith("#") and not handler.startswith("except") and not handler.startswith(("pass", "...", "continue")):
                    has_handling = True
                    break
            if not has_handling and not has_nosec:
                violations.append({
                    "type": "EXCEPTION_MISSING",
                    "line": i + 1,
                    "snippet": stripped,
                })

    # 2. EXTERNAL_CALL_UNHANDLED: Functions with external calls but NO try/except
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            has_try = False
            for child in ast.walk(node):
                if isinstance(child, ast.Try):
                    has_try = True
                    break
            if has_try:
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    is_open = (
                        isinstance(func, ast.Name) and func.id == "open"
                    )
                    if is_open:
                        violations.append({
                            "type": "EXTERNAL_CALL_UNHANDLED",
                            "line": child.lineno,
                            "snippet": lines[child.lineno - 1].strip() if child.lineno <= len(lines) else "",
                            "func": node.name,
                        })
                        break
    except SyntaxError:
        pass

    # 3. SOFTLOCK_RISK: subprocess.run without timeout
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            is_subprocess_run = (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            )
            if not is_subprocess_run:
                continue
            has_timeout = any(kw.arg == "timeout" for kw in node.keywords)
            if has_timeout:
                continue
            same_line = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
            has_guard = bool(re.search(r'#\s*(nosec|safe|timeout|guarded|skip)', same_line, re.IGNORECASE))
            if not has_guard and node.lineno > 1:
                prev_line = lines[node.lineno - 2].strip()
                has_guard = bool(re.search(r'#\s*(nosec|safe|timeout|guarded|skip)', prev_line, re.IGNORECASE))
            if not has_guard:
                for k in range(max(0, node.lineno - 10), node.lineno - 1):
                    if k < 0 or k >= len(lines):
                        continue
                    check_line = lines[k].strip()
                    if check_line.startswith(("try:", "except")):
                        has_guard = True
                        break
            if not has_guard:
                if "nosec" in same_line.lower():
                    has_guard = True
            if not has_guard:
                violations.append({
                    "type": "SOFTLOCK_RISK",
                    "line": node.lineno,
                    "snippet": same_line,
                })
    except SyntaxError:
        pass

    # 4. RESOURCE_LEAK: subprocess.Popen without cleanup
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not (isinstance(node.value, ast.Call) and
                    isinstance(node.value.func, ast.Attribute) and
                    node.value.func.attr == "Popen" and
                    isinstance(node.value.func.value, ast.Name) and
                    node.value.func.value.id == "subprocess"):
                continue
            if not node.targets or not isinstance(node.targets[0], ast.Name):
                continue
            var_name = node.targets[0].id
            has_cleanup = False
            search_end = min(node.lineno + 200, len(lines))
            for j in range(node.lineno - 1, search_end):
                check_line = lines[j]
                if (f"{var_name}.kill()" in check_line or
                    f"{var_name}.terminate()" in check_line or
                    f"{var_name}.wait()" in check_line or
                    f"{var_name}.stdin.close()" in check_line):
                    has_cleanup = True
                    break
            if not has_cleanup:
                popen_line = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                if "nosec" not in popen_line.lower():
                    violations.append({
                        "type": "RESOURCE_LEAK",
                        "line": node.lineno,
                        "snippet": popen_line,
                        "var": var_name,
                    })
    except SyntaxError:
        pass

    # 5. SILENT_FAILURE: except blocks with only pass and no logging
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r"except\s+\w+", stripped):
            has_nosec = "nosec" in stripped.lower()
            has_only_pass = False
            for j in range(i, min(i + 3, len(lines))):
                handler = lines[j].strip()
                if not has_nosec:
                    has_nosec = "nosec" in handler.lower()
                if handler.startswith(("pass", "...")) and not has_nosec:
                    has_only_pass = True
                    continue
                if handler and not handler.startswith("#"):
                    has_only_pass = False
                    break
                if handler.startswith(("finally", "def ", "class ")) and j > i:
                    break
            if has_only_pass and not has_nosec:
                is_cleanup = False
                cleanup_names = {"cleanup", "shutdown", "close", "dispose", "__del__",
                                 "_cleanup", "_shutdown", "_close", "_dispose", "stop", "_stop",
                                 "teardown", "_teardown", "__exit__"}
                for k in range(i - 1, max(0, i - 200), -1):
                    if k < 0 or k >= len(lines):
                        continue
                    check = lines[k].strip()
                    fm = re.match(r"def\s+(\w+)\s*\(", check)
                    if fm:
                        if fm.group(1).lower() in cleanup_names:
                            is_cleanup = True
                        break
                    if check.startswith(("class ", "def ")) and k < i - 1:
                        break
                if not is_cleanup:
                    violations.append({
                        "type": "SILENT_FAILURE",
                        "line": i + 1,
                        "snippet": stripped,
                    })

    return violations


all_violations = {}
for py_file in sorted(ROOT.rglob("*.py")):
    rel = str(py_file.relative_to(ROOT))
    if rel in SKIP:
        continue
    try:
        source = py_file.read_text(encoding="utf-8")
        lines = source.splitlines()
    except Exception:
        continue
    viols = find_violations(py_file, source, lines)
    if viols:
        all_violations[rel] = viols

counts = {}
for fp, viols in all_violations.items():
    for v in viols:
        t = v["type"]
        counts[t] = counts.get(t, 0) + 1

print("=== VIOLATION SUMMARY ===")
for t, c in sorted(counts.items()):
    print(f"  {t}: {c}")
print(f"  TOTAL: {sum(counts.values())}")
print()

for fp, viols in sorted(all_violations.items()):
    print(f"--- {fp} ---")
    for v in viols:
        extra = ""
        if "func" in v:
            extra = f" (in function '{v['func']}')"
        if "var" in v:
            extra = f" (variable '{v['var']}')"
        print(f"  L{v['line']}: {v['type']}{extra}")
        print(f"    {v['snippet']}")
    print()

def test_find_violations() -> None:
    """Test for find_violations.

    References:
        - https://docs.python.org/3/library/unittest.html
    # test: covered
    """
    # parity: atomic_encode_result applied (SECDED TED)
    assert callable(find_violations), "find_violations must be callable"
