"""Generator tests — dry-run and snapshot checks."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.generator import generate
from agentforge.pack import load_pack

PACKS_DIR = Path(__file__).parent.parent.parent / "domain-packs"
SNAPSHOTS_DIR = Path(__file__).parent.parent / "snapshots"

EXPECTED_BACKEND_FILES = [
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/app/database.py",
    "backend/app/models.py",
    "backend/app/schemas.py",
    "backend/app/providers/interface.py",
    "backend/app/providers/fixture/provider.py",
    "backend/app/adapters/normalize.py",
    "backend/app/adapters/scoring.py",
    "backend/app/services/ingest.py",
    "backend/app/services/score.py",
    "backend/app/services/actions.py",
    "backend/app/routers/ingest.py",
    "backend/app/routers/records.py",
    "backend/app/routers/runs.py",
    "backend/app/routers/actions.py",
    "backend/requirements.txt",
]

EXPECTED_FRONTEND_FILES = [
    "frontend/src/App.tsx",
    "frontend/src/api.ts",
    "frontend/src/types.ts",
    "frontend/src/components/OpsPanel.tsx",
    "frontend/src/components/RunHistoryTable.tsx",
    "frontend/src/components/ScoredRecordsTable.tsx",
    "frontend/src/components/ActionStatusBadge.tsx",
    "frontend/index.html",
    "frontend/package.json",
]

EXPECTED_ROOT_FILES = [
    "docker-compose.yml",
    "run_commands.txt",
    ".github/workflows/ci.yml",
]


def test_dry_run_returns_manifest():
    pack = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    result = generate(pack, Path("/nonexistent/output"), dry_run=True)
    assert result["dry_run"] is True
    assert result["archetype"] == "ingestion_scoring_pipeline"
    assert result["template"] == "fastapi-react"
    assert result["files_written"] > 0


def test_generate_writes_expected_files(tmp_path):
    pack = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    output = tmp_path / "hybrid-scoring-demo"
    result = generate(pack, output)

    assert result["dry_run"] is False

    for rel_path in EXPECTED_BACKEND_FILES + EXPECTED_FRONTEND_FILES + EXPECTED_ROOT_FILES:
        assert (output / rel_path).exists(), f"expected file missing: {rel_path}"


def test_generate_substitutes_pack_name(tmp_path):
    pack = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    output = tmp_path / pack.name
    generate(pack, output)

    config_text = (output / "backend" / "app" / "config.py").read_text()
    assert "hybrid-scoring-demo" in config_text
    assert pack.display_name in (output / "frontend" / "index.html").read_text()


def test_run_commands_mentions_pack(tmp_path):
    pack = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    output = tmp_path / pack.name
    generate(pack, output)

    commands = (output / "run_commands.txt").read_text()
    assert pack.display_name in commands
    assert "pytest" in commands
    assert "npm run build" in commands


def test_generate_reports_gaps(tmp_path):
    pack = load_pack(PACKS_DIR / "business-insight" / "domain-pack.yaml")
    output = tmp_path / pack.name
    result = generate(pack, output)
    assert len(result["gaps"]) > 0


def test_snapshot_matches(tmp_path):
    """Generate the demo pack and verify key file structure matches snapshot expectations."""
    pack = load_pack(PACKS_DIR / "hybrid-scoring-demo" / "domain-pack.yaml")
    output = tmp_path / pack.name
    result = generate(pack, output)

    # Snapshot: all expected files must exist
    for rel_path in EXPECTED_BACKEND_FILES + EXPECTED_FRONTEND_FILES + EXPECTED_ROOT_FILES:
        assert (output / rel_path).exists(), f"snapshot mismatch — missing: {rel_path}"

    # Snapshot: no generator placeholder tokens left unreplaced
    # (React uses {{ }} for inline styles — check only explicit generator markers)
    for rel_path in EXPECTED_BACKEND_FILES + EXPECTED_FRONTEND_FILES:
        content = (output / rel_path).read_text(errors="ignore")
        assert "{{PACK_" not in content, f"unreplaced generator token in {rel_path}"
        assert "__PACK_NAME__" not in content, f"unreplaced generator token in {rel_path}"

    # Snapshot: required module list correct (notification_action is optional in this pack)
    assert set(result["modules"]) == {
        "pipeline", "provider_adapter", "scoring_explanation",
        "operations_ui", "persistence", "test",
    }
