from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class ExtractedFile:
    file_id: int
    path: str
    raw_size: int
    decoded_size: int
    compression: str
    raw_sha256: str
    decoded_sha256: str


@dataclass(frozen=True)
class ExtractedOverlay:
    overlay_id: int
    file_id: int
    ram_address: int
    ram_size: int
    bss_size: int
    raw_size: int
    decoded_size: int
    raw_sha256: str
    decoded_sha256: str
    compression: str


@dataclass(frozen=True)
class WorkspaceManifest:
    format_version: int
    profile_id: str
    rom_sha256: str
    rom_size: int
    arm9_sha256: str
    arm7_sha256: str
    files: tuple[ExtractedFile, ...]
    overlays: tuple[ExtractedOverlay, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "profile_id": self.profile_id,
            "rom_sha256": self.rom_sha256,
            "rom_size": self.rom_size,
            "arm9_sha256": self.arm9_sha256,
            "arm7_sha256": self.arm7_sha256,
            "files": [asdict(item) for item in sorted(self.files, key=lambda item: item.file_id)],
            "overlays": [
                asdict(item) for item in sorted(self.overlays, key=lambda item: item.overlay_id)
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
