import json
from pathlib import Path

from fastapi.testclient import TestClient
from paper_setting_api.main import create_app
from paper_setting_core.rulepacks import default_rule_pack
from paper_setting_runtime.config import Settings


def test_import_rule_pack(tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        database_url=f"sqlite:///{tmp_path / 'rules.db'}",
        data_dir=tmp_path / "data",
        allowed_hosts=["testserver"],
        web_dist_dir=tmp_path / "missing-web",
    )
    app = create_app(settings)
    rule_pack = default_rule_pack().model_copy(
        update={"id": "school-demo", "name": "示例学校规则", "version": "1.0.1"}
    )
    with TestClient(app, base_url="http://testserver") as client:
        response = client.post(
            "/api/v1/rule-packs/import",
            files={
                "document": (
                    "school-demo.json",
                    json.dumps(rule_pack.model_dump(mode="json"), ensure_ascii=False).encode(),
                    "application/json",
                )
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["id"] == "school-demo"
        assert response.json()["capability_report"]["executable"] is True
        assert client.get("/api/v1/rule-packs/school-demo").status_code == 200
        capabilities = client.get("/api/v1/rule-packs/capabilities")
        assert capabilities.status_code == 200
        assert any(item["id"] == "template.inspect" for item in capabilities.json())


def test_import_rejects_rule_pack_with_unresolved_requirement(tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        database_url=f"sqlite:///{tmp_path / 'blocked-rules.db'}",
        data_dir=tmp_path / "data",
        allowed_hosts=["testserver"],
        web_dist_dir=tmp_path / "missing-web",
    )
    app = create_app(settings)
    payload = default_rule_pack().model_dump(mode="json")
    payload["schema_version"] = "2.0"
    payload["requirements"] = {
        "sources": [{"kind": "template", "label": "某学校模板"}],
        "unresolved": ["学校要求中的特殊图表编号规则待确认"],
        "conflicts": [],
        "required_capabilities": [],
    }
    with TestClient(app, base_url="http://testserver") as client:
        response = client.post(
            "/api/v1/rule-packs/import",
            files={
                "document": (
                    "blocked.json",
                    json.dumps(payload, ensure_ascii=False).encode(),
                    "application/json",
                )
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == "RULE_PACK_NOT_EXECUTABLE"
        assert response.json()["field_errors"][0]["field"] == "requirements"
