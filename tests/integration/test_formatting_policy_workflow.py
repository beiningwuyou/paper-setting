from pathlib import Path

from fastapi.testclient import TestClient
from paper_setting_api.main import create_app
from paper_setting_runtime.config import Settings


def test_policy_snapshot_and_mode_validation(sample_docx: Path, tmp_path: Path):
    app = create_app(
        Settings(
            env="test",
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            data_dir=tmp_path / "data",
            web_dist_dir=tmp_path / "missing",
            allowed_hosts=["testserver"],
            allowed_origins=["http://testserver"],
        )
    )
    with TestClient(app, base_url="http://testserver") as client:
        payload = sample_docx.read_bytes()
        files = {"document": ("paper.docx", payload)}
        for mode in ("standardize", "preserve"):
            response = client.post(
                "/api/v1/jobs",
                files=files,
                data={
                    "rule_pack_id": "zh-thesis-default",
                    "formatting_mode": mode,
                },
            )
            assert response.status_code == 202
            job = response.json()
            assert job["formatting_mode"] == mode
            # A later configuration change must not affect a queued job.
            app.state.job_service.settings.default_baseline_path = tmp_path / "not-present.json"
            assert app.state.job_service.process_next("test")
            plan = client.get(f"/api/v1/jobs/{job['id']}/plan").json()
            assert plan["formatting_policy"]["mode"] == mode
            assert (plan["formatting_policy"]["baseline"] is not None) == (mode == "standardize")
            app.state.job_service.settings.default_baseline_path = None
            approval = client.post(
                f"/api/v1/jobs/{job['id']}/approve",
                json={
                    "plan_version": plan["plan_version"],
                    "approved_operation_ids": [op["operation_id"] for op in plan["operations"]],
                    "confirmed_manual_operation_ids": [
                        op["operation_id"]
                        for op in plan["operations"]
                        if op["status"] == "manual_review"
                    ],
                },
            )
            assert approval.status_code == 200
            assert app.state.job_service.process_next("test")
            report = client.get(f"/api/v1/jobs/{job['id']}/report").json()
            assert report["integrity_ok"]
            assert report["formatting_mode"] == mode
            assert report["format_source_counts"]["rule_pack"] > 0
            if mode == "standardize":
                assert report["format_source_counts"]["default_template"] > 0
            else:
                assert report["format_source_counts"].get("default_template", 0) == 0
        invalid = client.post(
            "/api/v1/jobs",
            files=files,
            data={
                "rule_pack_id": "zh-thesis-default",
                "formatting_mode": "invalid",
            },
        )
        assert invalid.status_code == 422
