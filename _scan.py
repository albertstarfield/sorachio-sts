import ast
import os
import re
import sys

SRC = '/Users/albertstarfield/Documents/misc/AdaptiveSystem/sorachio-sts'
SKIP_FILES = {'utils/sabotage_verifier.py'}
violations = []

def should_skip(filepath):
    rel = os.path.relpath(filepath, SRC)
    for s in SKIP_FILES:
        if rel == s or rel.endswith('/' + s):
            return True
    return False

def has_nosec(lines, lineno, window=2):
    for k in range(max(0, lineno - window), min(len(lines), lineno + window + 1)):
        if 'nosec' in lines[k]:
            return True
    return False

for dirpath, _, filenames in os.walk(SRC):
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        fpath = os.path.join(dirpath, fn)
        if should_skip(fpath):
            continue
        rel = os.path.relpath(fpath, SRC)
        try:
            with open(fpath) as f:
                content = f.read()
            lines = content.splitlines()
            tree = ast.parse(content)
        except:
            continue

        # === 1. INTEGRATION_CONTRACT: **kwargs or >10 params ===
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_kwargs = node.args.kwarg is not None
                num_params = len(node.args.args)
                if num_params > 10 or has_kwargs:
                    if has_nosec(lines, node.lineno - 1):
                        continue
                    violations.append(('INTEGRATION_CONTRACT', rel, node.lineno, node.name, 
                                      f'kwargs={has_kwargs} params={num_params}'))

        # === 2. FUNCTION_NO_DOCUMENTATION: functions missing docstrings ===
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private/test functions and dunder methods
                if node.name.startswith('_') or node.name.startswith('test_'):
                    continue
                    
                # Check if has docstring
                has_docstring = False
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    has_docstring = True
                
                if has_docstring:
                    continue
                    
                # Check if def line has # comment (verifier accepts this)
                defline = lines[node.lineno - 1] if node.lineno <= len(lines) else ''
                # Check after the colon on the def line
                colon_pos = defline.find(':')
                if colon_pos >= 0 and '#' in defline[colon_pos:]:
                    continue
                    
                # Check prev line for comment
                if node.lineno >= 2:
                    prevline = lines[node.lineno - 2].strip()
                    if prevline.startswith('#'):
                        continue
                
                # Check next non-empty line for comment
                j = node.lineno
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                if j < len(lines) and lines[j].strip().startswith('#'):
                    continue
                    
                # Check if inside a class (methods often inherit docs)
                # Still flag them per verifier logic
                    
                violations.append(('FUNCTION_NO_DOCUMENTATION', rel, node.lineno, node.name, defline.strip()[:80]))

        # === 3. SOFTLOCK_RISK: subprocess without timeout ===
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = ''
                if isinstance(func, ast.Attribute):
                    if func.attr in ('run', 'Popen', 'call', 'check_output', 'check_call'):
                        if isinstance(func.value, ast.Name) and func.value.id == 'subprocess':
                            name = func.attr
                
                if name:
                    # Check for timeout keyword
                    has_timeout = False
                    for kw in node.keywords:
                        if kw.arg == 'timeout':
                            has_timeout = True
                            break
                    
                    if has_timeout:
                        continue
                    if has_nosec(lines, node.lineno - 1):
                        continue
                    
                    # Check if inside try/except
                    in_try = False
                    for k in range(max(0, node.lineno - 10), node.lineno):
                        if k < len(lines):
                            stripped = lines[k].strip()
                            if stripped.startswith(('try:', 'except')):
                                in_try = True
                                break
                    
                    if in_try:
                        continue
                    
                    violations.append(('SOFTLOCK_RISK', rel, node.lineno, name, 
                                      lines[node.lineno - 1].strip()[:80]))

        # === 4. RESOURCE_LEAK: bare open() ===
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'\w+\s*=\s*open\(', stripped) and 'with ' not in stripped:
                if has_nosec(lines, i):
                    continue
                violations.append(('RESOURCE_LEAK', rel, i + 1, 'bare open()', stripped[:80]))

        # === 5. GIVING_UP_BANNED: sys.exit without nosec ===
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'sys.exit(' in stripped:
                if has_nosec(lines, i):
                    continue
                violations.append(('GIVING_UP_BANNED', rel, i + 1, 'sys.exit()', stripped[:80]))

        # === 6. SEGFAULT_REFERENCE: segfault without approved comment ===
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'segfault' in stripped.lower():
                if any(x in stripped.lower() for x in ['resurrection', 'segfault handler']):
                    continue
                if has_nosec(lines, i):
                    continue
                violations.append(('SEGFAULT_REFERENCE', rel, i + 1, 'segfault ref', stripped[:80]))

        # === 7. STALE_FLAG ===
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == 'STALE_FLAG' or stripped == '"STALE_FLAG"' or stripped == "'STALE_FLAG'":
                if has_nosec(lines, i):
                    continue
                violations.append(('STALE_FLAG', rel, i + 1, 'stale flag', stripped[:80]))

        # === 8. ASSERTION_SCANNER: assert True ===
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == 'assert True' or stripped.startswith('assert True'):
                violations.append(('ASSERTION_SCANNER', rel, i + 1, 'assert True', stripped[:80]))

from collections import defaultdict
by_cat = defaultdict(list)
for v in violations:
    by_cat[v[0]].append(v)

for cat in sorted(by_cat.keys()):
    items = by_cat[cat]
    print(f'\n=== {cat} ({len(items)}) ===')
    for v in items:
        print(f'  {v[1]}:{v[2]} [{v[3]}] {v[4]}')

print(f'\nTotal: {len(violations)}')
