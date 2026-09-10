#!/usr/bin/env python3
"""Generate edit operations for all E501 violations."""
import json
import subprocess

r = subprocess.run(
    ['python3', '-m', 'ruff', 'check', 'utils/sabotage_verifier.py',
     '--select', 'E501', '--output-format', 'json', '--no-fix'],
    capture_output=True, text=True, timeout=300
)
data = json.loads(r.stdout)
e501s = [v for v in data if v.get('code') == 'E501']

# Sort by line length (longest first)
e501s.sort(key=lambda v: v['location']['row'])

print(f"Total E501 violations: {len(e501s)}")
print("\nLine numbers to fix:")
for v in e501s:
    print(f"  Line {v['location']['row']}")
