import json
from pathlib import Path

from paper_setting_api.main import create_app

destination = Path("packages/contracts/openapi.json")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(
    json.dumps(create_app().openapi(), ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(destination)

