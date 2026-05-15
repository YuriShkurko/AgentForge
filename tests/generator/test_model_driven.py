import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.generator import generate
from agentforge.pack import DomainPack, load_pack

PACKS_DIR = Path(__file__).parent.parent.parent / "domain-packs"


def _base_pack():
    return {
        "name": "model-test",
        "display_name": "Model Test",
        "version": "0.1.0",
        "domain": {"domain_name": "Model Test", "app_type": "model_driven_app"},
        "app_archetype": "model_driven_app",
        "required_shell_modules": ["model_driven", "operations_ui", "persistence", "test"],
        "optional_shell_modules": [],
        "model": {
            "entities": [
                {
                    "name": "ticket",
                    "label_singular": "Ticket",
                    "label_plural": "Tickets",
                    "fields": [
                        {"name": "title", "type": "string", "required": True},
                        {"name": "status", "type": "enum", "required": True, "enum_values": ["open", "closed"]},
                    ],
                }
            ],
            "pages": [{"name": "tickets", "type": "entity_list", "entity": "ticket"}],
            "actions": [{"name": "close_ticket", "type": "update_status", "entity": "ticket", "field": "status", "value": "closed"}],
            "seed_data": {"ticket": [{"title": "Example", "status": "open"}]},
        },
    }


def test_valid_model_driven_domain_pack_loads():
    pack = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    assert pack.app_archetype == "model_driven_app"
    assert pack.model is not None
    assert [entity.name for entity in pack.model.entities] == ["client", "onboarding_task"]


def test_existing_domain_packs_still_load():
    assert load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml").app_archetype == "ingestion_scoring_pipeline"
    assert load_pack(PACKS_DIR / "project-workspace-demo" / "domain-pack.yaml").app_archetype == "project_workspace_app"


def test_duplicate_entity_names_fail_clearly():
    data = _base_pack()
    data["model"]["entities"].append(dict(data["model"]["entities"][0]))
    with pytest.raises(Exception, match="entity names must be unique"):
        DomainPack.model_validate(data)


def test_duplicate_field_names_fail_clearly():
    data = _base_pack()
    data["model"]["entities"][0]["fields"].append({"name": "title", "type": "text"})
    with pytest.raises(Exception, match="duplicate field names"):
        DomainPack.model_validate(data)


def test_invalid_entity_and_field_names_fail():
    data = _base_pack()
    data["model"]["entities"][0]["name"] = "Bad Entity"
    with pytest.raises(Exception):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["entities"][0]["fields"][0]["name"] = "bad-field"
    with pytest.raises(Exception):
        DomainPack.model_validate(data)


def test_unsupported_model_field_type_fails_clearly():
    data = _base_pack()
    data["model"]["entities"][0]["fields"][0]["type"] = "currency"
    with pytest.raises(Exception, match="unsupported model field type"):
        DomainPack.model_validate(data)


def test_model_driven_app_requires_model_block_but_existing_packs_do_not():
    data = _base_pack()
    data.pop("model")
    with pytest.raises(Exception, match="must include a model block"):
        DomainPack.model_validate(data)
    existing = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    assert existing.model is None


def test_enum_field_requires_values():
    data = _base_pack()
    data["model"]["entities"][0]["fields"][1].pop("enum_values")
    with pytest.raises(Exception, match="must define enum_values"):
        DomainPack.model_validate(data)


def test_relation_target_validation_fails_clearly():
    data = _base_pack()
    data["model"]["entities"][0]["fields"].append({"name": "owner_id", "type": "relation", "target_entity": "missing"})
    with pytest.raises(Exception, match="targets unknown entity"):
        DomainPack.model_validate(data)


def test_malformed_pages_actions_and_seed_data_fail_clearly():
    data = _base_pack()
    data["model"]["pages"][0]["entity"] = "missing"
    with pytest.raises(Exception, match="references unknown entity"):
        DomainPack.model_validate(data)

    data = _base_pack()
    data["model"]["actions"][0]["value"] = "not_allowed"
    with pytest.raises(Exception, match="value must be one of"):
        DomainPack.model_validate(data)

    data = _base_pack()
    data["model"]["actions"] = [{"name": "finish", "type": "mark_complete", "entity": "ticket"}]
    with pytest.raises(Exception, match="field must be a boolean field"):
        DomainPack.model_validate(data)

    data = _base_pack()
    data["model"]["seed_data"] = {"ticket": [{"unknown": "Example"}]}
    with pytest.raises(Exception, match="includes unknown field"):
        DomainPack.model_validate(data)


def test_missing_required_entity_fields_fails_clearly():
    data = _base_pack()
    data["model"]["entities"][0]["fields"] = []
    with pytest.raises(Exception, match="must define at least one field"):
        DomainPack.model_validate(data)


def test_model_driven_generation_writes_entity_specific_files(tmp_path):
    pack = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    output = tmp_path / pack.name
    result = generate(pack, output)
    assert result["template"] == "model-driven-react"
    assert result["archetype"] == "model_driven_app"
    assert (output / "backend/app/main.py").exists()
    assert (output / "frontend/src/App.tsx").exists()
    assert (output / "Makefile").exists()
    assert (output / "README.md").exists()
    main = (output / "backend/app/main.py").read_text()
    app = (output / "frontend/src/App.tsx").read_text()
    assert "/onboarding-task" in main
    assert "Client Onboarding Workspace" in app
    assert "Onboarding Tasks" in app
    assert "mark_task_done" in main
    makefile = (output / "Makefile").read_text()
    assert "validate:" in makefile
    assert "cd backend && python -m pytest" in makefile
    assert "cd frontend && npm run build" in makefile
    assert "cd frontend && npm run lint" in makefile
    assert "make validate" in (output / "README.md").read_text()


def test_two_model_driven_packs_share_path_but_generate_different_outputs(tmp_path):
    client = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    client_out = tmp_path / client.name
    vendor_out = tmp_path / vendor.name
    generate(client, client_out)
    generate(vendor, vendor_out)
    client_app = (client_out / "frontend/src/App.tsx").read_text()
    vendor_app = (vendor_out / "frontend/src/App.tsx").read_text()
    assert "Clients" in client_app and "Onboarding Tasks" in client_app
    assert "Vendors" in vendor_app and "Risk Findings" in vendor_app
    assert "enterprise" in client_app
    assert "critical" in vendor_app
    assert client_app != vendor_app


def test_model_driven_generation_is_deterministic(tmp_path):
    pack = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(pack, first)
    generate(pack, second)
    for rel in ["backend/app/main.py", "backend/app/models.py", "frontend/src/App.tsx", "app-model.json"]:
        assert (first / rel).read_text() == (second / rel).read_text()
