from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import os
import secrets
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def state_dir(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        root = Path(explicit).expanduser()
    elif os.environ.get("AGENT_GOODPUT_DATA"):
        root = Path(os.environ["AGENT_GOODPUT_DATA"]).expanduser()
    elif os.environ.get("PLUGIN_DATA"):
        root = Path(os.environ["PLUGIN_DATA"]).expanduser()
    else:
        root = Path.cwd() / ".agent-goodput"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def atomic_write(path: Path, content: str, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, value: Any, *, mode: int = 0o600) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True) + "\n", mode=mode)


@contextlib.contextmanager
def file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        if fcntl is not None:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def load_or_create_secret(root: Path) -> bytes:
    path = root / "integrity.key"
    if path.exists():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_bytes()
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(secret)
        stream.flush()
        os.fsync(stream.fileno())
    return secret


def sign_value(value: Any, secret: bytes) -> str:
    return hmac.new(secret, canonical_json(value).encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(value: Any, signature: str, secret: bytes) -> bool:
    return hmac.compare_digest(sign_value(value, secret), signature)


def private_project_id(path: str | Path, secret: bytes) -> str:
    normalized = str(Path(path).expanduser().resolve())
    digest = hmac.new(secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"project_{digest[:16]}"


def bounded_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)] + "…"
