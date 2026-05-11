"""Planning-only Repo Extension Planner for AgentForge v0.8."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from agentforge.analyzer import AnalyzeOptions, analyze_repo

SUPPORTED_MODULES = [
    "provider_adapter",
    "pipeline",
    "scoring_explanation",
    "notification_action",
    "triage_ui",
    "agent_runtime",
    "dashboard_workspace",
    "deterministic_test_harness",
    "ci_local_validation",
]
UNSUPPORTED_MODULES = {
    "repo_patch_apply": "Runtime patch application is future scope; v0.8.2 only permits low-risk docs/blueprint/checklist apply.",
    "deploy_planner": "Deployment planning is future scope.",
    "real_provider_integrations": "Real external integrations are future scope.",
    "live_llm_provider": "Live LLM providers are not required for local deterministic planning.",
    "observability_debug": "Richer observability/debug generation is not implemented yet.",
}
MODULE_ORDER = SUPPORTED_MODULES + sorted(UNSUPPORTED_MODULES)


@dataclass(frozen=True)
class ExtensionPlanOptions:
    modules: tuple[str, ...] = ()
    max_files: int = 1000
    include_tests: bool = False
    from_report: bool = False


def load_analysis_report(path: str | Path) -> dict[str, Any]:
    report_path = Path(path).expanduser()
    if not report_path.exists():
        raise FileNotFoundError(f"analysis report not found: {report_path}")
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"analysis report is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or "repo" not in data or "module_compatibility" not in data:
        raise ValueError("analysis report does not look like agentforge analyze-repo JSON output")
    return data


def plan_extension(target: str | Path, options: ExtensionPlanOptions | None = None) -> dict[str, Any]:
    """Produce a planning-only extension plan from a repo path or analyzer JSON report."""
    opts = options or ExtensionPlanOptions()
    if opts.from_report:
        analysis = load_analysis_report(target)
    else:
        root = Path(target).expanduser()
        if not root.exists():
            raise FileNotFoundError(f"repository path not found: {root}")
        before = _snapshot(root)
        analysis = analyze_repo(root, AnalyzeOptions(max_files=opts.max_files, include_tests=opts.include_tests))
        after = _snapshot(root)
        if before != after:
            raise RuntimeError("safety check failed: analyzer changed target repository file listing")

    desired, unsupported = _select_modules(analysis, opts.modules)
    comp_by_module = {item["module"]: item for item in analysis.get("module_compatibility", [])}
    module_plans = [_module_plan(module, comp_by_module.get(module, {}), analysis) for module in desired]
    unsupported_items = _unsupported_items(unsupported)
    prerequisites = _prerequisites(module_plans, analysis)
    file_impact = _file_impact(module_plans, analysis)
    phases = _migration_phases(module_plans, prerequisites, analysis)
    risks = _risks(module_plans, analysis, unsupported_items)
    commands = _commands(analysis)
    recommended = _recommended_modules(analysis)

    return {
        "target_repo": {
            "name": analysis.get("repo", {}).get("name", "unknown"),
            "path": analysis.get("repo", {}).get("path", ""),
            "source": "analyzer_report" if opts.from_report else "repo_path",
            "planning_only": True,
            "files_modified": 0,
        },
        "source_analysis_summary": _analysis_summary(analysis),
        "blueprint_seed": analysis.get("blueprint_seed"),
        "selected_modules": desired,
        "recommended_modules": recommended,
        "module_plans": module_plans,
        "prerequisites": prerequisites,
        "file_impact": file_impact,
        "migration_phases": phases,
        "risks": risks,
        "unsupported_items": unsupported_items,
        "manual_steps": _manual_steps(),
        "generated_artifacts_preview": _generated_artifacts_preview(module_plans),
        "commands_to_run": commands,
        "confidence": _confidence(module_plans, analysis),
        "no_files_modified_statement": "No files were modified. This is an advisory extension plan only.",
    }


def _snapshot(root: Path) -> tuple[tuple[str, int], ...]:
    if root.is_file():
        return ((root.name, root.stat().st_size),)
    rows: list[tuple[str, int]] = []
    for path in sorted(root.rglob("*")):
        parts = set(path.relative_to(root).parts)
        if parts & {"node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".scribe", ".tmp"}:
            continue
        if path.is_file():
            try:
                rows.append((path.relative_to(root).as_posix(), path.stat().st_size))
            except OSError:
                continue
    return tuple(rows)


def _select_modules(analysis: dict[str, Any], requested: tuple[str, ...]) -> tuple[list[str], list[str]]:
    if requested:
        wanted = [m.strip() for item in requested for m in item.split(",") if m.strip()]
    else:
        wanted = _recommended_modules(analysis)
    selected = [m for m in MODULE_ORDER if m in wanted and m in SUPPORTED_MODULES]
    unsupported = [m for m in wanted if m not in SUPPORTED_MODULES]
    return selected, unsupported


def _recommended_modules(analysis: dict[str, Any]) -> list[str]:
    comp = {item["module"]: item.get("status", "unknown") for item in analysis.get("module_compatibility", [])}
    archetype = (analysis.get("archetype_candidates") or [{}])[0].get("archetype", "unknown/custom")
    recommended = ["deterministic_test_harness", "ci_local_validation"]
    if archetype in {"ingestion_scoring_pipeline", "hybrid_agent_pipeline"}:
        recommended += ["provider_adapter", "pipeline", "scoring_explanation"]
    if archetype in {"agent_dashboard_app", "hybrid_agent_pipeline"}:
        recommended += ["agent_runtime", "dashboard_workspace"]
    if archetype == "notification_triage_app":
        recommended += ["notification_action", "triage_ui"]
    for module, status in comp.items():
        if module in SUPPORTED_MODULES and status in {"compatible", "partial"}:
            recommended.append(module)
    return [m for m in SUPPORTED_MODULES if m in set(recommended)]


def _module_plan(module: str, compatibility: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    compat_status = compatibility.get("status", "unknown")
    evidence = compatibility.get("evidence", [])
    status = {
        "compatible": "ready",
        "partial": "partial",
        "missing": "blocked",
        "unknown": "blocked",
        "conflict": "blocked",
    }.get(compat_status, "blocked")
    if module in {"deterministic_test_harness", "ci_local_validation"} and compat_status in {"missing", "unknown"}:
        status = "partial"
    prereq = _module_prereqs(module, analysis, compat_status)
    risk = "low" if status == "ready" else "medium" if status == "partial" else "high"
    return {
        "module": module,
        "status": status,
        "why": compatibility.get("notes") or _default_why(module),
        "evidence": evidence,
        "prerequisites": prereq,
        "likely_files_to_add": _files_to_add(module),
        "likely_files_to_modify": _files_to_modify(module, analysis),
        "tests_to_add": _tests_to_add(module),
        "validation_commands": _validation_commands(module),
        "rollback_notes": "Keep changes in a review branch and revert the module patch group if validation fails.",
        "risk_level": risk,
    }


def _default_why(module: str) -> str:
    return f"{module} was selected for advisory AgentForge extension planning."


def _module_prereqs(module: str, analysis: dict[str, Any], compat_status: str) -> list[str]:
    prereqs: list[str] = []
    risks = {r.get("risk") for r in analysis.get("risks", [])}
    if "missing_tests" in risks and module != "deterministic_test_harness":
        prereqs.append("Add deterministic baseline tests before extending runtime behavior.")
    if "no_env_example" in risks and module in {"agent_runtime", "ci_local_validation", "pipeline"}:
        prereqs.append("Add or review .env.example before new runtime/config surfaces.")
    if compat_status in {"missing", "unknown"}:
        prereqs.append("Map existing repo boundaries manually; analyzer found little direct evidence.")
    if module in {"triage_ui", "dashboard_workspace", "agent_runtime"} and not analysis.get("detected_stack", {}).get("frontend"):
        prereqs.append("Choose a frontend integration strategy; analyzer did not detect a frontend.")
    return prereqs or ["Review analyzer evidence and confirm this module fits the repo."]


def _files_to_add(module: str) -> list[str]:
    mapping = {
        "provider_adapter": ["backend/app/providers/", "backend/app/adapters/", "tests/test_provider_adapter.py"],
        "pipeline": ["backend/app/services/pipeline.py", "backend/app/models/run_history.py", "tests/test_pipeline.py"],
        "scoring_explanation": ["backend/app/services/scoring.py", "backend/app/schemas/scoring.py", "tests/test_scoring.py"],
        "notification_action": ["backend/app/services/notifications.py", "backend/app/models/actions.py", "tests/test_notifications.py"],
        "triage_ui": ["frontend/src/components/TriagePanel.tsx", "frontend/src/api/triage.ts", "frontend/e2e/triage.spec.ts"],
        "agent_runtime": ["backend/app/agent/", "backend/app/api/agent.py", "frontend/src/components/AgentChatPanel.tsx", "tests/test_agent_runtime.py"],
        "dashboard_workspace": ["backend/app/workspace/", "frontend/src/components/WorkspacePanel.tsx", "tests/test_workspace.py"],
        "deterministic_test_harness": ["tests/fixtures/", "tests/test_baseline.py", "pytest.ini"],
        "ci_local_validation": ["Makefile", ".github/workflows/ci.yml", ".env.example"],
    }
    return mapping.get(module, [])


def _files_to_modify(module: str, analysis: dict[str, Any]) -> list[str]:
    package_files = analysis.get("repo", {}).get("package_files", [])
    common = [p for p in ["README.md", *package_files] if p]
    mapping = {
        "provider_adapter": ["backend app service imports", *common],
        "pipeline": ["backend app/router registration", *common],
        "scoring_explanation": ["backend API schemas/routes", *common],
        "notification_action": ["backend router registration", "frontend app shell", *common],
        "triage_ui": ["frontend app shell/routes", *common],
        "agent_runtime": ["backend main/router registration", "frontend app shell", *common],
        "dashboard_workspace": ["backend main/router registration", "frontend app shell", *common],
        "deterministic_test_harness": [*common],
        "ci_local_validation": [*common],
    }
    return list(dict.fromkeys(mapping.get(module, common)))


def _tests_to_add(module: str) -> list[str]:
    if module == "ci_local_validation":
        return ["CI/local validation smoke test"]
    if module == "deterministic_test_harness":
        return ["Baseline unit tests", "fixture determinism tests"]
    return [f"{module} unit tests", f"{module} integration tests", "no live LLM/API regression test"]


def _validation_commands(module: str) -> list[str]:
    cmds = ["python -m pytest"]
    if module in {"triage_ui", "agent_runtime", "dashboard_workspace"}:
        cmds += ["npm run build", "npm run lint"]
    return cmds


def _prerequisites(module_plans: list[dict[str, Any]], analysis: dict[str, Any]) -> list[str]:
    values = []
    for plan in module_plans:
        values.extend(plan["prerequisites"])
    if analysis.get("repo", {}).get("scan_cap_hit"):
        values.append("Re-run analyzer with a higher --max-files before implementation.")
    return sorted(set(values))


def _file_impact(module_plans: list[dict[str, Any]], analysis: dict[str, Any]) -> dict[str, Any]:
    add, modify, tests = [], [], []
    for plan in module_plans:
        add.extend(plan["likely_files_to_add"])
        modify.extend(plan["likely_files_to_modify"])
        tests.extend(plan["tests_to_add"])
    return {
        "advisory_only": True,
        "likely_files_to_add": sorted(set(add)),
        "likely_files_to_modify": sorted(set(modify)),
        "tests_to_add": sorted(set(tests)),
        "patch_groups_needed_later": [f"{plan['module']}_patch_group" for plan in module_plans],
        "files_modified_now": 0,
    }


def _migration_phases(module_plans: list[dict[str, Any]], prerequisites: list[str], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    selected = {p["module"] for p in module_plans}
    phases = [
        {"phase": "Phase 1", "title": "Baseline safety", "steps": ["Confirm the repo runs locally.", "Review analyzer risks.", "Add/verify tests and env examples before module work."], "modules": ["deterministic_test_harness", "ci_local_validation"]},
        {"phase": "Phase 2", "title": "Blueprint alignment", "steps": ["Create/review draft App Blueprint.", "Map current architecture to selected AgentForge modules."], "modules": []},
    ]
    ordered = [
        ("provider_adapter", "Provider/adapter extraction", ["Define provider interface.", "Normalize source records.", "Add fixture/mock provider tests."]),
        ("pipeline", "Pipeline and scoring flow", ["Add deterministic pipeline service.", "Persist run history.", "Validate idempotent local runs."]),
        ("scoring_explanation", "Scoring and explanation", ["Add scoring DTOs.", "Record drivers/risks.", "Test boundary cases."]),
        ("agent_runtime", "Agent runtime integration", ["Add scripted provider.", "Add tool registry.", "Add chat endpoint/UI with typed validation."]),
        ("dashboard_workspace", "Dashboard/workspace integration", ["Add widget persistence.", "Add generic renderers.", "Enforce tool/widget compatibility."]),
        ("notification_action", "Notification/action loop", ["Add preview-only notifications.", "Add action state/history.", "Keep external delivery disabled."]),
        ("triage_ui", "Triage UI", ["Add decision UI.", "Show preview cards and action history.", "Test user actions."]),
    ]
    for module, title, steps in ordered:
        if module in selected:
            phases.append({"phase": f"Phase {len(phases)+1}", "title": title, "steps": steps, "modules": [module]})
    phases.append({"phase": f"Phase {len(phases)+1}", "title": "Validation and docs", "steps": ["Run local tests/build/lint.", "Update README and run commands.", "Review patch groups before any future application."], "modules": sorted(selected)})
    return phases


def _risks(module_plans: list[dict[str, Any]], analysis: dict[str, Any], unsupported_items: list[dict[str, str]]) -> list[dict[str, str]]:
    risks = [{"risk": r.get("risk", "analysis_risk"), "detail": r.get("detail", "Analyzer reported a risk.")} for r in analysis.get("risks", [])]
    for plan in module_plans:
        if plan["risk_level"] == "high":
            risks.append({"risk": f"{plan['module']}_blocked", "detail": "Analyzer evidence is weak or missing; manual architecture review required."})
    for item in unsupported_items:
        risks.append({"risk": "unsupported_requested_module", "detail": f"{item['module']}: {item['reason']}"})
    return risks or [{"risk": "review_required", "detail": "Plan is advisory; review file impact before implementing."}]


def _unsupported_items(items: list[str]) -> list[dict[str, str]]:
    return [{"module": item, "reason": UNSUPPORTED_MODULES.get(item, "Module is not supported by v0.8 extension planning.")} for item in sorted(set(items))]


def _manual_steps() -> list[str]:
    return [
        "Review analyzer evidence and this extension plan with the repo owner.",
        "Create or update an App Blueprint outside the target repo unless intentionally adding one later.",
        "Implement one patch group at a time in a separate future change set.",
        "Run validation after each module group.",
        "Use agentforge prepare-extension for a safe bundle preview; only use --apply for explicitly approved low-risk docs/blueprint/checklist files.",
    ]


def _generated_artifacts_preview(module_plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"name": f"{plan['module']}_patch_plan", "type": "patch_plan_only", "applied": False, "files": plan["likely_files_to_add"] + plan["likely_files_to_modify"]} for plan in module_plans]


def _commands(analysis: dict[str, Any]) -> list[str]:
    path = analysis.get("repo", {}).get("path") or "<repo>"
    return [
        f"agentforge analyze-repo {path} --json --output analysis.json",
        "agentforge plan-extension analysis.json --from-report --format md --output extension-plan.md",
        "agentforge plan path/to/domain-pack.yaml",
        "agentforge generate path/to/domain-pack.yaml",
    ]


def _confidence(module_plans: list[dict[str, Any]], analysis: dict[str, Any]) -> str:
    if not module_plans:
        return "low"
    high_risk = sum(1 for p in module_plans if p["risk_level"] == "high")
    if high_risk:
        return "low"
    partial = sum(1 for p in module_plans if p["status"] == "partial")
    return "medium" if partial else "high"


def _analysis_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    arch = (analysis.get("archetype_candidates") or [{}])[0]
    return {
        "repo_name": analysis.get("repo", {}).get("name", "unknown"),
        "is_git_repo": analysis.get("repo", {}).get("is_git_repo", False),
        "monorepo_likely": analysis.get("repo", {}).get("monorepo_likely", False),
        "top_archetype": arch.get("archetype", "unknown/custom"),
        "archetype_confidence": arch.get("confidence", "low"),
        "detected_stack_counts": {k: len(v or []) for k, v in analysis.get("detected_stack", {}).items()},
    }


def result_to_jsonable(plan: dict[str, Any]) -> dict[str, Any]:
    return plan


def render_extension_plan(plan: dict[str, Any], format: str = "text") -> str:
    if format == "json":
        return json.dumps(result_to_jsonable(plan), indent=2) + "\n"
    md = format == "md"
    h1 = "#" if md else ""
    h2 = "##" if md else ""
    lines = [
        f"{h1} AgentForge Repo Extension Plan".strip(),
        "",
        plan["no_files_modified_statement"],
        "",
        f"Repository: {plan['target_repo']['name']}",
        f"Source: {plan['target_repo']['source']}",
        f"Confidence: {plan['confidence']}",
        "",
        f"{h2} Selected and Recommended Modules".strip(),
        f"Selected: {', '.join(plan['selected_modules']) or 'none'}",
        f"Recommended: {', '.join(plan['recommended_modules']) or 'none'}",
        "",
        f"{h2} Module Plan".strip(),
        "| Module | Status | Risk | Why |" if md else "Module | Status | Risk | Why",
        "| --- | --- | --- | --- |" if md else "--- | --- | --- | ---",
    ]
    for item in plan["module_plans"]:
        lines.append(f"| {item['module']} | {item['status']} | {item['risk_level']} | {item['why']} |")
    lines += ["", f"{h2} File Impact".strip(), "Likely files to add:"]
    lines += [f"- {p}" for p in plan["file_impact"]["likely_files_to_add"]] or ["- none"]
    lines += ["Likely files to modify:"]
    lines += [f"- {p}" for p in plan["file_impact"]["likely_files_to_modify"]] or ["- none"]
    lines += ["", f"{h2} Migration Phases".strip()]
    for phase in plan["migration_phases"]:
        lines.append(f"- {phase['phase']}: {phase['title']} - {'; '.join(phase['steps'])}")
    lines += ["", f"{h2} Risks and Blockers".strip()]
    lines += [f"- {r['risk']}: {r['detail']}" for r in plan["risks"]]
    if plan["unsupported_items"]:
        lines += ["", f"{h2} Unsupported Items".strip()]
        lines += [f"- {u['module']}: {u['reason']}" for u in plan["unsupported_items"]]
    lines += ["", f"{h2} Manual Steps".strip()]
    lines += [f"- {s}" for s in plan["manual_steps"]]
    lines += ["", f"{h2} Validation Commands".strip()]
    validation = sorted({cmd for mp in plan["module_plans"] for cmd in mp["validation_commands"]})
    lines += [f"- {cmd}" for cmd in validation] or ["- python -m pytest"]
    lines += ["", f"{h2} Next Steps".strip()]
    lines += [f"- {cmd}" for cmd in plan["commands_to_run"]]
    return "\n".join(lines).strip() + "\n"
