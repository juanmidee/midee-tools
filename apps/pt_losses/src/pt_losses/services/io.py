from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pt_losses.domain.models import LossesInput

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None


SUPPORTED_EXTENSIONS = {".json", ".yaml", ".yml"}


def load_input_file(path: str | Path) -> LossesInput:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"No se encontro el archivo de entrada: {source}")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Tipo de archivo no soportado: {source.suffix}")

    with source.open("r", encoding="utf-8") as handle:
        data = _parse_mapping(handle.read(), source.suffix.lower())

    if not isinstance(data, dict):
        raise ValueError("El archivo de entrada debe contener un objeto o mapa de claves y valores.")

    return LossesInput.from_mapping(data)


def write_result_file(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def _parse_mapping(raw_text: str, suffix: str) -> dict[str, Any]:
    if suffix == ".json":
        return json.loads(raw_text)
    if yaml is not None:
        parsed = yaml.safe_load(raw_text)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("El archivo YAML debe contener un objeto o mapa de claves y valores.")
    return _parse_simple_yaml_mapping(raw_text)


def _parse_simple_yaml_mapping(raw_text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError("El analizador YAML simple solo admite pares clave: valor.")
        key, value = line.split(":", 1)
        parsed[key.strip()] = _coerce_scalar(value.strip())
    return parsed


def _coerce_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if any(char in value for char in [".", "e", "E"]):
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")
