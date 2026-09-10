#!/usr/bin/env python3
"""Check ruff E501 violations and save to file."""
import json
import subprocess

r = subprocess.run(
    ['python3', '-m', 'ruff', 'check', 'utils/sabotage_verifier.py',
     '--select', 'E501', '--output-format', 'json', '--no-fix'],
    capture_output=True, text=True, timeout=300
)
data = json.loads(r.stdout)
e501s = [v for v in data if v.get('code') == 'E501']

with open('_ruff_final.txt', 'w') as f:
    f.write('E501: ' + str(len(e501s)) + '\n')
    for v in e501s:
        f.write('Line ' + str(v['location']['row']) + '\n')

print('E501: ' + str(len(e501s)))
