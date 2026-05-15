"""
Core generation logic: copy template + apply domain pack substitutions.

v0.1 strategy: copy the fastapi-react template to the output directory, then
substitute the handful of app-name tokens that differ between packs. Fixture
records are also emitted from the domain pack's seed_data hints.

This proves the generator flow end-to-end. Later milestones will introduce
per-capability code generation using Jinja2 templates.
"""
import json
import shutil
import textwrap
from pathlib import Path

from agentforge.model_driven import generate_model_driven_app
from agentforge.modules import select_modules
from agentforge.pack import DomainPack

def _build_substitutions(pack: DomainPack) -> list[tuple[str, str]]:
    slug = pack.name.replace("-", "_")
    return [
        ("hybrid-scoring-demo", pack.name),
        ("Hybrid Scoring Demo", pack.display_name),
        ("hybrid_scoring_demo", slug),
        ("scoring_demo",        slug),
        ("project-workspace-demo", pack.name),
        ("Project Workspace Demo", pack.display_name),
        ("project_workspace_demo", slug),
    ]

# File extensions we consider "text" for substitution
_TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".json", ".yaml", ".yml",
    ".md", ".html", ".env", ".ini", ".txt", ".toml",
}

# Files/dirs to skip when copying the template
_SKIP_NAMES = {"__pycache__", ".pytest_cache", "node_modules", "dist", ".venv", "venv"}


def _template_root(template: str = "fastapi-react") -> Path:
    return Path(__file__).parent.parent.parent / "templates" / template


def _docker_compose_template() -> Path:
    return Path(__file__).parent.parent.parent / "templates" / "docker-compose" / "docker-compose.yml"


def _ci_template_root() -> Path:
    return Path(__file__).parent.parent.parent / "templates" / "ci"


def generate(pack: DomainPack, output_dir: Path, *, dry_run: bool = False) -> dict:
    """
    Generate the app for the given domain pack into output_dir.

    Returns a manifest dict with: output_dir, template, files_written, gaps.
    Raises if output_dir already exists (use --force to overwrite).
    """
    selection = select_modules(pack)
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    if pack.app_archetype == "model_driven_app":
        files_written = generate_model_driven_app(pack, output_dir, dry_run=dry_run)
        return {
            "output_dir": str(output_dir),
            "template": selection.template,
            "archetype": selection.archetype,
            "modules": sorted(selection.active),
            "gaps": selection.gaps,
            "files_written": len(files_written),
            "dry_run": dry_run,
        }

    template_root = _template_root(selection.template)

    if not template_root.exists():
        raise FileNotFoundError(f"template not found: {template_root}")

    files_written: list[str] = []
    substitutions = _build_substitutions(pack)

    def _substitute(text: str) -> str:
        for token, replacement in substitutions:
            text = text.replace(token, replacement)
        return text

    def _copy_tree(src: Path, dst: Path) -> None:
        for item in src.iterdir():
            if item.name in _SKIP_NAMES:
                continue
            target = dst / item.name
            if item.is_dir():
                if not dry_run:
                    target.mkdir(parents=True, exist_ok=True)
                _copy_tree(item, target)
            else:
                if item.suffix in _TEXT_EXTENSIONS:
                    text = item.read_text(encoding="utf-8")
                    text = _substitute(text)
                    if not dry_run:
                        target.write_text(text, encoding="utf-8")
                else:
                    if not dry_run:
                        shutil.copy2(item, target)
                files_written.append(str(target.relative_to(output_dir) if not dry_run else item))

    if not dry_run:
        _copy_tree(template_root, output_dir)
    else:
        _copy_tree(template_root, output_dir)  # still walks to collect files_written list

    # Emit docker-compose.yml at the output root
    dc_src = _docker_compose_template()
    if dc_src.exists():
        dc_text = dc_src.read_text(encoding="utf-8")
        dc_text = _substitute(dc_text)
        dc_dst = output_dir / "docker-compose.yml"
        if not dry_run:
            dc_dst.write_text(dc_text, encoding="utf-8")
        files_written.append("docker-compose.yml")

    # Copy CI skeleton (.github/workflows/)
    ci_root = _ci_template_root()
    if ci_root.exists():
        _copy_tree(ci_root, output_dir)

    # Emit run_commands.txt
    commands = _build_run_commands(pack)
    cmd_dst = output_dir / "run_commands.txt"
    if not dry_run:
        cmd_dst.write_text(commands, encoding="utf-8")
    files_written.append("run_commands.txt")

    # Emit deterministic frontend customization config when the template has a frontend.
    customization_path = output_dir / "frontend" / "src" / "customization.ts"
    if not dry_run and customization_path.parent.exists():
        customization_path.write_text(_build_frontend_customization(pack), encoding="utf-8")
    files_written.append("frontend/src/customization.ts")

    return {
        "output_dir": str(output_dir),
        "template": selection.template,
        "archetype": selection.archetype,
        "modules": sorted(selection.active),
        "gaps": selection.gaps,
        "files_written": len(files_written),
        "dry_run": dry_run,
    }


