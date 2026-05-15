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
    assert "No items yet." in app
    assert "humanize" in app and "replace(/_/g, ' ')" in app
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
    assert "Client Onboarding Command Center" in client_app
    assert "Vendor Risk Register" in vendor_app
    assert "composition-board-workspace" in client_app
    assert "workspace-main" in client_app
    assert '"recipe": "workspace_board"' in client_app
    assert "composition-register-table" in vendor_app
    assert "register-main" in vendor_app
    assert "register-card" in vendor_app
    assert '"recipe": "executive_register"' in vendor_app
    assert "No records yet" in vendor_app
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
    assert "titleize(`${ctx.primary.labelPlural} Board`)" in client_app
    assert "titleize(`${ctx.primary.labelPlural} Register`)" in vendor_app
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
    assert "max-width:1440px" in styles
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
    assert "isPrimaryActive && model.ui.composition === 'board_workspace'" in app
    assert "isPrimaryActive && model.ui.composition === 'register_table'" in app
    assert "<FocusedSurface" in app
    assert 'data-ui-layout="composition-focused"' in app


def test_side_panel_dedupes_secondary_rows(tmp_path):
    vendor = load_pack(PACKS_DIR / "vendor-risk-tracker" / "domain-pack.yaml")
    out = tmp_path / vendor.name
    generate(vendor, out)
    app = (out / "frontend/src/App.tsx").read_text()
    assert "const uniqueById =" in app
    assert "uniqueById(ctx.rowsByEntity[ctx.secondary.name]" in app
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
    for rel in ["backend/app/main.py", "backend/app/models.py", "frontend/src/App.tsx", "app-model.json"]:
        assert (first / rel).read_text() == (second / rel).read_text()
