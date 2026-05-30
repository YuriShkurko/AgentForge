import json
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
    assert pack.model.ui.composition == "board_workspace"
    assert pack.model.ui.recipe == "workspace_board"
    assert pack.model.ui.focus.primary_entity == "onboarding_task"
    assert pack.model.ui.style.accent == "emerald"
    assert pack.model.ui.entities["onboarding_task"].display.layout == "board_by_status"


def test_missing_ui_config_uses_defaults():
    pack = DomainPack.model_validate(_base_pack())
    assert pack.model is not None
    assert pack.model.ui.composition == "standard"
    assert pack.model.ui.recipe == "standard"
    assert pack.model.ui.style.accent == "blue"
    assert pack.model.ui.style.density == "comfortable"
    assert pack.model.ui.entities == {}


def test_invalid_ui_values_fail_clearly():
    data = _base_pack()
    data["model"]["ui"] = {"style": {"accent": "neon"}}
    with pytest.raises(Exception, match="unknown ui accent"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"style": {"density": "tiny"}}
    with pytest.raises(Exception, match="unknown ui density"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"entities": {"ticket": {"display": {"layout": "masonry"}}}}
    with pytest.raises(Exception, match="unknown entity display layout"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"composition": "split_screen"}
    with pytest.raises(Exception, match="unknown ui composition"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"recipe": "client_special"}
    with pytest.raises(Exception, match="unknown ui recipe"):
        DomainPack.model_validate(data)


def test_valid_recipe_config_loads():
    data = _base_pack()
    data["model"]["ui"] = {"recipe": "workspace_board"}
    pack = DomainPack.model_validate(data)
    assert pack.model is not None
    assert pack.model.ui.recipe == "workspace_board"


def test_valid_composition_config_loads():
    data = _base_pack()
    data["model"]["ui"] = {"composition": "board_workspace", "focus": {"primary_entity": "ticket", "group_by": "status", "title_field": "title", "badge_field": "status"}}
    pack = DomainPack.model_validate(data)
    assert pack.model is not None
    assert pack.model.ui.composition == "board_workspace"
    assert pack.model.ui.focus.group_by == "status"


def test_invalid_focus_entity_and_field_fail():
    data = _base_pack()
    data["model"]["ui"] = {"composition": "register_table", "focus": {"primary_entity": "missing"}}
    with pytest.raises(Exception, match="focus primary_entity references unknown entity"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"composition": "register_table", "focus": {"primary_entity": "ticket", "secondary_entity": "missing"}}
    with pytest.raises(Exception, match="focus secondary_entity references unknown entity"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"composition": "register_table", "focus": {"primary_entity": "ticket", "group_by": "missing"}}
    with pytest.raises(Exception, match="focus group_by references unknown field"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"composition": "board_workspace", "focus": {"primary_entity": "ticket", "group_by": "title"}}
    with pytest.raises(Exception, match="group_by must be an enum field"):
        DomainPack.model_validate(data)


def test_invalid_entity_display_field_fails():
    data = _base_pack()
    data["model"]["ui"] = {"entities": {"ticket": {"display": {"layout": "cards", "title_field": "missing"}}}}
    with pytest.raises(Exception, match="references unknown field 'missing'"):
        DomainPack.model_validate(data)


def test_invalid_dashboard_entity_and_field_fail():
    data = _base_pack()
    data["model"]["ui"] = {"dashboard": {"cards": [{"type": "count", "entity": "missing"}]}}
    with pytest.raises(Exception, match="references unknown entity 'missing'"):
        DomainPack.model_validate(data)
    data = _base_pack()
    data["model"]["ui"] = {"dashboard": {"cards": [{"type": "attention_list", "entity": "ticket", "field": "missing", "value": "open"}]}}
    with pytest.raises(Exception, match="references unknown field 'missing'"):
        DomainPack.model_validate(data)


def test_enum_breakdown_on_non_enum_field_fails():
    data = _base_pack()
    data["model"]["ui"] = {"dashboard": {"cards": [{"type": "enum_breakdown", "entity": "ticket", "field": "title"}]}}
    with pytest.raises(Exception, match="field must be enum"):
        DomainPack.model_validate(data)


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
    assert "accent-" in app
    assert '"recipe": "workspace_board"' in app
    assert "data-recipe" in app
    assert "data-ui-layout=\"composition-board-workspace\"" in app
    assert "data-ui-layout=\"board_by_status\"" in app
    assert "data-ui-state=\"empty\"" in app
    assert "emptyForLane" in app
    assert "emptyForList" in app
    assert "emptyForRelated" in app
    assert "No items yet." not in app
    assert "No related records yet." not in app
    assert "humanize" in app and "replace(/_/g, ' ')" in app
    makefile = (output / "Makefile").read_text()
    assert "validate:" in makefile
    assert "cd backend && python -m pytest" in makefile
    assert "cd frontend && npm run build" in makefile
    assert "cd frontend && npm run lint" in makefile
    assert "make validate" in (output / "README.md").read_text()


def test_model_driven_schema_date_field_named_date_does_not_shadow_type(tmp_path):
    data = _base_pack()
    data["name"] = "date-shadow-test"
    data["display_name"] = "Date Shadow Test"
    data["model"]["entities"] = [{
        "name": "session",
        "label_singular": "Session",
        "label_plural": "Sessions",
        "fields": [
            {"name": "date", "type": "date", "required": True},
            {"name": "status", "type": "enum", "required": True, "enum_values": ["scheduled", "completed"]},
        ],
    }]
    data["model"]["pages"] = [{"name": "sessions", "type": "entity_list", "entity": "session"}]
    data["model"]["actions"] = [{"name": "complete_session", "type": "update_status", "entity": "session", "field": "status", "value": "completed"}]
    data["model"]["seed_data"] = {"session": [{"date": "2026-06-01", "status": "scheduled"}]}
    pack = DomainPack.model_validate(data)
    output = tmp_path / pack.name

    generate(pack, output)
    schemas = (output / "backend/app/schemas.py").read_text()

    assert "from __future__ import annotations" in schemas
    assert "from datetime import date as date_type" in schemas
    exec(compile(schemas, str(output / "backend/app/schemas.py"), "exec"), {})


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
    assert "Client Onboarding Command Center" in client_app
    assert "Vendor Risk Register" in vendor_app
    assert "composition-board-workspace" in client_app
    assert "workspace-main" in client_app
    assert '"recipe": "workspace_board"' in client_app
    assert "composition-register-table" in vendor_app
    assert "register-main" in vendor_app
    assert "register-card" in vendor_app
    assert '"recipe": "executive_register"' in vendor_app
    assert "emptyForList" in vendor_app
    assert "No records yet" not in vendor_app
    assert "emerald" in client_app and "amber" in vendor_app
    assert client_app != vendor_app


