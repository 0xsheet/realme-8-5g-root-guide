"""Reject accidentally tracked private artifacts and common credential formats."""
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
files = [root / n.decode() for n in result.stdout.split(b"\0") if n]
patterns = [re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
            re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
            re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----")]
bad = []
for path in files:
    rel = path.relative_to(root)
    if rel.parts[0] in {"local", ".venv"} or path.suffix.lower() in {
        ".bin", ".img", ".apk", ".zip", ".whl", ".log"
    } or path.name in {"hwparam.json", ".state"} or path.name.startswith(".env"):
        bad.append(str(rel) + ": private/binary artifact")
        continue
    if path.is_file():
        data = path.read_text(errors="replace")
        if any(pattern.search(data) for pattern in patterns):
            bad.append(str(rel) + ": credential-like content")
if bad:
    print("Publication refused:\n" + "\n".join(bad), file=sys.stderr)
    raise SystemExit(1)
print(f"Public-tree check passed for {len(files)} tracked files.")