def _build_run_commands(pack: DomainPack) -> str:
    tests = pack.tests if isinstance(pack.tests, dict) else pack.tests.model_dump()
    commands = tests.get("commands", {})
    backend_cmd = commands.get("backend", "pytest")
    frontend_build = commands.get("frontend_build", "npm run build")
    frontend_lint = commands.get("frontend_lint", "npm run lint")
    e2e_cmd = commands.get("e2e", "npm run test:e2e")

    return textwrap.dedent(f"""\
        # {pack.display_name} — local validation commands
        # Generated by AgentForge generator for pack: {pack.name}

        ## Start local services
        docker compose up -d db

        ## Backend
        cd backend
        pip install -r requirements-dev.txt
        {backend_cmd}

        ## Frontend
        cd ../frontend
        npm install
        {frontend_build}
        {frontend_lint}

        ## E2E (requires running app)
        # Start backend with local SQLite demo DB:
        #   DATABASE_URL=sqlite+aiosqlite:///./demo.db uvicorn app.main:app --reload
        # Windows cmd:
        #   set DATABASE_URL=sqlite+aiosqlite:///./demo.db && uvicorn app.main:app --reload
        # PowerShell:
        #   $env:DATABASE_URL="sqlite+aiosqlite:///./demo.db"; uvicorn app.main:app --reload
        # Start frontend: npm run dev
        {e2e_cmd}

        ## Full stack (Docker Compose)
        docker compose up --build
    """)


def _build_frontend_customization(pack: DomainPack) -> str:
    config = _resolved_customization(pack)
    payload = json.dumps(config, indent=2)
    return f"""// Generated by AgentForge from the App Blueprint customization block.
// Edit the Blueprint and regenerate to change these labels deterministically.
export const customization = {payload} as const;
"""


def _resolved_customization(pack: DomainPack) -> dict:
    customization = pack.customization
    target_user = customization.app.target_user_label or (pack.domain.target_users[0] if pack.domain.target_users else "operator")
    subtitle = customization.app.subtitle or " ".join(pack.domain.product_purpose.split()) or f"Generated local app for {target_user}."
    workflow_label = customization.app.workflow_label or (
        "Project command center" if pack.app_archetype == "project_workspace_app" else "Review workflow"
    )

    scoring_record = customization.scoring.record_label
    project_label = customization.project_workspace.project_label
    task_label = customization.project_workspace.task_label

    default_agent_starters = (
        ["list tasks", "summarize project", "pin task list"]
        if pack.app_archetype == "project_workspace_app"
        else ["score the records", "show best records", "pin the scored records to the workspace"]
    )

    resolved = {
        "app": {
            "name": pack.display_name,
            "subtitle": subtitle,
            "targetUserLabel": target_user,
            "workflowLabel": workflow_label,
        },
        "agentStarters": customization.agent_starters or default_agent_starters,
        "workspace": {
            "emptyState": customization.workspace.empty_state or (
                "Ask the agent to pin a project summary or task list."
                if pack.app_archetype == "project_workspace_app"
                else "Ask the agent to pin scored records, notification previews, or action history."
            ),
            "widgetLabel": customization.workspace.widget_label or "widgets",
            "pinnedLabel": customization.workspace.pinned_label or "Pinned context",
        },
    }
    if pack.app_archetype == "project_workspace_app":
        resolved["projectWorkspace"] = {
            "projectLabel": {
                "singular": project_label.singular or "project",
                "plural": project_label.plural or "projects",
            },
            "taskLabel": {
                "singular": task_label.singular or "task",
                "plural": task_label.plural or "tasks",
            },
            "activityLabel": customization.project_workspace.activity_label or "Notes and activity",
            "sampleDataLabel": customization.project_workspace.sample_data_label or "sample workspace",
        }
        return resolved

    resolved["scoring"] = {
        "recordLabel": {
            "singular": scoring_record.singular or "record",
            "plural": scoring_record.plural or "records",
        },
        "criteriaLabels": customization.scoring.criteria_labels or ["Fit", "Priority", "Risk"],
        "reviewQueueLabel": customization.scoring.review_queue_label or "Scored Records",
        "notificationLabel": customization.scoring.notification_label or "Notification Previews",
        "sampleDataLabel": customization.scoring.sample_data_label or "demo records",
    }
    return resolved