def test_relation_helpers_present_in_generated_frontend(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "relationLabel" in app
    assert "inferTitleField" in app
    assert "cellValue" in app


def test_relation_fields_render_select_in_create_form(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert 'data-ui-control="relation-select"' in app
    assert "Load seed data or create a ${targetLabel} first" in app


def test_table_cells_route_through_cell_value_for_relations(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "cellValue(field, row[field.name], rowsByEntity)" in app
    assert "displayValue(" not in app


def test_relation_label_falls_back_to_entity_id_pattern(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "target?.labelSingular || 'Entity'" in app
    assert "${singular} #${id}" in app


def test_title_humanizer_applied_to_composition_headers(tmp_path):
    client = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    client_out = tmp_path / client.name
    vendor_out = tmp_path / vendor.name
    generate(client, client_out)
    generate(vendor, vendor_out)
    client_app = (client_out / "frontend/src/App.tsx").read_text()
    vendor_app = (vendor_out / "frontend/src/App.tsx").read_text()
    assert "const titleize" in client_app
    assert "function HeroBanner" in client_app
    assert "heroHeadline" in client_app
    assert "function HeroBanner" in vendor_app
    assert "labelPlural} board" not in client_app
    assert "labelPlural} register" not in vendor_app


def test_table_and_board_have_overflow_wrappers(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    client = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    for pack in (vendor, client):
        out = tmp_path / pack.name
        generate(pack, out)
        app = (out / "frontend/src/App.tsx").read_text()
        assert 'className="table-scroll"' in app
        assert 'className="board-scroll"' in app


def test_responsive_breakpoints_in_styles(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    styles = (out / "frontend/src/styles.css").read_text()
    assert "max-width:1320px" in styles
    assert "margin:0 auto" in styles
    assert "@media(max-width:1280px)" in styles
    assert "@media(max-width:980px)" in styles
    assert "clamp(" in styles
    assert "min-width:0" in styles
    assert ".table-scroll{" in styles or ".register-card .table-scroll" in styles
    assert ".board-scroll{" in styles
    assert "table-layout:auto" in styles


def test_board_workspace_places_create_form_under_board(tmp_path):
    client = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    out = tmp_path / client.name
    generate(client, out)
    app = (out / "frontend/src/App.tsx").read_text()
    board_idx = app.find("function BoardWorkspace")
    next_fn = app.find("function RegisterTable", board_idx)
    board_body = app[board_idx:next_fn]
    workspace_board_idx = board_body.find('className="workspace-board"')
    secondary_idx = board_body.find('className="secondary-panel"')
    compact_create_idx = board_body.find('className="compact-create"')
    assert workspace_board_idx != -1
    assert compact_create_idx != -1
    assert secondary_idx == -1 or compact_create_idx < secondary_idx, "create form should sit inside the board column, not after the secondary aside"


def test_generated_backend_test_covers_seed_idempotency(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    backend_test = (out / "backend/tests/test_model_driven_app.py").read_text()
    assert "def test_seed_is_idempotent():" in backend_test
    assert backend_test.count("client.post('/seed')") >= 3
    assert "first == second" in backend_test


@pytest.mark.parametrize(
    "pack_name",
    ["client-onboarding-workspace", "vendor-risk-tracker", "github-issues-workspace"],
)
def test_generated_backend_database_honors_database_url_env(tmp_path, pack_name):
    pack = load_pack(PACKS_DIR / pack_name / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    db_module = (out / "backend/app/database.py").read_text()
    assert "import os" in db_module
    assert 'os.environ.get("DATABASE_URL", "sqlite:///./app.db")' in db_module


@pytest.mark.parametrize(
    "pack_name",
    ["client-onboarding-workspace", "vendor-risk-tracker", "github-issues-workspace"],
)
def test_generated_backend_tests_use_isolated_database(tmp_path, pack_name):
    pack = load_pack(PACKS_DIR / pack_name / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    conftest_path = out / "backend/tests/conftest.py"
    assert conftest_path.exists(), "generated backend must emit tests/conftest.py for isolation"
    conftest = conftest_path.read_text()
    assert 'os.environ["DATABASE_URL"]' in conftest
    assert "test_app.db" in conftest
    assert "_TEST_DB_PATH.unlink()" in conftest


def test_seed_inserts_parent_before_child_and_fills_required_fk(tmp_path):
    pack_data = _base_pack()
    pack_data["name"] = "model-test-fk"
    pack_data["model"]["entities"] = [
        {
            "name": "farm",
            "label_singular": "Farm",
            "label_plural": "Farms",
            "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "location", "type": "string", "required": True},
            ],
        },
        {
            "name": "livestock",
            "label_singular": "Livestock",
            "label_plural": "Livestock",
            "fields": [
                {"name": "type", "type": "string", "required": True},
                {"name": "age", "type": "integer", "required": True},
                {"name": "health_status", "type": "enum", "required": True, "enum_values": ["healthy", "sick"]},
                {"name": "farm_id", "type": "relation", "required": True, "target_entity": "farm"},
            ],
        },
    ]
    pack_data["model"]["pages"] = [
        {"name": "farms", "type": "entity_list", "entity": "farm"},
        {"name": "livestock", "type": "entity_list", "entity": "livestock"},
    ]
    pack_data["model"]["actions"] = []
    # Intentionally omit a farm seed row AND omit farm_id on the livestock seed
    # row — this matches the failure mode where the generator emitted an
    # INSERT with farm_id=NULL against a NOT NULL column.
    pack_data["model"]["seed_data"] = {
        "livestock": [{"type": "Example Type", "age": 0, "health_status": "healthy"}],
    }
    pack = DomainPack.model_validate(pack_data)
    out = tmp_path / pack.name
    generate(pack, out)
    main_py = (out / "backend/app/main.py").read_text(encoding="utf-8")
    # Parent (Farm) must be seeded before the child (Livestock) block.
    farm_index = main_py.index("db.add(models.Farm(")
    livestock_index = main_py.index("db.add(models.Livestock(")
    assert farm_index < livestock_index
    # The Livestock insert must include farm_id resolved from a parent lookup.
    livestock_block = main_py[livestock_index - 400:livestock_index + 400]
    assert "db.query(models.Farm).order_by(models.Farm.id).first()" in livestock_block
    assert "farm_id=_farm_id_parent_" in livestock_block
    # Parent insert receives a placeholder row even though seed_data omitted it.
    assert "name='Example Farm Name'" in main_py or "name=\"Example Farm Name\"" in main_py or "models.Farm(name=" in main_py
    # Flush before the next entity so freshly-assigned ids are usable as FKs.
    assert "db.flush()" in main_py


def test_seed_block_guards_when_parent_row_is_unavailable(tmp_path):
    pack_data = _base_pack()
    pack_data["name"] = "model-test-fk-guard"
    pack_data["model"]["entities"] = [
        {
            "name": "owner",
            "label_singular": "Owner",
            "label_plural": "Owners",
            "fields": [{"name": "name", "type": "string", "required": True}],
        },
        {
            "name": "pet",
            "label_singular": "Pet",
            "label_plural": "Pets",
            "fields": [
                {"name": "nickname", "type": "string", "required": True},
                {"name": "owner_id", "type": "relation", "required": True, "target_entity": "owner"},
            ],
        },
    ]
    pack_data["model"]["pages"] = [{"name": "pets", "type": "entity_list", "entity": "pet"}]
    pack_data["model"]["actions"] = []
    pack_data["model"]["seed_data"] = {"pet": [{"nickname": "Spot"}]}
    pack = DomainPack.model_validate(pack_data)
    out = tmp_path / pack.name
    generate(pack, out)
    main_py = (out / "backend/app/main.py").read_text(encoding="utf-8")
    # The pet insert is guarded against missing parent rows.
    pet_block = main_py.split("db.query(models.Pet)")[1].split("created['pet']")[0]
    assert "if _owner_id_parent_0 is not None" in pet_block
    assert "db.add(models.Pet(nickname='Spot', owner_id=_owner_id_parent_0.id))" in pet_block


def test_app_exposes_active_entity_state(tmp_path):
    client = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    out = tmp_path / client.name
    generate(client, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "useState(primary.name)" in app
    assert "data-active-entity={active}" in app
    assert "data-primary-active={isPrimaryActive" in app
    assert "const isPrimaryActive = entity.name === primary.name" in app


def test_dispatch_renders_focused_surface_when_not_primary(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "function FocusedSurface(" in app
    assert "isPrimaryActive && useBoardWorkspace()" in app
    assert "isPrimaryActive && model.ui.composition === 'register_table'" in app
    assert "<FocusedSurface" in app
    assert 'data-ui-layout="composition-focused"' in app


def test_side_panel_dedupes_secondary_rows(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "const uniqueById =" in app
    assert "uniqueById(asRows(ctx.rowsByEntity[ctx.secondary.name]))" in app
    assert 'data-ui-surface="secondary-related"' in app


def test_register_table_places_create_form_under_register(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    register_idx = app.find("function RegisterTable")
    next_fn = app.find("function FocusedSurface", register_idx)
    body = app[register_idx:next_fn]
    register_focus_idx = body.find('className="register-focus"')
    compact_create_idx = body.find('className="compact-create"')
    side_idx = body.find('className="register-side"')
    assert register_focus_idx != -1 and compact_create_idx != -1
    assert register_focus_idx < compact_create_idx < side_idx, "compact-create must sit under register-focus, not in side rail"


def test_focused_surface_css_has_responsive_breakpoint(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    styles = (out / "frontend/src/styles.css").read_text()
    assert ".focused-surface" in styles
    assert ".focused-main" in styles
    assert "@media(max-width:1180px)" in styles
    assert ".secondary-panel,.register-side{max-height:" in styles


def test_seed_endpoint_uses_existing_count_guard(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    main = (out / "backend/app/main.py").read_text()
    assert ".count() == 0:" in main


def test_executive_register_side_card_contrast_css(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    styles = (out / "frontend/src/styles.css").read_text()
    assert ".recipe-executive_register .register-side .record-card" in styles
    assert ".recipe-executive_register .register-side .record-card h3" in styles
    assert ".recipe-executive_register .register-side .record-card small" in styles
    assert ".recipe-executive_register .register-side .empty-state" in styles


def test_model_driven_generation_is_deterministic(tmp_path):
    pack = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(pack, first)
    generate(pack, second)
    for rel in ["backend/app/main.py", "backend/app/models.py", "backend/app/imports.py", "frontend/src/App.tsx", "app-model.json"]:
        assert (first / rel).read_text() == (second / rel).read_text()


# --------------------------------------------------------------------------- #
# Importer v0 — schema validation
# --------------------------------------------------------------------------- #


def _pack_with_imports(extra_import=None, replace_imports=None):
    data = {
        "name": "import-test",
        "display_name": "Import Test",
        "version": "0.1.0",
        "domain": {"domain_name": "Import Test", "app_type": "model_driven_app"},
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
            "actions": [],
            "seed_data": {"ticket": [{"title": "Example", "status": "open"}]},
            "imports": replace_imports if replace_imports is not None else [
                {
                    "id": "tickets_import",
                    "label": "Import tickets",
                    "entity": "ticket",
                    "formats": ["csv", "json"],
                    "upsert_key": "title",
                    "field_map": {"Title": "title", "Status": "status"},
                }
            ],
        },
    }
    if extra_import is not None:
        data["model"]["imports"].append(extra_import)
    return data


def test_import_config_loads_for_example_packs():
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    assert vendor.model is not None
    assert [imp.id for imp in vendor.model.imports] == ["vendors_import", "risk_findings_import"]
    vendors_import = vendor.model.imports[0]
    assert vendors_import.entity == "vendor"
    assert vendors_import.formats == ["csv", "json"]
    assert vendors_import.upsert_key == "name"
    assert vendors_import.field_map["Vendor name"] == "name"

    client = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    assert [imp.id for imp in client.model.imports] == ["clients_import", "onboarding_tasks_import"]


def test_import_with_unknown_entity_fails():
    data = _pack_with_imports(replace_imports=[{"id": "bad", "entity": "missing", "formats": ["csv"]}])
    with pytest.raises(Exception, match="references unknown entity"):
        DomainPack.model_validate(data)


def test_import_with_invalid_format_fails():
    data = _pack_with_imports(replace_imports=[{"id": "bad", "entity": "ticket", "formats": ["xml"]}])
    with pytest.raises(Exception, match="unsupported import formats"):
        DomainPack.model_validate(data)


def test_import_with_empty_format_list_fails():
    data = _pack_with_imports(replace_imports=[{"id": "bad", "entity": "ticket", "formats": []}])
    with pytest.raises(Exception, match="at least one of csv, json"):
        DomainPack.model_validate(data)


def test_import_with_unknown_upsert_key_fails():
    data = _pack_with_imports(replace_imports=[{"id": "bad", "entity": "ticket", "formats": ["csv"], "upsert_key": "missing"}])
    with pytest.raises(Exception, match="upsert_key references unknown field"):
        DomainPack.model_validate(data)


def test_import_with_unknown_field_map_target_fails():
    data = _pack_with_imports(replace_imports=[{"id": "bad", "entity": "ticket", "formats": ["csv"], "field_map": {"Title": "missing"}}])
    with pytest.raises(Exception, match="field_map target field 'missing' is not defined"):
        DomainPack.model_validate(data)


def test_duplicate_import_ids_fail():
    data = _pack_with_imports(
        extra_import={"id": "tickets_import", "entity": "ticket", "formats": ["csv"]}
    )
    with pytest.raises(Exception, match="import id 'tickets_import' is duplicated"):
        DomainPack.model_validate(data)


def test_pack_with_no_imports_still_validates():
    data = _pack_with_imports(replace_imports=[])
    pack = DomainPack.model_validate(data)
    assert pack.model is not None
    assert pack.model.imports == []


# --------------------------------------------------------------------------- #
# Importer v0 — generated source surface
# --------------------------------------------------------------------------- #


def test_generated_imports_module_emits_pipeline(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    imports_module = (out / "backend/app/imports.py").read_text()
    assert "IMPORTS" in imports_module
    assert "ENTITY_FIELDS" in imports_module
    assert "ENTITY_MODELS" in imports_module
    assert "def parse_csv" in imports_module
    assert "def parse_json" in imports_module
    assert "def preview" in imports_module
    assert "def commit" in imports_module
    assert "vendors_import" in imports_module


def test_generated_main_has_import_endpoints(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    main = (out / "backend/app/main.py").read_text()
    assert "@app.get('/imports')" in main
    assert "@app.get('/imports/runs')" in main
    assert "@app.post('/imports/{import_id}/preview')" in main
    assert "@app.post('/imports/{import_id}/commit')" in main
    assert "from app import imports as importer" in main


def test_generated_models_include_import_run(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    models_py = (out / "backend/app/models.py").read_text()
    assert "class ImportRun(Base):" in models_py
    assert "import_runs" in models_py
    assert "error_summary" in models_py


def test_generated_app_metadata_includes_imports(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    meta = json.loads((out / "app-model.json").read_text())
    assert len(meta["imports"]) == 2
    first = meta["imports"][0]
    assert first["id"] == "vendors_import"
    assert "csv" in first["formats"] and "json" in first["formats"]
    assert first["fieldMap"]["Vendor name"] == "name"


def test_generated_frontend_renders_import_panel(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "function ImportPanel" in app
    assert 'data-ui-surface="import-panel"' in app
    assert 'data-ui-control="imports-nav"' in app
    assert "'__imports__'" in app
    assert 'data-ui-control="import-data"' in app
    assert 'data-ui-action="import-preview"' in app
    assert 'data-ui-action="import-commit"' in app
    assert 'data-ui-surface="import-runs"' in app


def test_generated_frontend_import_panel_includes_relation_helper_text(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert 'data-ui-surface="import-relation-help"' in app
    assert "Relation columns can use either IDs or related record names" in app
    assert "relationFieldsForImport" in app
    assert "relationImportAliases" in app


def test_generated_backend_tests_cover_import_flow(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    backend_test = (out / "backend/tests/test_model_driven_app.py").read_text()
    assert "test_imports_endpoint_lists_configured_imports" in backend_test
    assert "test_import_preview_csv" in backend_test
    assert "test_import_preview_json" in backend_test
    assert "test_import_commit_creates_records" in backend_test


def test_generated_readme_documents_relation_by_label_imports(tmp_path):
    client = load_pack(PACKS_DIR / "client-onboarding-workspace" / "domain-pack.yaml")
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    for pack, alias in [(client, "client"), (vendor, "vendor")]:
        out = tmp_path / pack.name
        generate(pack, out)
        readme = (out / "README.md").read_text()
        assert "Relation import examples" in readme
        assert f"`{alias}` containing" in readme
        assert "Related records must already exist" in readme


def test_pack_without_imports_still_generates(tmp_path):
    # Existing model-driven pack without imports — synthesize via _pack_with_imports
    data = _pack_with_imports(replace_imports=[])
    pack = DomainPack.model_validate(data)
    out = tmp_path / pack.name
    generate(pack, out)
    app = (out / "frontend/src/App.tsx").read_text()
    # Panel code is always generated, but the sidebar entry is gated on imports.length
    assert "function ImportPanel" in app
    assert "model.imports.length > 0" in app
    meta = json.loads((out / "app-model.json").read_text())
    assert meta["imports"] == []


# --------------------------------------------------------------------------- #
# Importer v0 — in-process generated backend exercise
# --------------------------------------------------------------------------- #


@pytest.fixture
def generated_vendor_client(tmp_path, monkeypatch):
    return _make_generated_client(tmp_path, monkeypatch, "vendor-risk-tracker")


@pytest.fixture
def generated_client_client(tmp_path, monkeypatch):
    return _make_generated_client(tmp_path, monkeypatch, "client-onboarding-workspace")


def _make_generated_client(tmp_path, monkeypatch, pack_name):
    pack = load_pack(PACKS_DIR / pack_name / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    backend_dir = out / "backend"
    monkeypatch.chdir(backend_dir)
    monkeypatch.syspath_prepend(str(backend_dir))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    from app.main import app  # noqa: E402
    from fastapi.testclient import TestClient  # noqa: E402
    return TestClient(app)


def test_imports_endpoint_lists_configured_imports(generated_vendor_client):
    response = generated_vendor_client.get("/imports")
    assert response.status_code == 200
    items = response.json()
    ids = [item["id"] for item in items]
    assert "vendors_import" in ids and "risk_findings_import" in ids
    vendors = next(item for item in items if item["id"] == "vendors_import")
    assert vendors["upsert_key"] == "name"
    assert "csv" in vendors["formats"] and "json" in vendors["formats"]


def test_imports_runs_endpoint_starts_empty(generated_vendor_client):
    response = generated_vendor_client.get("/imports/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_csv_preview_reports_valid_rows(generated_vendor_client):
    csv_data = "Vendor name,Service area,Inherent risk,Next review date\nAcme,Finance,high,2026-07-10\n"
    response = generated_vendor_client.post("/imports/vendors_import/preview", json={"format": "csv", "data": csv_data})
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 1
    assert body["valid_rows"] == 1
    assert body["invalid_rows"] == 0
    assert body["would_create"] == 1
    assert body["would_update"] == 0
    assert set(body["mapped_fields"]) == {"name", "service_area", "inherent_risk", "next_review_date"}


def test_json_array_preview_uses_shared_pipeline(generated_vendor_client):
    json_data = json.dumps([{"Vendor name": "Acme", "Service area": "Finance", "Inherent risk": "high", "Next review date": "2026-07-10"}])
    response = generated_vendor_client.post("/imports/vendors_import/preview", json={"format": "json", "data": json_data})
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 1
    assert body["valid_rows"] == 1


def test_json_records_envelope_preview(generated_vendor_client):
    json_data = json.dumps({"records": [{"Vendor name": "Acme", "Service area": "Finance", "Inherent risk": "high", "Next review date": "2026-07-10"}]})
    response = generated_vendor_client.post("/imports/vendors_import/preview", json={"format": "json", "data": json_data})
    assert response.status_code == 200
    assert response.json()["valid_rows"] == 1


def test_preview_invalid_enum_value_reports_error(generated_vendor_client):
    csv_data = "Vendor name,Service area,Inherent risk\nAcme,Finance,extreme\n"
    response = generated_vendor_client.post("/imports/vendors_import/preview", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["valid_rows"] == 0
    assert body["invalid_rows"] == 1
    assert "inherent_risk" in body["errors"][0]["errors"][0]


def test_preview_invalid_date_value_reports_error(generated_vendor_client):
    csv_data = "Vendor name,Service area,Inherent risk,Next review date\nAcme,Finance,high,not-a-date\n"
    response = generated_vendor_client.post("/imports/vendors_import/preview", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["invalid_rows"] == 1
    assert "next_review_date" in body["errors"][0]["errors"][0]


def test_preview_missing_required_column_reports_error(generated_vendor_client):
    csv_data = "Service area,Inherent risk\nFinance,high\n"
    response = generated_vendor_client.post("/imports/vendors_import/preview", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["invalid_rows"] == 1
    assert any("name is required" in err for err in body["errors"][0]["errors"])


def test_commit_creates_records_and_records_a_run(generated_vendor_client):
    csv_data = "Vendor name,Service area,Inherent risk,Next review date\nAcme,Finance,high,2026-07-10\n"
    response = generated_vendor_client.post("/imports/vendors_import/commit", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["status"] == "ok"
    assert body["created_count"] == 1
    assert body["error_count"] == 0
    listing = generated_vendor_client.get("/vendor").json()
    assert any(row["name"] == "Acme" for row in listing)
    runs = generated_vendor_client.get("/imports/runs").json()
    assert runs and runs[0]["import_id"] == "vendors_import"
    assert runs[0]["status"] == "ok"


def test_commit_rejects_invalid_rows_and_creates_no_records(generated_vendor_client):
    csv_data = "Vendor name,Service area,Inherent risk\nAcme,Finance,extreme\n"
    response = generated_vendor_client.post("/imports/vendors_import/commit", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["status"] == "rejected"
    assert body["created_count"] == 0
    assert body["error_count"] == 1
    listing = generated_vendor_client.get("/vendor").json()
    assert all(row["name"] != "Acme" for row in listing)
    runs = generated_vendor_client.get("/imports/runs").json()
    assert runs[0]["status"] == "rejected"


def test_commit_upsert_is_idempotent(generated_vendor_client):
    csv_data = "Vendor name,Service area,Inherent risk,Next review date\nAcme,Finance,high,2026-07-10\n"
    first = generated_vendor_client.post("/imports/vendors_import/commit", json={"format": "csv", "data": csv_data}).json()
    second = generated_vendor_client.post("/imports/vendors_import/commit", json={"format": "csv", "data": csv_data}).json()
    assert first["created_count"] == 1
    assert second["created_count"] == 0
    assert second["updated_count"] == 1
    listing = generated_vendor_client.get("/vendor").json()
    matches = [row for row in listing if row["name"] == "Acme"]
    assert len(matches) == 1


def test_unknown_import_id_returns_404(generated_vendor_client):
    response = generated_vendor_client.post("/imports/nonexistent/preview", json={"format": "csv", "data": ""})
    assert response.status_code == 404


def test_unsupported_format_for_import_returns_400(generated_vendor_client):
    # Hypothetically restrict — risk_findings_import allows both; force mismatch via unknown format
    response = generated_vendor_client.post("/imports/vendors_import/preview", json={"format": "xml", "data": ""})
    assert response.status_code == 400


def test_client_onboarding_import_creates_clients(generated_client_client):
    csv_data = "Client name,Tier,Launch date,Kickoff complete\nNorthstar,enterprise,2026-08-01,true\n"
    response = generated_client_client.post("/imports/clients_import/commit", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["status"] == "ok"
    assert body["created_count"] == 1
    listing = generated_client_client.get("/client").json()
    assert any(row["name"] == "Northstar" and row["tier"] == "enterprise" for row in listing)


def test_relation_import_by_integer_id_still_works(generated_client_client):
    generated_client_client.post("/seed")
    csv_data = "client_id,Task title,Status\n1,Prepare kickoff,todo\n"
    response = generated_client_client.post("/imports/onboarding_tasks_import/commit", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["status"] == "ok"
    rows = generated_client_client.get("/onboarding-task").json()
    assert any(row["title"] == "Prepare kickoff" and row["client_id"] == 1 for row in rows)


def test_relation_import_by_label_csv_and_alias_mapping(generated_client_client):
    generated_client_client.post("/seed")
    csv_data = "client,Task title,Status\nAcme Health,Prepare kickoff,todo\n"
    response = generated_client_client.post("/imports/onboarding_tasks_import/preview", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["valid_rows"] == 1
    assert "client_id" in body["mapped_fields"]
    assert body["relation_resolutions"][0]["matched_id"] == 1
    assert body["relation_resolutions"][0]["matched_by"] == "label"
    commit = generated_client_client.post("/imports/onboarding_tasks_import/commit", json={"format": "csv", "data": csv_data}).json()
    assert commit["status"] == "ok"
    rows = generated_client_client.get("/onboarding-task").json()
    assert any(row["title"] == "Prepare kickoff" and row["client_id"] == 1 for row in rows)


def test_relation_import_by_label_json_and_vendor_alias(generated_vendor_client):
    generated_vendor_client.post("/seed")
    payload = json.dumps([{"vendor": "Northstar Payroll", "Summary": "Review SOC report", "Severity": "medium", "State": "open"}])
    response = generated_vendor_client.post("/imports/risk_findings_import/commit", json={"format": "json", "data": payload})
    body = response.json()
    assert body["status"] == "ok"
    rows = generated_vendor_client.get("/risk-finding").json()
    assert any(row["summary"] == "Review SOC report" and row["vendor_id"] == 1 for row in rows)


def test_relation_import_missing_label_reports_clear_error(generated_client_client):
    generated_client_client.post("/seed")
    csv_data = "client,Task title,Status\nUnknown Client,Prepare kickoff,todo\n"
    response = generated_client_client.post("/imports/onboarding_tasks_import/preview", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["invalid_rows"] == 1
    assert "client 'Unknown Client' did not match any Client record" in body["errors"][0]["errors"]


def test_relation_import_ambiguous_label_reports_clear_error(generated_client_client):
    generated_client_client.post("/imports/clients_import/commit", json={"format": "csv", "data": "Client name,Tier\nDuplicate,standard\n"})
    generated_client_client.post("/client", json={"name": "Duplicate", "tier": "premium"})
    csv_data = "client,Task title,Status\nDuplicate,Prepare kickoff,todo\n"
    response = generated_client_client.post("/imports/onboarding_tasks_import/preview", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["invalid_rows"] == 1
    assert "client 'Duplicate' matched multiple Client records" in body["errors"][0]["errors"]


def test_reject_on_invalid_still_rejects_whole_relation_import(generated_client_client):
    generated_client_client.post("/seed")
    csv_data = "client,Task title,Status\nAcme Health,Good task,todo\nUnknown Client,Bad task,todo\n"
    response = generated_client_client.post("/imports/onboarding_tasks_import/commit", json={"format": "csv", "data": csv_data})
    body = response.json()
    assert body["status"] == "rejected"
    assert body["created_count"] == 0
    assert body["skipped_count"] == 2
    rows = generated_client_client.get("/onboarding-task").json()
    assert all(row["title"] != "Good task" for row in rows)


# --------------------------------------------------------------------------- #
# Provider Runtime v0 — schema, generation, and generated backend
# --------------------------------------------------------------------------- #


def _pack_with_provider(replace_providers=None, replace_imports=None):
    data = _pack_with_imports(replace_imports=replace_imports)
    data["model"]["providers"] = replace_providers if replace_providers is not None else [
        {
            "id": "github_issues",
            "label": "GitHub Issues",
            "type": "github_issues",
            "mode": "read_only",
            "target_import": "tickets_import",
            "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"},
            "source": {"state": "open", "labels": []},
        }
    ]
    return data


def test_provider_config_loads_for_github_issues_pack():
    pack = load_pack(PACKS_DIR / "github-issues-workspace" / "domain-pack.yaml")
    assert pack.model is not None
    assert pack.model.providers[0].id == "github_issues"
    assert pack.model.providers[0].target_import == "github_issues_import"
    assert pack.model.imports[0].upsert_key == "external_id"


def test_provider_schema_validation_failures():
    with pytest.raises(Exception, match="provider id 'github_issues' is duplicated"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[
            {"id": "github_issues", "type": "github_issues", "mode": "read_only", "target_import": "tickets_import", "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"}},
            {"id": "github_issues", "type": "github_issues", "mode": "read_only", "target_import": "tickets_import", "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"}},
        ]))
    with pytest.raises(Exception, match="unsupported provider type"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[{"id": "bad", "type": "jira", "mode": "read_only", "target_import": "tickets_import", "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"}}]))
    with pytest.raises(Exception, match="unsupported provider mode"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[{"id": "bad", "type": "github_issues", "mode": "write_back", "target_import": "tickets_import", "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"}}]))
    with pytest.raises(Exception, match="target_import is required"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[{"id": "bad", "type": "github_issues", "mode": "read_only", "target_import": "", "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"}}]))
    with pytest.raises(Exception, match="target_import references unknown import"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[{"id": "bad", "type": "github_issues", "mode": "read_only", "target_import": "missing", "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"}}]))
    with pytest.raises(Exception):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[{"id": "bad", "type": "github_issues", "mode": "read_only", "target_import": "tickets_import", "env": {"token": "github-token", "repo": "GITHUB_REPO"}}]))


def test_generated_provider_metadata_and_files(tmp_path):
    pack = load_pack(PACKS_DIR / "github-issues-workspace" / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    meta = json.loads((out / "app-model.json").read_text())
    assert meta["providers"][0]["id"] == "github_issues"
    assert meta["providers"][0]["targetImport"] == "github_issues_import"
    assert (out / "backend/app/providers.py").exists()
    assert "GET /providers" not in (out / "README.md").read_text()  # docs are user-facing, not route dumps
    assert "GITHUB_TOKEN=" in (out / ".env.example").read_text()
    assert "GITHUB_REPO=owner/repo" in (out / ".env.example").read_text()
    main = (out / "backend/app/main.py").read_text()
    assert "@app.get('/providers')" in main
    assert "@app.post('/providers/{provider_id}/preview')" in main
    assert "@app.post('/providers/{provider_id}/sync')" in main
    app = (out / "frontend/src/App.tsx").read_text()
    assert "function ProviderPanel" in app
    assert 'data-ui-control="providers-nav"' in app
    assert 'data-ui-action="provider-preview"' in app
    assert 'data-ui-state={ready ? \'configured\' : \'missing-env\'}' in app


def test_pack_without_providers_does_not_generate_provider_runtime(tmp_path):
    pack = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    assert not (out / "backend/app/providers.py").exists()
    assert not (out / ".env.example").exists()
    app = (out / "frontend/src/App.tsx").read_text()
    assert "function ProviderPanel" in app
    assert "model.providers.length > 0" in app


@pytest.fixture
def generated_github_client(tmp_path, monkeypatch):
    return _make_generated_client(tmp_path, monkeypatch, "github-issues-workspace")


def test_generated_provider_list_endpoint_hides_secrets(generated_github_client, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    response = generated_github_client.get("/providers")
    assert response.status_code == 200
    provider = response.json()[0]
    assert provider["id"] == "github_issues"
    assert provider["target_import"] == "github_issues_import"
    assert provider["env_status"]["configured"] is False
    assert set(provider["env_status"]["missing"]) == {"GITHUB_TOKEN", "GITHUB_REPO"}
    assert "test-token" not in json.dumps(provider)


def test_generated_provider_preview_sync_and_upsert(generated_github_client, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    from app import providers
    fixture = [
        {"number": 777, "title": "Sync me", "body": "body", "state": "open", "html_url": "https://github.com/owner/repo/issues/777", "labels": [{"name": "bug"}], "user": {"login": "octocat"}, "updated_at": "2026-05-15T00:00:00Z"},
        {"number": 778, "title": "Ignore PR", "state": "open", "pull_request": {"url": "https://api.github.com/pr/778"}},
    ]
    monkeypatch.setattr(providers, "fetch_github_issues", lambda provider: fixture)
    preview = generated_github_client.post("/providers/github_issues/preview")
    assert preview.status_code == 200
    assert preview.json()["total_rows"] == 1
    first = generated_github_client.post("/providers/github_issues/sync").json()
    second = generated_github_client.post("/providers/github_issues/sync").json()
    assert first["created_count"] == 1
    assert second["updated_count"] == 1
    rows = generated_github_client.get("/issue").json()
    assert len([row for row in rows if row["external_id"] == "777"]) == 1
    runs = generated_github_client.get("/providers/runs").json()
    assert runs and runs[0]["format"] == "provider"


def test_generated_provider_missing_env_error(generated_github_client, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    response = generated_github_client.post("/providers/github_issues/sync")
    assert response.status_code == 400
    assert "missing provider env vars" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# HTTP JSON Provider v0 — schema, generation, generated backend
# --------------------------------------------------------------------------- #


def _http_json_provider_block(**overrides):
    base = {
        "id": "external_vendor_feed",
        "label": "External Vendor Feed",
        "type": "http_json",
        "mode": "read_only",
        "target_import": "tickets_import",
        "env": {"url": "EXTERNAL_VENDOR_FEED_URL", "token": "EXTERNAL_VENDOR_FEED_TOKEN"},
        "source": {"records_path": "data", "auth": "bearer"},
    }
    base.update(overrides)
    return base


def test_http_json_provider_config_loads():
    pack = load_pack(PACKS_DIR / "http-json-vendor-feed" / "domain-pack.yaml")
    assert pack.model is not None
    provider = pack.model.providers[0]
    assert provider.type == "http_json"
    assert provider.env.url == "EXTERNAL_VENDOR_FEED_URL"
    assert provider.env.token == "EXTERNAL_VENDOR_FEED_TOKEN"
    assert provider.env.repo == ""
    assert provider.source.records_path == "data"
    assert provider.source.auth == "bearer"


def test_http_json_provider_minimal_no_token_no_records_path():
    block = _http_json_provider_block(
        env={"url": "EXAMPLE_FEED_URL"},
        source={"auth": "none"},
    )
    pack = DomainPack.model_validate(_pack_with_provider(replace_providers=[block]))
    assert pack.model.providers[0].env.token == ""
    assert pack.model.providers[0].source.records_path == ""
    assert pack.model.providers[0].source.auth == "none"


def test_http_json_provider_schema_validation_failures():
    with pytest.raises(Exception, match="requires env.url"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[
            _http_json_provider_block(env={"url": "", "token": "TOK"}),
        ]))
    with pytest.raises(Exception, match="source.auth"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[
            _http_json_provider_block(source={"records_path": "data", "auth": "oauth"}),
        ]))
    with pytest.raises(Exception, match="records_path"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[
            _http_json_provider_block(source={"records_path": "Bad-Path!", "auth": "bearer"}),
        ]))
    with pytest.raises(Exception, match="env.url"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[
            _http_json_provider_block(env={"url": "not_uppercase", "token": "TOK"}),
        ]))
    with pytest.raises(Exception, match="target_import references unknown import"):
        DomainPack.model_validate(_pack_with_provider(replace_providers=[
            _http_json_provider_block(target_import="missing_import"),
        ]))


def test_github_issues_pack_still_validates_after_schema_changes():
    pack = load_pack(PACKS_DIR / "github-issues-workspace" / "domain-pack.yaml")
    provider = pack.model.providers[0]
    assert provider.type == "github_issues"
    assert provider.env.token == "GITHUB_TOKEN"
    assert provider.env.repo == "GITHUB_REPO"
    assert provider.env.url == ""


def test_http_json_generated_metadata_and_files(tmp_path):
    pack = load_pack(PACKS_DIR / "http-json-vendor-feed" / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    meta = json.loads((out / "app-model.json").read_text())
    assert meta["providers"][0]["type"] == "http_json"
    assert meta["providers"][0]["env"]["url"] == "EXTERNAL_VENDOR_FEED_URL"
    assert meta["providers"][0]["source"]["records_path"] == "data"
    assert (out / "backend/app/providers.py").exists()
    env_example = (out / ".env.example").read_text()
    assert "EXTERNAL_VENDOR_FEED_URL=" in env_example
    assert "EXTERNAL_VENDOR_FEED_TOKEN=" in env_example
    providers_module = (out / "backend/app/providers.py").read_text()
    assert "def fetch_http_json" in providers_module
    assert "_extract_http_json_records" in providers_module
    backend_test = (out / "backend/tests/test_model_driven_app.py").read_text()
    assert "fetch_http_json" in backend_test
    assert "EXTERNAL_VENDOR_FEED_URL" in backend_test


def test_http_json_env_example_omits_token_when_unconfigured(tmp_path):
    data = _pack_with_provider(replace_providers=[_http_json_provider_block(
        env={"url": "ONLY_URL"},
        source={"auth": "none"},
    )])
    pack = DomainPack.model_validate(data)
    out = tmp_path / pack.name
    generate(pack, out)
    env_example = (out / ".env.example").read_text()
    assert "ONLY_URL=" in env_example
    assert "TOKEN" not in env_example


def test_http_json_readme_documents_provider(tmp_path):
    pack = load_pack(PACKS_DIR / "http-json-vendor-feed" / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    readme = (out / "README.md").read_text()
    assert "Generic HTTP JSON" in readme
    assert "EXTERNAL_VENDOR_FEED_URL" in readme
    assert "EXTERNAL_VENDOR_FEED_TOKEN" in readme
    assert "mock provider responses" in readme


def test_http_json_frontend_provider_panel_is_reused(tmp_path):
    pack = load_pack(PACKS_DIR / "http-json-vendor-feed" / "domain-pack.yaml")
    out = tmp_path / pack.name
    generate(pack, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "function ProviderPanel" in app
    assert 'data-ui-control="providers-nav"' in app
    assert 'data-ui-action="provider-preview"' in app
    # Provider panel reuses the same ProviderPanel component for any provider type.
    assert app.count("function ProviderPanel") == 1


def test_http_json_generation_is_deterministic(tmp_path):
    pack = load_pack(PACKS_DIR / "http-json-vendor-feed" / "domain-pack.yaml")
    first = tmp_path / "a"
    second = tmp_path / "b"
    generate(pack, first)
    generate(pack, second)
    for relative in ("backend/app/providers.py", "backend/tests/test_model_driven_app.py", "app-model.json", ".env.example", "README.md"):
        assert (first / relative).read_text() == (second / relative).read_text(), relative


@pytest.fixture
def generated_http_json_client(tmp_path, monkeypatch):
    return _make_generated_client(tmp_path, monkeypatch, "http-json-vendor-feed")


def test_generated_http_json_list_endpoint_hides_secrets(generated_http_json_client, monkeypatch):
    monkeypatch.delenv("EXTERNAL_VENDOR_FEED_URL", raising=False)
    monkeypatch.delenv("EXTERNAL_VENDOR_FEED_TOKEN", raising=False)
    response = generated_http_json_client.get("/providers")
    assert response.status_code == 200
    provider = response.json()[0]
    assert provider["type"] == "http_json"
    assert provider["env_status"]["configured"] is False
    assert "EXTERNAL_VENDOR_FEED_URL" in provider["env_status"]["missing"]
    # token only required when bearer configured AND token env var set; with bearer auth + token configured it's in required
    assert provider["env_status"]["required"] == ["EXTERNAL_VENDOR_FEED_URL", "EXTERNAL_VENDOR_FEED_TOKEN"]


def test_generated_http_json_preview_sync_uses_importer(generated_http_json_client, monkeypatch):
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_URL", "https://example.invalid/feed")
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_TOKEN", "should-not-leak")
    from app import providers
    fixture_record = {
        "external_id": "ext-99",
        "name": "Acme Cloud",
        "service_area": "Cloud",
        "risk_level": "high",
        "owner": "ops-team",
        "source_url": "https://example.invalid/vendors/ext-99",
    }
    monkeypatch.setattr(providers, "fetch_http_json", lambda provider: {"data": [fixture_record]})
    preview = generated_http_json_client.post("/providers/external_vendor_feed/preview")
    assert preview.status_code == 200
    assert preview.json()["valid_rows"] == 1
    first = generated_http_json_client.post("/providers/external_vendor_feed/sync").json()
    second = generated_http_json_client.post("/providers/external_vendor_feed/sync").json()
    assert first["created_count"] == 1
    assert second["updated_count"] == 1
    listing = generated_http_json_client.get("/vendor").json()
    assert [row for row in listing if row["external_id"] == "ext-99"]
    runs = generated_http_json_client.get("/providers/runs").json()
    assert runs and runs[0]["format"] == "provider"


def test_generated_http_json_records_path_missing_returns_clear_error(generated_http_json_client, monkeypatch):
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_URL", "https://example.invalid/feed")
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_TOKEN", "tok")
    from app import providers
    monkeypatch.setattr(providers, "fetch_http_json", lambda provider: {"wrong_key": []})
    response = generated_http_json_client.post("/providers/external_vendor_feed/preview")
    assert response.status_code == 400
    assert "records_path" in response.json()["detail"]


def test_generated_http_json_records_not_a_list_returns_clear_error(generated_http_json_client, monkeypatch):
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_URL", "https://example.invalid/feed")
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_TOKEN", "tok")
    from app import providers
    monkeypatch.setattr(providers, "fetch_http_json", lambda provider: {"data": "not-a-list"})
    response = generated_http_json_client.post("/providers/external_vendor_feed/preview")
    assert response.status_code == 400
    assert "not a list" in response.json()["detail"]


def test_generated_http_json_record_not_object_returns_clear_error(generated_http_json_client, monkeypatch):
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_URL", "https://example.invalid/feed")
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_TOKEN", "tok")
    from app import providers
    monkeypatch.setattr(providers, "fetch_http_json", lambda provider: {"data": ["just-a-string"]})
    response = generated_http_json_client.post("/providers/external_vendor_feed/preview")
    assert response.status_code == 400
    assert "JSON object" in response.json()["detail"]


def test_generated_http_json_bearer_token_only_when_configured(generated_http_json_client, monkeypatch):
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_URL", "https://example.invalid/feed")
    monkeypatch.setenv("EXTERNAL_VENDOR_FEED_TOKEN", "secret-token")
    from app import providers
    headers_with = providers._http_json_request_headers(providers.PROVIDERS[0])
    assert headers_with.get("Authorization") == "Bearer secret-token"
    monkeypatch.delenv("EXTERNAL_VENDOR_FEED_TOKEN", raising=False)
    headers_without = providers._http_json_request_headers(providers.PROVIDERS[0])
    assert "Authorization" not in headers_without
