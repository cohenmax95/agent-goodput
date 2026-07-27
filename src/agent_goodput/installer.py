from __future__ import annotations

import contextlib
import json
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import sha256_bytes, utc_now, write_json

_BUNDLE_PATHS = (
    ".codex-plugin",
    "hooks",
    "skills",
    "src",
)


@dataclass(frozen=True)
class InstallPlan:
    source: str
    target: str
    marketplace: str
    actions: tuple[str, ...]
    conflicts: tuple[str, ...]
    apply_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "marketplace": self.marketplace,
            "actions": list(self.actions),
            "conflicts": list(self.conflicts),
            "apply_allowed": self.apply_allowed,
        }


def _hash_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _install_bytes(relative: str, source_path: Path) -> bytes:
    content = source_path.read_bytes()
    if relative != "hooks/hooks.json":
        return content
    document = json.loads(content)
    expected = '/usr/bin/env python3 -B "$PLUGIN_ROOT/hooks/agent_goodput_hook.py"'
    replacement = f'{shlex.quote(sys.executable)} -B "$PLUGIN_ROOT/hooks/agent_goodput_hook.py"'
    commands = 0
    for groups in document["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                if hook.get("type") != "command":
                    continue
                if hook.get("command") != expected:
                    raise ValueError("unexpected packaged hook command")
                hook["command"] = replacement
                commands += 1
    if commands == 0:
        raise ValueError("packaged hooks contain no commands")
    return (json.dumps(document, indent=2) + "\n").encode()


def _install_hash(relative: str, source_path: Path) -> str:
    return sha256_bytes(_install_bytes(relative, source_path))


def _contains_symlink(path: Path, boundary: Path) -> bool:
    relative = path.relative_to(boundary)
    current = boundary
    if current.is_symlink():
        return True
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _packaged_files() -> dict[str, Path]:
    package_root = Path(__file__).resolve().parent
    assets_root = package_root / "assets"
    files: dict[str, Path] = {}
    for path in assets_root.rglob("*"):
        if path.is_symlink():
            raise ValueError("packaged plugin bundle contains a symlink")
        if path.is_file() and "__pycache__" not in path.parts:
            files[str(path.relative_to(assets_root))] = path
    for path in package_root.glob("*.py"):
        if path.is_symlink():
            raise ValueError("packaged plugin bundle contains a symlink")
        files[f"src/agent_goodput/{path.name}"] = path
    return files


def _source_files(source: Path) -> dict[str, Path]:
    if not (source / ".codex-plugin" / "plugin.json").is_file():
        return _packaged_files()
    files: dict[str, Path] = {}
    packaged_assets = source / "src" / "agent_goodput" / "assets"
    for relative_root in _BUNDLE_PATHS:
        root = source / relative_root
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError("plugin source contains a symlink")
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and not path.is_relative_to(packaged_assets)
            ):
                files[str(path.relative_to(source))] = path
    return files


def bundle_files(source_root: str | Path | None = None) -> dict[str, Path]:
    source = (
        Path(source_root).expanduser().resolve()
        if source_root is not None
        else Path(__file__).resolve().parents[2]
    )
    return _source_files(source)


