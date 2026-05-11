"""Analysis-only local repository analyzer for AgentForge v0.7."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

IGNORED_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build",
    ".next", "coverage", "playwright-report", "test-results", ".scribe", ".tmp",
}
TEST_DIR_NAMES = {"test", "tests", "e2e", "spec", "specs", "__tests__"}
TEXT_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".env", ".ini", ".cfg", ".html", ".css"}
CONFIG_FILES = {
    "pyproject.toml", "requirements.txt", "requirements-dev.txt", "package.json", "package-lock.json",
    "pnpm-lock.yaml", "yarn.lock", "vite.config.ts", "vite.config.js", "next.config.js", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml", "Makefile", "pytest.ini", "playwright.config.ts",
}
MODULES = [
    "provider_adapter", "pipeline", "scoring_explanation", "notification_action", "triage_ui",
    "agent_runtime", "dashboard_workspace", "deterministic_test_harness", "ci_local_validation", "observability_debug",
]


@dataclass(frozen=True)
class AnalyzeOptions:
    max_files: int = 1000
    include_tests: bool = False
    include_blueprint_draft: bool = True
    report_format: str = "text"


def analyze_repo(path: str | Path, options: AnalyzeOptions | None = None) -> dict[str, Any]:
    """Analyze a local repository without modifying it."""
    opts = options or AnalyzeOptions()
    root = Path(path).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"repository path not found: {root}")
    if not root.is_dir():
        raise ValueError(f"repository path is not a directory: {root}")
    root = root.resolve()

    files, ignored, unreadable, cap_hit = _scan_files(root, opts)
    file_set = {f["path"] for f in files}
    snippets = {f["path"]: f.get("snippet", "") for f in files}
    top_dirs = sorted({p.split("/", 1)[0] for p in file_set if "/" in p})
    package_files = sorted(p for p in file_set if Path(p).name in CONFIG_FILES or Path(p).name.endswith(".csproj"))

    signals = _detect_signals(file_set, snippets)
    architecture = _architecture_signals(file_set, snippets)
    compatibility = _compatibility(signals, architecture)
    archetypes = _archetypes(signals, architecture, compatibility)
    risks = _risks(signals, architecture, file_set, cap_hit, unreadable)
    migration = _migration_plan(compatibility, risks)
    blueprint = _blueprint_seed(root.name, archetypes, compatibility, signals) if opts.include_blueprint_draft else None

    return {
        "repo": {
            "name": root.name,
            "path": str(root),
            "is_git_repo": (root / ".git").exists(),
            "top_level_dirs": top_dirs,
            "package_files": package_files,
            "monorepo_likely": _is_monorepo(file_set),
            "max_files": opts.max_files,
            "scan_cap_hit": cap_hit,
        },
        "detected_stack": signals,
        "architecture_signals": architecture,
        "archetype_candidates": archetypes,
        "module_compatibility": compatibility,
        "risks": risks,
        "migration_plan": migration,
        "blueprint_seed": blueprint,
        "ignored_paths": ignored,
        "unreadable_paths": unreadable,
        "scanned_files": [f["path"] for f in files],
    }


def _scan_files(root: Path, opts: AnalyzeOptions) -> tuple[list[dict[str, str]], list[str], list[str], bool]:
    files: list[dict[str, str]] = []
    ignored: set[str] = set()
    unreadable: list[str] = []
    cap_hit = False
    for current, dirs, names in __import__("os").walk(root):
        cur = Path(current)
        rel_cur = _rel(root, cur)
        kept_dirs = []
        for d in sorted(dirs):
            rel = d if rel_cur == "." else f"{rel_cur}/{d}"
            if d in IGNORED_DIRS or (not opts.include_tests and d.lower() in TEST_DIR_NAMES):
                ignored.add(rel)
            else:
                kept_dirs.append(d)
        dirs[:] = kept_dirs
        for name in sorted(names):
            if len(files) >= opts.max_files:
                cap_hit = True
                dirs[:] = []
                break
            path = cur / name
            rel = _rel(root, path)
            entry: dict[str, str] = {"path": rel}
            if _is_text_like(path):
                try:
                    entry["snippet"] = path.read_text(encoding="utf-8", errors="ignore")[:20000].lower()
                except OSError:
                    unreadable.append(rel)
            files.append(entry)
    return files, sorted(ignored), sorted(unreadable), cap_hit


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix() if path != root else "."


def _is_text_like(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in CONFIG_FILES or path.name.startswith(".env")


def _detect_signals(file_set: set[str], snippets: dict[str, str]) -> dict[str, list[str]]:
    s: dict[str, set[str]] = {k: set() for k in ["backend", "frontend", "data", "testing", "devops", "ai_agent", "observability"]}
    names = {Path(p).name: p for p in file_set}
    all_text = "\n".join(snippets.values())
    def add(group: str, label: str, evidence: str) -> None:
        s[group].add(f"{label}: {evidence}")
    for name in ["pyproject.toml", "requirements.txt"]:
        if name in names: add("backend", "python", names[name])
    if "package.json" in names:
        add("backend", "node/typescript", names["package.json"]); add("frontend", "package.json", names["package.json"])
    for p, text in snippets.items():
        if "fastapi" in text: add("backend", "fastapi", p)
        if "flask" in text: add("backend", "flask", p)
        if "django" in text: add("backend", "django", p)
        if "express" in text: add("backend", "express", p)
        if "next" in text or "next.config" in p: add("frontend", "nextjs", p)
        if "react" in text or p.endswith((".tsx", ".jsx")): add("frontend", "react", p)
        if "vite" in text or "vite.config" in p: add("frontend", "vite", p)
        if "tailwind" in text: add("frontend", "tailwind", p)
        for label in ["postgres", "sqlite", "mongodb", "sqlalchemy", "prisma", "alembic"]:
            if label in text or label in p.lower(): add("data", label, p)
        for label in ["pytest", "vitest", "playwright", "jest", "cypress"]:
            if label in text or label in p.lower(): add("testing", label, p)
        for label in ["openai", "llm", "tool_call", "chat", "server-sent", "eventsource", "websocket", "prompt", "mcp"]:
            if label in text or label.replace("-", "_") in text: add("ai_agent", label, p)
        for label in ["prometheus", "grafana", "metrics", "health", "logging"]:
            if label in text or label in p.lower(): add("observability", label, p)
    for p in file_set:
        name = Path(p).name
        if name == "Dockerfile" or name.startswith("docker-compose"): add("devops", "docker", p)
        if name == "Makefile": add("devops", "makefile", p)
        if p.startswith(".github/workflows/"): add("devops", "github_actions", p)
        if name.startswith(".env") and ("example" in name or "sample" in name): add("devops", "env_example", p)
    return {k: sorted(v) for k, v in s.items()}


def _architecture_signals(file_set: set[str], snippets: dict[str, str]) -> dict[str, list[str]]:
    mapping = {
        "api_routes": ["route", "router", "api", "endpoint"],
        "services_domain": ["service", "domain"],
        "providers_adapters": ["provider", "adapter", "integration"],
        "models_schemas": ["model", "schema", "dto"],
        "frontend_components_pages": ["component", "components", "page", "pages"],
        "background_jobs": ["job", "worker", "scheduler", "cron"],
        "notifications_actions": ["notification", "action", "triage"],
        "dashboard_workspace": ["dashboard", "workspace", "widget"],
    }
    out: dict[str, set[str]] = {k: set() for k in mapping}
    for p in file_set:
        low = p.lower()
        for key, words in mapping.items():
            if any(w in low for w in words): out[key].add(p)
    for p, text in snippets.items():
        for key, words in mapping.items():
            if any(w in text for w in words): out[key].add(p)
    return {k: sorted(list(v))[:12] for k, v in out.items()}


def _compatibility(signals: dict[str, list[str]], arch: dict[str, list[str]]) -> list[dict[str, Any]]:
    def rec(module: str, status: str, evidence: list[str], notes: str, step: str) -> dict[str, Any]:
        return {"module": module, "status": status, "evidence": evidence[:8], "notes": notes, "suggested_migration_step": step}
    return [
        rec("provider_adapter", "partial" if arch["providers_adapters"] else "missing", arch["providers_adapters"], "Provider/adapter boundaries support AgentForge ingestion modules.", "Introduce explicit provider and adapter interfaces."),
        rec("pipeline", "partial" if arch["services_domain"] or arch["background_jobs"] else "missing", arch["services_domain"] + arch["background_jobs"], "Pipeline fit depends on clear service/job boundaries.", "Map existing processing steps into deterministic pipeline stages."),
        rec("scoring_explanation", "partial" if any("score" in e.lower() for e in arch["services_domain"] + arch["models_schemas"]) else "missing", arch["services_domain"] + arch["models_schemas"], "Scoring needs deterministic labels, drivers, and risks.", "Add explanation DTOs and tests around scoring decisions."),
        rec("notification_action", "partial" if arch["notifications_actions"] else "missing", arch["notifications_actions"], "Notification/action loops should remain preview-first.", "Model action states and append-only history."),
        rec("triage_ui", "partial" if arch["notifications_actions"] and arch["frontend_components_pages"] else "missing", arch["notifications_actions"] + arch["frontend_components_pages"], "Triage UI requires frontend surfaces for decisions.", "Add preview cards and bounded actions."),
        rec("agent_runtime", "partial" if signals["ai_agent"] else "missing", signals["ai_agent"], "Agent runtime compatibility requires safe tools and deterministic tests.", "Wrap tool calls with typed validation and scripted provider tests."),
        rec("dashboard_workspace", "partial" if arch["dashboard_workspace"] else "missing", arch["dashboard_workspace"], "Workspace fit is strongest with dashboard/widget concepts.", "Introduce persisted generic widgets only after core flow is stable."),
        rec("deterministic_test_harness", "compatible" if signals["testing"] else "missing", signals["testing"], "Detected tests can anchor migration safety.", "Add deterministic fixtures for every AgentForge capability."),
        rec("ci_local_validation", "partial" if signals["devops"] else "missing", signals["devops"], "Make/CI/env examples help reproduce local validation.", "Add a single local validation command and CI skeleton."),
        rec("observability_debug", "partial" if signals["observability"] else "missing", signals["observability"], "Observability support is advisory in current AgentForge scope.", "Keep health/logging/metrics explicit and local-friendly."),
    ]


def _archetypes(signals: dict[str, list[str]], arch: dict[str, list[str]], comp: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scores = []
    def add(name: str, points: int, evidence: list[str]) -> None:
        conf = "high" if points >= 4 else "medium" if points >= 2 else "low"
        scores.append({"archetype": name, "confidence": conf, "score": points, "evidence": evidence[:8]})
    add("ingestion_scoring_pipeline", int(bool(arch["providers_adapters"])) + int(bool(arch["services_domain"])) + int(any("score" in e.lower() for e in arch["models_schemas"] + arch["services_domain"]))*2, arch["providers_adapters"] + arch["services_domain"] + arch["models_schemas"])
    add("notification_triage_app", int(bool(arch["notifications_actions"]))*2 + int(bool(arch["frontend_components_pages"])), arch["notifications_actions"] + arch["frontend_components_pages"])
    add("agent_dashboard_app", int(bool(signals["ai_agent"]))*2 + int(bool(arch["dashboard_workspace"]))*2, signals["ai_agent"] + arch["dashboard_workspace"])
    add("hybrid_agent_pipeline", int(bool(signals["ai_agent"]))*2 + int(bool(arch["services_domain"])) + int(bool(arch["providers_adapters"])), signals["ai_agent"] + arch["services_domain"] + arch["providers_adapters"])
    scores = sorted(scores, key=lambda x: (-x["score"], x["archetype"]))
    return scores if scores and scores[0]["score"] > 0 else [{"archetype": "unknown/custom", "confidence": "low", "score": 0, "evidence": []}]


def _risks(signals: dict[str, list[str]], arch: dict[str, list[str]], file_set: set[str], cap_hit: bool, unreadable: list[str]) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    def add(kind: str, detail: str) -> None: risks.append({"risk": kind, "detail": detail})
    if not signals["testing"]: add("missing_tests", "No common test framework signals detected.")
    if not arch["api_routes"] and not arch["services_domain"]: add("unclear_app_boundaries", "No obvious API or service/domain layer detected.")
    if not any(Path(p).name.startswith(".env") and ("example" in p or "sample" in p) for p in file_set): add("no_env_example", "No .env example/sample file detected.")
    if not signals["frontend"]: add("no_frontend", "No frontend framework signal detected.")
    if any(Path(p).name.startswith(".env") and "example" not in p and "sample" not in p for p in file_set): add("secrets_risk_pattern", "Environment-like files are present; analyzer did not extract secret contents.")
    if cap_hit: add("scan_cap_hit", "The max file scan cap was reached; report may be incomplete.")
    if unreadable: add("unreadable_paths", f"Some paths could not be read: {', '.join(unreadable[:5])}")
    return risks


def _migration_plan(comp: list[dict[str, Any]], risks: list[dict[str, str]]) -> list[dict[str, str]]:
    phases = [{"phase": "Phase 1", "title": "Draft and review App Blueprint", "advisory": "true", "step": "Describe the current app shape and validate it with agentforge plan."}]
    if any(r["risk"] == "missing_tests" for r in risks) or _status(comp, "deterministic_test_harness") != "compatible":
        phases.append({"phase": "Phase 2", "title": "Add deterministic test harness", "advisory": "true", "step": "Create offline fixtures for core flows before migration."})
    for module, title in [("provider_adapter", "Align provider/adapter layer"), ("pipeline", "Map pipeline and scoring flow"), ("agent_runtime", "Add safe agent runtime"), ("dashboard_workspace", "Add workspace/dashboard"), ("notification_action", "Add notification/triage loop"), ("ci_local_validation", "Document local validation and CI")]:
        if _status(comp, module) in {"missing", "partial", "unknown"}:
            phases.append({"phase": f"Phase {len(phases)+1}", "title": title, "advisory": "true", "step": next(c["suggested_migration_step"] for c in comp if c["module"] == module)})
    return phases


def _status(comp: list[dict[str, Any]], module: str) -> str:
    return next(c["status"] for c in comp if c["module"] == module)


def _blueprint_seed(name: str, archetypes: list[dict[str, Any]], comp: list[dict[str, Any]], signals: dict[str, list[str]]) -> str:
    archetype = archetypes[0]["archetype"]
    active = [c["module"] for c in comp if c["status"] in {"compatible", "partial"}]
    return "\n".join([
        "# DRAFT ONLY - review before using as an App Blueprint",
        f"name: {name.lower().replace(' ', '-')}",
        f"display_name: {name}",
        f"app_archetype: {archetype}",
        "required_shell_modules:",
        *[f"  - {m}" for m in active[:6]],
        "analysis_notes:",
        f"  backend_signals: {len(signals['backend'])}",
        f"  frontend_signals: {len(signals['frontend'])}",
        f"  ai_agent_signals: {len(signals['ai_agent'])}",
    ])


def _is_monorepo(file_set: set[str]) -> bool:
    package_roots = {str(Path(p).parent) for p in file_set if Path(p).name in {"package.json", "pyproject.toml"}}
    return len(package_roots) > 1 or any(Path(p).name in {"pnpm-workspace.yaml", "turbo.json", "nx.json"} for p in file_set)


def result_to_jsonable(result: dict[str, Any]) -> dict[str, Any]:
    return result


def render_report(result: dict[str, Any], format: str = "text") -> str:
    if format == "json":
        return json.dumps(result_to_jsonable(result), indent=2)
    md = format == "md"
    h1 = "#" if md else ""
    h2 = "##" if md else ""
    lines = [f"{h1} AgentForge Repo Analyzer Report".strip(), "", f"Repository: {result['repo']['name']}", f"Path: {result['repo']['path']}", f"Git repo: {result['repo']['is_git_repo']}", f"Monorepo likely: {result['repo']['monorepo_likely']}", ""]
    lines += [f"{h2} Detected Stack".strip()]
    for group, items in result["detected_stack"].items():
        lines.append(f"- {group}: {', '.join(items) if items else 'none detected'}")
    lines += ["", f"{h2} Likely Archetype".strip()]
    for a in result["archetype_candidates"][:3]:
        lines.append(f"- {a['archetype']} ({a['confidence']}) evidence: {', '.join(a['evidence']) or 'none'}")
    lines += ["", f"{h2} Module Compatibility".strip(), "| Module | Status | Evidence | Suggested step |", "| --- | --- | --- | --- |"]
    for c in result["module_compatibility"]:
        lines.append(f"| {c['module']} | {c['status']} | {'; '.join(c['evidence']) or 'none'} | {c['suggested_migration_step']} |")
    lines += ["", f"{h2} Migration Plan".strip()]
    for p in result["migration_plan"]:
        lines.append(f"- {p['phase']}: {p['title']} — {p['step']} (advisory only)")
    lines += ["", f"{h2} Risks and Blockers".strip()]
    lines += [f"- {r['risk']}: {r['detail']}" for r in result["risks"]] or ["- none detected"]
    if result.get("blueprint_seed"):
        lines += ["", f"{h2} Suggested App Blueprint Seed".strip(), "```yaml" if md else "", result["blueprint_seed"], "```" if md else ""]
    lines += ["", f"{h2} Next Steps".strip(), "- Review this advisory report before editing the analyzed repository.", "- Run AgentForge generation only from a reviewed App Blueprint."]
    return "\n".join(lines).strip() + "\n"
