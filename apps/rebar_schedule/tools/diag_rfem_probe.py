from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rebar_schedule.adapters.rfem_client import RfemRebarAdapter


def main() -> None:
    adapter = RfemRebarAdapter(
        api_key_name=os.getenv("RFEM_API_KEY_NAME", "default"),
        api_key_value=os.getenv("RFEM_API_KEY_VALUE") or None,
        port=int(os.getenv("RFEM_PORT", "9000")),
    )
    result = adapter.probe_active_model(model_path=os.getenv("RFEM_MODEL_PATH") or None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