def _marketplace_entry() -> dict[str, Any]:
    return {
        "name": "agent-goodput",
        "source": {
            "source": "local",
            "path": "./agent-goodput",
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Developer Tools",
    }


def _load_marketplace(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "name": "personal",
            "interface": {"displayName": "Personal"},
            "plugins": [],
        }
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("marketplace must be an object")
    if not isinstance(value.get("plugins"), list):
        raise ValueError("marketplace plugins must be an array")
    return dict(value)


def plan_install(
    source_root: str | Path,
    agents_home: str | Path,
) -> InstallPlan:
    source = Path(source_root).expanduser().resolve()
    home = Path(agents_home).expanduser().resolve()
    plugin_root = home / "plugins"
    target = plugin_root / "agent-goodput"
    marketplace_path = plugin_root / "marketplace.json"
    ledger_path = target / ".agent-goodput-install.json"
    source_files = bundle_files(source)
    if _contains_symlink(target, home) or _contains_symlink(marketplace_path, home):
        return InstallPlan(
            source=str(source),
            target=str(target),
            marketplace=str(marketplace_path),
            actions=(),
            conflicts=("preserve symlinked plugin or marketplace path",),
            apply_allowed=False,
        )
    prior: dict[str, Any] = {}
    if ledger_path.exists():
        with ledger_path.open(encoding="utf-8") as stream:
            prior = json.load(stream)
    prior_hashes = dict(prior.get("files", {}))
    actions: list[str] = []
    conflicts: list[str] = []
    for relative, source_path in source_files.items():
        destination = target / relative
        if _contains_symlink(destination, home):
            conflicts.append(f"preserve symlinked path: {relative}")
            continue
        if not destination.exists():
            actions.append(f"create {relative}")
            continue
        current_hash = _hash_file(destination)
        expected_prior = prior_hashes.get(relative)
        if expected_prior is None or current_hash != expected_prior:
            conflicts.append(f"preserve modified or unmanaged file: {relative}")
        elif current_hash != _install_hash(relative, source_path):
            actions.append(f"update {relative}")
    marketplace = _load_marketplace(marketplace_path)
    matching = [item for item in marketplace["plugins"] if item.get("name") == "agent-goodput"]
    if matching:
        if matching[0] != _marketplace_entry():
            conflicts.append("preserve conflicting agent-goodput marketplace entry")
    else:
        actions.append("add personal marketplace entry")
    return InstallPlan(
        source=str(source),
        target=str(target),
        marketplace=str(marketplace_path),
        actions=tuple(actions),
        conflicts=tuple(conflicts),
        apply_allowed=not conflicts,
    )


def install(
    source_root: str | Path,
    agents_home: str | Path,
    *,
    apply: bool = False,
) -> InstallPlan:
    plan = plan_install(source_root, agents_home)
    if not apply:
        return plan
    if not plan.apply_allowed:
        raise RuntimeError("installation has conflicts; no files were changed")
    source = Path(plan.source)
    target = Path(plan.target)
    marketplace_path = Path(plan.marketplace)
    source_files = bundle_files(source)
    target.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for relative, source_path in source_files.items():
        destination = target / relative
        if _contains_symlink(destination, Path(agents_home).expanduser().resolve()):
            raise RuntimeError("installation path became symlinked; no further files were changed")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_install_bytes(relative, source_path))
        shutil.copymode(source_path, destination)
        hashes[relative] = _hash_file(destination)
    ledger = {
        "schema_version": 1,
        "installed_at": utc_now(),
        "source": str(source),
        "files": hashes,
    }
    write_json(target / ".agent-goodput-install.json", ledger)
    marketplace = _load_marketplace(marketplace_path)
    if not any(item.get("name") == "agent-goodput" for item in marketplace["plugins"]):
        marketplace["plugins"].append(_marketplace_entry())
    write_json(marketplace_path, marketplace, mode=0o644)
    return plan


def uninstall(
    agents_home: str | Path,
    *,
    apply: bool = False,
) -> InstallPlan:
    home = Path(agents_home).expanduser().resolve()
    target = home / "plugins" / "agent-goodput"
    marketplace_path = home / "plugins" / "marketplace.json"
    ledger_path = target / ".agent-goodput-install.json"
    conflicts: list[str] = []
    actions: list[str] = []
    hashes: dict[str, str] = {}
    if _contains_symlink(target, home) or _contains_symlink(marketplace_path, home):
        return InstallPlan(
            source="",
            target=str(target),
            marketplace=str(marketplace_path),
            actions=(),
            conflicts=("preserve symlinked plugin or marketplace path",),
            apply_allowed=False,
        )
    if ledger_path.exists():
        with ledger_path.open(encoding="utf-8") as stream:
            hashes = dict(json.load(stream).get("files", {}))
    else:
        conflicts.append("install ledger is missing; ownership cannot be proven")
    for relative, expected_hash in hashes.items():
        path = target / relative
        if _contains_symlink(path, home):
            conflicts.append(f"preserve symlinked path: {relative}")
            continue
        if not path.exists():
            continue
        if _hash_file(path) != expected_hash:
            conflicts.append(f"preserve modified file: {relative}")
        else:
            actions.append(f"remove {relative}")
    actions.append("remove personal marketplace entry")
    plan = InstallPlan(
        source="",
        target=str(target),
        marketplace=str(marketplace_path),
        actions=tuple(actions),
        conflicts=tuple(conflicts),
        apply_allowed=not conflicts,
    )
    if not apply:
        return plan
    if not plan.apply_allowed:
        raise RuntimeError("uninstall has conflicts; no files were changed")
    for relative in hashes:
        path = target / relative
        if path.exists() and _hash_file(path) == hashes[relative]:
            path.unlink()
    ledger_path.unlink(missing_ok=True)
    for path in sorted(target.rglob("*"), reverse=True):
        if path.is_dir():
            with contextlib.suppress(OSError):
                path.rmdir()
    with contextlib.suppress(OSError):
        target.rmdir()
    marketplace = _load_marketplace(marketplace_path)
    marketplace["plugins"] = [
        item for item in marketplace["plugins"] if item.get("name") != "agent-goodput"
    ]
    write_json(marketplace_path, marketplace, mode=0o644)
    return plan
