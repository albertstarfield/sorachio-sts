#!/usr/bin/env python3
"""Diagnostic: count remaining E501 violations and save report."""
import json
import subprocess

r = subprocess.run(
    ['python3', '-m', 'ruff', 'check', '.', '--select', 'E501', '--output-format', 'json', '--no-fix'],
    capture_output=True, text=True, timeout=300
)
data = json.loads(r.stdout)
e501s = [v for v in data if v.get('code') == 'E501']

with open('_e501_report.txt', 'w') as f:
    f.write(f'Total E501 violations: {len(e501s)}\n')
    f.write(f'Return code: {r.returncode}\n\n')

    # Group by file
    by_file = {}
    for v in e501s:
        fn = v['filename'].replace('/Users/albertstarfield/Documents/misc/AdaptiveSystem/sorachio-sts/', '')
        by_file.setdefault(fn, []).append(v)

    for fn, violations in sorted(by_file.items()):
        f.write(f'--- {fn} ({len(violations)} violations) ---\n')
        for v in violations:
            row = v['location']['row']
            msg = v.get('message', '')
            f.write(f'  Line {row}: {msg}\n')
        f.write('\n')

print(f'Done. Total E501: {len(e501s)}. Report saved to _e501_report.txt')
