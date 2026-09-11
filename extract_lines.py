import json
import subprocess

result = subprocess.run(
    ["python3", "-m", "ruff", "check", "utils/sabotage_verifier.py",
     "--select", "E501", "--output-format=json"],
    capture_output=True, text=True, timeout=300
)
data = json.loads(result.stdout)
lines = sorted(set(d['location']['row'] for d in data))
print(f"Total violations: {len(data)}")
print(f"Unique lines: {len(lines)}")
print(f"Lines: {json.dumps(lines)}")
for line_num in lines:
    for d in data:
        if d['location']['row'] == line_num:
            print(f"  Line {line_num}: {d['message']}")
            break
