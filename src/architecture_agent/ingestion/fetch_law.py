from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

LAW_SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"
DEFAULT_LAW_IDS = ("1823", "2118")


def fetch_law_json(law_id: str, oc: str | None = None) -> dict:
    oc_value = oc or os.getenv("OC", "")
    if not oc_value:
        raise ValueError("Missing OC. Set OC in environment or pass explicitly.")

    params = {
        "OC": oc_value,
        "target": "eflaw",
        "ID": law_id,
        "type": "JSON",
    }
    response = requests.get(LAW_SERVICE_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_and_save_laws(
    law_ids: tuple[str, ...] = DEFAULT_LAW_IDS,
    output_dir: str = "data/processed/raw",
    oc: str | None = None,
) -> list[Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[Path] = []
    for law_id in law_ids:
        payload = fetch_law_json(law_id=law_id, oc=oc)
        law_name = payload["법령"]["기본정보"].get("법령명_한글", law_id)
        file_name = f"{law_id}_{law_name}.json"
        target = out_dir / file_name
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        saved_files.append(target)
    return saved_files


if __name__ == "__main__":
    files = fetch_and_save_laws()
    for f in files:
        print(f"saved: {f}")
