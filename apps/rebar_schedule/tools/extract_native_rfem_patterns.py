from __future__ import annotations

import json
import sys
from pathlib import Path

from rebar_schedule.services.native_dxf_patterns import extract_native_section_patterns


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("Uso: python tools/extract_native_rfem_patterns.py <archivo.dxf> [analisis.json] [salida.json]")
        return 1

    source_path = args[0]
    analysis_path = args[1] if len(args) > 1 and args[1] else None
    target_path = args[2] if len(args) > 2 else None

    payload = extract_native_section_patterns(source_path, analysis_path=analysis_path)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    if target_path:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
