"""Planning-only Deployment Planner for AgentForge v0.9."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re

from agentforge.analyzer import AnalyzeOptions, analyze_repo
from agentforge.extension_planner import load_analysis_report

PLATFORMS = ["railway", "render", "fly", "aws-ecs", "docker-vps", "auto"]
TEXT_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".env", ".ini", ".cfg"}
IGNORED = {"node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".scribe", ".tmp", "coverage", "playwright-report", "test-results"}


@dataclass(frozen=True)
class DeploymentPlanOptions:
    from_report: bool = False
    platform: str = "auto"
    include_cost_notes: bool = False
    docs_bundle: bool = False
    output: str | Path | None = None
    max_files: int = 1000
    include_tests: bool = False


def plan_deployment(target: str | Path, options: DeploymentPlanOptions | None = None) -> dict[str, Any]:
    opts = options or DeploymentPlanOptions()
    if opts.platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {opts.platform}")
    if opts.from_report:
        analysis = load_analysis_report(target)
        root = None
        files = set(analysis.get("scanned_files", []))
        snippets: dict[str, str] = {}
    else:
        root = Path(target).expanduser()
        if not root.exists():
            raise FileNotFoundError(f"repository path not found: {root}")
        if not root.is_dir():
            raise ValueError(f"repository path is not a directory: {root}")
        before = _snapshot(root)
        analysis = analyze_repo(root, AnalyzeOptions(max_files=opts.max_files, include_tests=opts.include_tests))
        files, snippets = _scan(root, opts.max_files, opts.include_tests)
        after = _snapshot(root)
        if before != after:
            raise RuntimeError("safety check failed: deployment planner changed target repository file listing")

    detected = _detect_deployment(files, snippets, analysis)
    readiness_checks = _readiness_checks(detected, analysis)
    readiness_summary = _readiness_summary(readiness_checks)
    env_checklist = _env_checklist(detected, analysis)
    docker_checklist = _docker_checklist(detected)
    ci_checklist = _ci_checklist(detected, analysis)
    database_notes = _database_notes(detected, analysis)
    healthcheck_notes = _healthcheck_notes(detected)
    cost_risk_notes = _cost_risk_notes(detected, opts.include_cost_notes)
    recommendations = _platform_recommendations(detected, readiness_checks, opts.platform)
    phased = _phased_plan(readiness_summary, detected)
    manual_commands = _manual_commands(detected)
    return {
        "target_repo": {
            "name": analysis.get("repo", {}).get("name", "unknown"),
            "path": analysis.get("repo", {}).get("path", ""),
            "source": "analyzer_report" if opts.from_report else "repo_path",
            "planning_only": True,
            "files_modified": 0,
        },
        "detected_stack": detected,
        "readiness_summary": readiness_summary,
        "readiness_checks": readiness_checks,
        "platform_recommendations": recommendations,
        "env_checklist": env_checklist,
        "docker_checklist": docker_checklist,
        "ci_checklist": ci_checklist,
        "database_notes": database_notes,
        "healthcheck_notes": healthcheck_notes,
        "cost_risk_notes": cost_risk_notes,
        "phased_plan": phased,
        "manual_commands": manual_commands,
        "not_executed_warning": "No deployment was performed. No cloud resources were provisioned. No secrets were read or stored. No target repo scripts, package installs, cloud CLIs, commits, pushes, or destructive commands were run.",
    }


def write_deployment_docs_bundle(plan: dict[str, Any], output: str | Path) -> list[str]:
    out = Path(output).expanduser()
    files = {
        "README.md": _bundle_readme(plan),
        "deployment-plan.md": render_deployment_plan(plan, "md"),
        "env-checklist.md": _checklist_md("Environment Checklist", plan["env_checklist"]),
        "docker-readiness.md": _checklist_md("Docker Readiness", plan["docker_checklist"]),
        "ci-readiness.md": _checklist_md("CI Readiness", plan["ci_checklist"]),
        "platform-recommendations.md": _platform_md(plan),
        "risk-notes.md": "# Risk and Cost Notes\n\n" + "\n".join(f"- {n}" for n in plan["cost_risk_notes"]) + "\n",
    }
    written = []
    for rel, content in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(rel)
    return written


def render_deployment_plan(plan: dict[str, Any], format: str = "text") -> str:
    if format == "json":
        return json.dumps(plan, indent=2) + "\n"
    md = format == "md"
    h1 = "#" if md else ""
    h2 = "##" if md else ""
    lines = [
        f"{h1} AgentForge Deployment Readiness Plan".strip(),
        "",
        plan["not_executed_warning"],
        "",
        f"Repository: {plan['target_repo']['name']}",
        f"Path: {plan['target_repo'].get('path', '')}",
        f"Overall readiness: {plan['readiness_summary']['status']} ({plan['readiness_summary']['score']}/100)",
        "",
        f"{h2} Detected Stack".strip(),
    ]
    ds = plan["detected_stack"]
    for key in ["backend", "frontend", "database", "docker", "ci_cd", "environment", "observability"]:
        lines.append(f"- {key}: {json.dumps(ds.get(key, {}), sort_keys=True)}")
    lines += ["", f"{h2} Readiness Checks".strip()]
    lines += ["| Area | Status | Evidence | Missing |" if md else "Area | Status | Evidence | Missing", "| --- | --- | --- | --- |" if md else "--- | --- | --- | ---"]
    for c in plan["readiness_checks"]:
        lines.append(f"| {c['area']} | {c['status']} | {'; '.join(c['evidence']) or 'none'} | {'; '.join(c['missing']) or 'none'} |")
    lines += ["", f"{h2} Platform Recommendations".strip()]
    for r in plan["platform_recommendations"]:
        lines += [f"- **{r['platform']}** ({r['fit']}): {r['why']}", f"  - requirements: {', '.join(r['requirements']) or 'none'}", f"  - missing: {', '.join(r['missing_pieces']) or 'none'}", f"  - risk/cost: {r['cost_risk_notes']}"]
    for title, key in [("Environment Checklist", "env_checklist"), ("Docker Checklist", "docker_checklist"), ("CI Checklist", "ci_checklist")]:
        lines += ["", f"{h2} {title}".strip()]
        lines += [f"- [{ 'x' if i['status'] == 'present' else ' ' }] {i['item']}: {i['detail']}" for i in plan[key]]
    lines += ["", f"{h2} Database Notes".strip()]
    lines += [f"- {n}" for n in plan["database_notes"]]
    lines += ["", f"{h2} Healthcheck Notes".strip()]
    lines += [f"- {n}" for n in plan["healthcheck_notes"]]
    lines += ["", f"{h2} Cost / Risk Notes".strip()]
    lines += [f"- {n}" for n in plan["cost_risk_notes"]]
    lines += ["", f"{h2} Phased Deployment Plan".strip()]
    for p in plan["phased_plan"]:
        lines.append(f"- {p['phase']}: {p['title']} — {'; '.join(p['steps'])}")
    lines += ["", f"{h2} Manual Next Steps".strip()]
    lines += [f"- {c}" for c in plan["manual_commands"]]
    return "\n".join(lines).strip() + "\n"


def _scan(root: Path, max_files: int, include_tests: bool) -> tuple[set[str], dict[str, str]]:
    files: set[str] = set(); snippets: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if len(files) >= max_files: break
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        parts = set(Path(rel).parts)
        if parts & IGNORED: continue
        if not include_tests and parts & {"tests", "test", "e2e", "spec", "specs", "__tests__"}: continue
        if path.is_file():
            files.add(rel)
            if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile", "Makefile"} or path.name.startswith(".env"):
                try: snippets[rel] = path.read_text(encoding="utf-8", errors="ignore")[:20000].lower()
                except OSError: pass
    return files, snippets


def _snapshot(root: Path) -> tuple[tuple[str, int], ...]:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (set(p.relative_to(root).parts) & IGNORED):
            rows.append((p.relative_to(root).as_posix(), p.stat().st_size))
    return tuple(rows)


def _has(files: set[str], name: str) -> bool:
    return any(Path(p).name == name for p in files)


def _detect_deployment(files: set[str], snippets: dict[str, str], analysis: dict[str, Any]) -> dict[str, Any]:
    all_text = "\n".join(snippets.values()).lower()
    signals = analysis.get("detected_stack", {})
    backend = _backend(files, snippets, signals, all_text)
    frontend = _frontend(files, snippets, signals, all_text)
    db = _database(files, snippets, signals, all_text)
    docker = _docker(files, snippets)
    ci = _ci(files, snippets, signals)
    env = _environment(files, snippets, signals)
    obs = _observability(files, snippets, signals, all_text)
    return {"backend": backend, "frontend": frontend, "database": db, "docker": docker, "ci_cd": ci, "environment": env, "observability": obs}


def _backend(files, snippets, signals, text):
    framework = "unknown"
    for fw in ["fastapi", "flask", "django", "express"]:
        if fw in text or any(fw in e.lower() for e in signals.get("backend", [])):
            framework = fw if fw != "express" else "express/node"; break
    if framework == "unknown" and any("pages/api" in p or "app/api" in p for p in files): framework = "next_api"
    deps = sorted(p for p in files if Path(p).name in {"requirements.txt", "requirements-dev.txt", "pyproject.toml", "package.json"})
    ports = sorted(set(re.findall(r"(?:port|:)(\d{4,5})", text)))[:5]
    start = []
    if "uvicorn" in text: start.append("uvicorn ...")
    if "gunicorn" in text: start.append("gunicorn ...")
    if "npm run start" in text or '"start"' in text: start.append("npm run start")
    return {"framework": framework, "dependency_files": deps, "ports": ports, "start_command_hints": sorted(set(start))}


def _frontend(files, snippets, signals, text):
    framework = "unknown"
    if "vite" in text or any("vite" in e.lower() for e in signals.get("frontend", [])): framework = "vite/react" if "react" in text else "vite"
    elif "next.config" in text or any(Path(p).name.startswith("next.config") for p in files): framework = "nextjs"
    elif "react" in text or any(p.endswith((".tsx", ".jsx")) for p in files): framework = "react"
    build = []
    if '"build"' in text: build.append("npm run build")
    output = "dist" if any("vite" in p for p in files) or "vite" in text else ".next" if framework == "nextjs" else "unknown"
    prefixes = []
    if "vite_" in text: prefixes.append("VITE_")
    if "next_public_" in text: prefixes.append("NEXT_PUBLIC_")
    return {"framework": framework, "build_commands": build, "output_directory": output, "public_env_prefixes": prefixes}


def _database(files, snippets, signals, text):
    types = []
    for label, aliases in {"postgresql": ["postgres", "postgresql"], "sqlite": ["sqlite", "sqlite:///"], "mongodb": ["mongodb", "mongo"]}.items():
        if any(a in text for a in aliases) or any(a in e.lower() for e in signals.get("data", []) for a in aliases): types.append(label)
    migrations = []
    if "alembic" in text or any("alembic" in p.lower() for p in files): migrations.append("alembic")
    if "prisma" in text or any("prisma" in p.lower() for p in files): migrations.append("prisma")
    return {"types": sorted(set(types)) or ["unknown"], "migrations": sorted(set(migrations)), "local_only_risks": ["SQLite is usually local-only; plan managed PostgreSQL or persistent volume before production."] if "sqlite" in types else []}


def _docker(files, snippets):
    dockerfiles = sorted(p for p in files if Path(p).name == "Dockerfile")
    compose = sorted(p for p in files if Path(p).name in {"docker-compose.yml", "docker-compose.yaml"})
    text = "\n".join(snippets.get(p, "") for p in dockerfiles + compose)
    ports = sorted(set(re.findall(r"(?:expose|ports:|:)(\d{4,5})", text)))[:8]
    health = "healthcheck" in text or "/health" in text
    return {"dockerfiles": dockerfiles, "compose_files": compose, "multi_service": bool(compose and ("services:" in text)), "exposed_ports": ports, "healthchecks": health, "missing_dockerfile": not dockerfiles}


def _ci(files, snippets, signals):
    workflows = sorted(p for p in files if p.startswith(".github/workflows/"))
    makefile = _has(files, "Makefile")
    text = "\n".join(snippets.values())
    tests = sorted({cmd for cmd in ["python -m pytest", "pytest", "npm test", "npm run build", "npm run lint"] if cmd in text})
    return {"github_actions": workflows, "makefile": makefile, "test_commands": tests, "validation_path_present": bool(workflows or makefile or tests or signals.get("testing"))}


def _environment(files, snippets, signals):
    env_examples = sorted(p for p in files if Path(p).name.startswith(".env") and ("example" in p or "sample" in p))
    env_like = sorted(p for p in files if Path(p).name.startswith(".env") and p not in env_examples)
    candidates = set()
    for text in snippets.values():
        candidates.update(re.findall(r"(?:os\.getenv|os\.environ|getenv|process\.env)\(?[\['\"]([A-Z][A-Z0-9_]{2,})", text, flags=re.I))
        candidates.update(re.findall(r"\b([A-Z][A-Z0-9_]{2,})=", text))
    public = sorted(v for v in candidates if v.startswith(("VITE_", "NEXT_PUBLIC_")))
    secretish = sorted(v for v in candidates if any(w in v for w in ["KEY", "SECRET", "TOKEN", "PASSWORD"]))
    return {"env_examples": env_examples, "env_like_files_present": bool(env_like), "required_env_candidates": sorted(candidates)[:30], "public_frontend_envs": public, "secret_like_names": secretish, "missing_env_example": not env_examples}


def _observability(files, snippets, signals, text):
    health_paths = sorted(set(re.findall(r"['\"](/(?:health|ready|live|metrics)[^'\"]*)['\"]", text)))[:10]
    return {"health_endpoints": health_paths, "metrics": "metrics" in text or bool(signals.get("observability")), "logging": "logging" in text or "logger" in text, "readiness_liveness": bool(health_paths)}


def _status(ok: bool, partial: bool = False) -> str:
    return "ready" if ok else "nearly_ready" if partial else "needs_work"


def _readiness_checks(d, analysis):
    checks = []
    def add(area, status, evidence, missing): checks.append({"area": area, "status": status, "evidence": evidence, "missing": missing})
    add("local_validation", _status(d["ci_cd"]["validation_path_present"]), d["ci_cd"]["test_commands"] + (["Makefile"] if d["ci_cd"]["makefile"] else []), [] if d["ci_cd"]["validation_path_present"] else ["Document one local validation command"])
    add("build_commands", _status(bool(d["backend"]["dependency_files"] and (d["frontend"]["build_commands"] or d["frontend"]["framework"] == "unknown")), bool(d["backend"]["dependency_files"])), d["backend"]["dependency_files"] + d["frontend"]["build_commands"], ["Confirm production backend start command", "Confirm frontend build command"] if not d["frontend"]["build_commands"] and d["frontend"]["framework"] != "unknown" else [])
    add("docker_readiness", _status(not d["docker"]["missing_dockerfile"], bool(d["docker"]["compose_files"])), d["docker"]["dockerfiles"] + d["docker"]["compose_files"], ["Add/review Dockerfile"] if d["docker"]["missing_dockerfile"] else [])
    add("env_examples", _status(not d["environment"]["missing_env_example"]), d["environment"]["env_examples"], ["Add .env.example with placeholder values only"] if d["environment"]["missing_env_example"] else [])
    add("database_migrations", _status(bool(d["database"]["migrations"]), "unknown" not in d["database"]["types"]), d["database"]["types"] + d["database"]["migrations"], ["Document migration or persistence strategy"] if not d["database"]["migrations"] else [])
    add("health_checks", _status(bool(d["observability"]["health_endpoints"]), d["observability"]["metrics"] or d["observability"]["logging"]), d["observability"]["health_endpoints"], ["Add/confirm /health or readiness endpoint"] if not d["observability"]["health_endpoints"] else [])
    add("ci", _status(bool(d["ci_cd"]["github_actions"]), d["ci_cd"]["validation_path_present"]), d["ci_cd"]["github_actions"], ["Add CI workflow for tests/build"] if not d["ci_cd"]["github_actions"] else [])
    add("secrets_handling", _status(not d["environment"]["env_like_files_present"], bool(d["environment"]["env_examples"])), d["environment"]["secret_like_names"], ["Do not commit real .env files; use platform secret store"] if d["environment"]["env_like_files_present"] else [])
    add("production_start_commands", _status(bool(d["backend"]["start_command_hints"]), bool(d["backend"]["dependency_files"])), d["backend"]["start_command_hints"], ["Document production start command"] if not d["backend"]["start_command_hints"] else [])
    return checks


def _readiness_summary(checks):
    values = {"ready": 100, "nearly_ready": 70, "needs_work": 35, "blocked": 0, "unknown": 20}
    score = round(sum(values.get(c["status"], 20) for c in checks) / max(len(checks), 1))
    status = "ready" if score >= 85 else "nearly_ready" if score >= 65 else "needs_work" if score >= 35 else "blocked"
    return {"status": status, "score": score, "ready_count": sum(1 for c in checks if c["status"] == "ready"), "total_checks": len(checks)}


def _env_checklist(d, analysis):
    e = d["environment"]
    return [
        {"item": ".env.example present", "status": "present" if e["env_examples"] else "missing", "detail": ", ".join(e["env_examples"]) or "Add placeholders only; do not store real secrets."},
        {"item": "Required env candidates reviewed", "status": "present" if e["required_env_candidates"] else "missing", "detail": ", ".join(e["required_env_candidates"]) or "No env vars safely detected."},
        {"item": "Public frontend env prefixes", "status": "present" if e["public_frontend_envs"] or not d["frontend"]["public_env_prefixes"] else "missing", "detail": ", ".join(d["frontend"]["public_env_prefixes"] or e["public_frontend_envs"]) or "None detected."},
        {"item": "Secret storage plan", "status": "missing", "detail": "Use platform secret store manually; AgentForge does not read/store secrets."},
    ]


def _docker_checklist(d):
    x = d["docker"]
    return [
        {"item": "Dockerfile present", "status": "present" if x["dockerfiles"] else "missing", "detail": ", ".join(x["dockerfiles"]) or "Add/review Dockerfile."},
        {"item": "Compose file present", "status": "present" if x["compose_files"] else "missing", "detail": ", ".join(x["compose_files"]) or "Optional for multi-service local validation."},
        {"item": "Ports documented", "status": "present" if x["exposed_ports"] else "missing", "detail": ", ".join(x["exposed_ports"]) or "Document app ports."},
        {"item": "Container healthcheck", "status": "present" if x["healthchecks"] else "missing", "detail": "Add HEALTHCHECK or platform health path if needed."},
    ]


def _ci_checklist(d, analysis):
    c = d["ci_cd"]
    return [
        {"item": "GitHub Actions", "status": "present" if c["github_actions"] else "missing", "detail": ", ".join(c["github_actions"]) or "Add workflow if deploying from git."},
        {"item": "Makefile/local validation", "status": "present" if c["makefile"] else "missing", "detail": "Makefile present" if c["makefile"] else "Document a single validation command."},
        {"item": "Test/build commands", "status": "present" if c["test_commands"] else "missing", "detail": ", ".join(c["test_commands"]) or "No commands detected."},
    ]


def _database_notes(d, analysis):
    notes = [f"Detected database signals: {', '.join(d['database']['types'])}."]
    notes += d["database"]["local_only_risks"]
    if not d["database"]["migrations"]: notes.append("No migration tool detected; document schema migration process before production.")
    else: notes.append(f"Migration signals: {', '.join(d['database']['migrations'])}.")
    return notes


def _healthcheck_notes(d):
    return [f"Health endpoints: {', '.join(d['observability']['health_endpoints']) or 'none detected'}.", "Deployment platforms usually need a health/readiness path; add one manually if absent."]


def _cost_risk_notes(d, include_cost):
    notes = ["Recommendations are advisory; verify free tier/paid resource behavior manually before creating resources.", "AgentForge did not run cloud CLIs or create infrastructure.", "Do not paste real secrets into reports; use platform secret stores manually."]
    if include_cost: notes.append("Managed databases, always-on containers, outbound bandwidth, and logs may incur cost depending on provider.")
    if d["database"]["local_only_risks"]: notes.extend(d["database"]["local_only_risks"])
    return notes


def _platform_recommendations(d, checks, requested):
    candidates = ["railway", "render", "fly", "aws-ecs", "docker-vps"] if requested == "auto" else [requested]
    out = []
    docker_ready = not d["docker"]["missing_dockerfile"]
    has_frontend = d["frontend"]["framework"] != "unknown"
    for p in candidates:
        req = ["env vars configured manually", "production start command"]
        missing = []
        fit = "medium"; why = "General web app deployment option."
        if p in {"railway", "render"}:
            why = "Good fit for simple web services and managed PostgreSQL when env/start commands are documented."
            if not d["environment"]["env_examples"]: missing.append(".env.example")
            if not d["backend"]["start_command_hints"]: missing.append("start command")
            fit = "high" if not missing else "medium"
        elif p == "fly":
            why = "Good fit for Dockerized apps that need container-level control."
            req.append("Dockerfile")
            if not docker_ready: missing.append("Dockerfile")
            fit = "high" if docker_ready else "low"
        elif p == "aws-ecs":
            why = "Flexible production container platform, but operational complexity and cost risk are higher."
            req += ["Dockerfile", "container registry", "VPC/IAM review"]
            if not docker_ready: missing.append("Dockerfile")
            fit = "medium" if docker_ready else "low"
        elif p == "docker-vps":
            why = "Manual Docker VPS path fits teams comfortable managing servers, TLS, backups, and updates."
            req.append("Dockerfile or compose file")
            if not (docker_ready or d["docker"]["compose_files"]): missing.append("Dockerfile/docker-compose")
            fit = "medium" if not missing else "low"
        if has_frontend and d["frontend"]["framework"] in {"vite", "vite/react", "react"} and p in {"railway", "render"}:
            req.append("decide single-service vs static frontend + backend API split")
        out.append({"platform": p, "fit": fit, "why": why, "requirements": req, "missing_pieces": missing, "cost_risk_notes": "Manual provider review required; commands that create resources are intentionally omitted."})
    return out


def _phased_plan(summary, d):
    return [
        {"phase": "Phase 1", "title": "Local readiness", "steps": ["Run existing tests/build locally yourself.", "Confirm production start command.", "Do not add real secrets to files."]},
        {"phase": "Phase 2", "title": "Configuration", "steps": ["Create .env.example placeholders.", "Document required env vars and public frontend env prefixes.", "Choose database persistence/migration path."]},
        {"phase": "Phase 3", "title": "Container/CI", "steps": ["Review Dockerfile/compose or add them manually.", "Add health/readiness path if absent.", "Ensure CI runs tests/build."]},
        {"phase": "Phase 4", "title": "Manual platform setup", "steps": ["Choose a recommended platform.", "Manually create resources after cost review.", "Configure secrets in the platform secret store."]},
        {"phase": "Phase 5", "title": "Post-deploy validation", "steps": ["Manually check health endpoint.", "Review logs and rollback plan.", "Keep deployment changes in version control under user control."]},
    ]


def _manual_commands(d):
    cmds = ["Review this report; no deployment commands were run by AgentForge."]
    if d["ci_cd"]["makefile"]: cmds.append("make validate  # manual local validation, not run by plan-deployment")
    elif d["ci_cd"]["test_commands"]: cmds += [f"{c}  # manual validation" for c in d["ci_cd"]["test_commands"][:3]]
    else: cmds.append("Document and run your app's test/build commands manually before deployment.")
    cmds.append("Configure secrets manually in your chosen platform; do not commit real .env files.")
    return cmds


def _bundle_readme(plan):
    return "# AgentForge Deployment Docs Bundle\n\n" + plan["not_executed_warning"] + "\n\nStart with `deployment-plan.md`, then review env, Docker, CI, platform, and risk notes.\n"


def _checklist_md(title, items):
    return f"# {title}\n\n" + "\n".join(f"- [{ 'x' if i['status'] == 'present' else ' ' }] {i['item']}: {i['detail']}" for i in items) + "\n"


def _platform_md(plan):
    return "# Platform Recommendations\n\n" + "\n".join(f"- **{r['platform']}** ({r['fit']}): {r['why']} Missing: {', '.join(r['missing_pieces']) or 'none'}." for r in plan["platform_recommendations"]) + "\n"
