import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.modules import ARCHETYPE_REQUIRED_MODULES, select_modules
from agentforge.pack import DomainPack

PACKS_DIR = Path(__file__).parent.parent.parent / "domain-packs"


def _pack(archetype: str, required: list[str], optional: list[str] | None = None) -> DomainPack:
    return DomainPack.model_validate({
        "name": "test",
        "display_name": "Test",
        "app_archetype": archetype,
        "required_shell_modules": required,
        "optional_shell_modules": optional or [],
        "domain": {"domain_name": "Test", "app_type": archetype},
    })


def test_ingestion_pipeline_selects_fastapi_react():
    pack = _pack("ingestion_scoring_pipeline", ["pipeline", "provider_adapter", "scoring_explanation", "operations_ui", "persistence", "test"])
    sel = select_modules(pack)
    assert sel.template == "fastapi-react"
    assert sel.archetype == "ingestion_scoring_pipeline"


def test_agent_dashboard_selects_fastapi_react():
    pack = _pack("agent_dashboard_app", ["agent", "workspace", "provider_adapter", "test"])
    sel = select_modules(pack)
    assert sel.template == "fastapi-react"


def test_required_modules_preserved():
    modules = ["pipeline", "provider_adapter", "scoring_explanation", "operations_ui", "persistence", "test"]
    pack = _pack("ingestion_scoring_pipeline", modules)
    sel = select_modules(pack)
    assert sel.required == set(modules)


def test_optional_modules_preserved():
    pack = _pack(
        "ingestion_scoring_pipeline",
        ["pipeline", "provider_adapter", "scoring_explanation", "operations_ui", "persistence", "test"],
        optional=["notification_action", "agent_runtime"],
    )
    sel = select_modules(pack)
    assert "notification_action" in sel.optional
    assert "agent_runtime" in sel.optional


def test_workspace_module_flagged_as_gap():
    pack = _pack("agent_dashboard_app", ["agent", "workspace", "provider_adapter", "test"])
    sel = select_modules(pack)
    assert any("workspace" in g for g in sel.gaps)


def test_hybrid_scoring_demo_pack_selects_correctly():
    from agentforge.pack import load_pack
    pack = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    sel = select_modules(pack)
    assert sel.archetype == "ingestion_scoring_pipeline"
    assert sel.template == "fastapi-react"
    assert "pipeline" in sel.required
    assert "scoring_explanation" in sel.required


def test_business_insight_identifies_gaps():
    from agentforge.pack import load_pack
    pack = load_pack(PACKS_DIR / "business-insight" / "domain-pack.yaml")
    sel = select_modules(pack)
    assert sel.archetype == "agent_dashboard_app"
    # workspace is in required_shell_modules; flagged as not yet in template
    assert any("workspace" in g for g in sel.gaps)


def test_ai_job_radar_identifies_observability_gap():
    from agentforge.pack import load_pack
    pack = load_pack(PACKS_DIR / "ai-job-radar" / "domain-pack.yaml")
    sel = select_modules(pack)
    assert any("observability_debug" in g for g in sel.gaps)
