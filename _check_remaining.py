#!/usr/bin/env python3
"""Check remaining E501 violations."""
import json
import subprocess

r = subprocess.run(
    ['python3', '-m', 'ruff', 'check', 'utils/sabotage_verifier.py', '--select', 'E501', '--output-format', 'json', '--no-fix'],
    capture_output=True, text=True, timeout=300
)
data = json.loads(r.stdout)
e501s = [v for v in data if v.get('code') == 'E501']

with open('_e501_remaining.txt', 'w') as f:
    f.write(f'Remaining E501: {len(e501s)}\n\n')
    for v in e501s:
        row = v['location']['row']
        msg = v.get('message', '')
        f.write(f'Line {row}: {msg}\n')

print(f'Done: {len(e501s)} violations')
