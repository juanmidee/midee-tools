from __future__ import annotations

import json
import sys
from pathlib import Path

from rebar_schedule.services.native_dxf_analysis import analyze_native_rfem_dxf


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("Uso: python tools/analyze_native_rfem_dxf.py <archivo.dxf> [salida.json]")
        return 1

    source_path = args[0]
    payload = analyze_native_rfem_dxf(source_path)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)

    if len(args) > 1:
        target = Path(args[1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
