import ast
import os
import re

SRC = '.'
violations = []

for dp, _, fns in os.walk(SRC):
    for fn in fns:
        if not fn.endswith('.py'):
            continue
        if 'sabotage_verifier' in fn:
            continue
        fpath = os.path.join(dp, fn)
        try:
            with open(fpath) as f:
                content = f.read()
            lines = content.splitlines()
            tree = ast.parse(content)
        except:
            continue
        rel = os.path.relpath(fpath, SRC)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_kwargs = node.args.kwarg is not None
                num_params = len(node.args.args)
                if num_params > 10 or has_kwargs:
                    defline = lines[node.lineno - 1] if node.lineno <= len(lines) else ''
                    nextline = lines[node.lineno] if node.lineno < len(lines) else ''
                    prevline = lines[node.lineno - 2] if node.lineno >= 2 else ''
                    if 'nosec' in defline or 'nosec' in nextline or 'nosec' in prevline:
                        continue
                    violations.append(('IC', rel, node.lineno, node.name, f'kw={has_kwargs} p={num_params}'))

print(f'Total IC: {len(violations)}')
for v in violations:
    print(f'  {v[1]}:{v[2]} {v[3]} {v[4]}')
