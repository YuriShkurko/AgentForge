"""Tests for domain pack loading and validation."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.pack import DomainPack, load_pack

PACKS_DIR = Path(__file__).parent.parent.parent / "domain-packs"


def test_load_hybrid_scoring_demo():
    pack = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    assert pack.name == "hybrid-scoring-demo"
    assert pack.app_archetype == "ingestion_scoring_pipeline"
    assert "pipeline" in pack.required_shell_modules
    assert "provider_adapter" in pack.required_shell_modules


def test_load_business_insight():
    pack = load_pack(PACKS_DIR / "business-insight" / "domain-pack.yaml")
    assert pack.name == "business-insight"
    assert pack.app_archetype == "agent_dashboard_app"
    assert "agent" in pack.required_shell_modules


def test_load_ai_job_radar():
    pack = load_pack(PACKS_DIR / "ai-job-radar" / "domain-pack.yaml")
    assert pack.name == "ai-job-radar"
    assert pack.app_archetype == "ingestion_scoring_pipeline"
    assert "pipeline" in pack.required_shell_modules


def test_invalid_archetype_raises():
    with pytest.raises(Exception, match="unknown app_archetype"):
        DomainPack.model_validate({
            "name": "bad",
            "display_name": "Bad",
            "app_archetype": "not_a_real_archetype",
            "required_shell_modules": ["pipeline"],
            "domain": {"domain_name": "Bad", "app_type": "bad"},
        })


def test_unknown_module_raises():
    with pytest.raises(Exception, match="unknown shell modules"):
        DomainPack.model_validate({
            "name": "bad",
            "display_name": "Bad",
            "app_archetype": "ingestion_scoring_pipeline",
            "required_shell_modules": ["pipeline", "does_not_exist"],
            "domain": {"domain_name": "Bad", "app_type": "pipeline"},
        })


def test_agent_archetype_without_agent_module_raises():
    with pytest.raises(Exception, match="'agent'"):
        DomainPack.model_validate({
            "name": "bad",
            "display_name": "Bad",
            "app_archetype": "agent_dashboard_app",
            "required_shell_modules": ["workspace", "test"],
            "domain": {"domain_name": "Bad", "app_type": "agent"},
        })
