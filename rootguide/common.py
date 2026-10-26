import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "local"
PROFILE = ROOT / "profiles/rmx3241-f12.json"


class Refusal(RuntimeError):
    """An unmet precondition; no implicit fallback to a different device or image."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def private_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def save_json(path, data):
    path = Path(path)
    private_dir(path.parent)
    # Session files may contain device metadata. Never make them world-readable.
    with path.open("w", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(argv, timeout=30, check=True, **kwargs):
    result = subprocess.run([str(x) for x in argv], timeout=timeout,
                            capture_output=True, text=True, **kwargs)
    if check and result.returncode:
        raise Refusal(f"Command failed ({result.returncode}): {argv[0]}\n{result.stderr.strip()}")
    return result


def profile():
    return load_json(PROFILE)
