"""Safe patch bundle and approved low-risk apply for AgentForge v0.8.1/v0.8.2."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import subprocess

from agentforge.extension_planner import ExtensionPlanOptions, plan_extension, render_extension_plan


@dataclass(frozen=True)
class PrepareExtensionOptions:
    modules: tuple[str, ...] = ()
    max_files: int = 1000
    include_tests: bool = False
    from_report: bool = False
    output: str | Path | None = None
    format: str = "text"
    dry_run: bool = False
    apply: bool = False
    yes: bool = False
    allow_dirty: bool = False
    overwrite: bool = False


def prepare_extension(target: str | Path, options: PrepareExtensionOptions | None = None) -> dict[str, Any]:
    """Create a safe bundle preview, or explicitly apply low-risk docs/blueprint files."""
    opts = options or PrepareExtensionOptions()
    plan = plan_extension(
        target,
        ExtensionPlanOptions(
            modules=opts.modules,
            max_files=opts.max_files,
            include_tests=opts.include_tests,
            from_report=opts.from_report,
        ),
    )
    target_repo = _target_repo_path(plan)
    output_path = Path(opts.output).expanduser() if opts.output else Path("agentforge-output") / f"{plan['target_repo']['name']}-extension"
    bundle_files = _bundle_files(plan)
    apply_ops = _apply_operations(plan)
    mode = "apply" if opts.apply else "dry-run" if opts.dry_run else "bundle"
    result: dict[str, Any] = {
        "mode": mode,
        "target_repo": str(target_repo) if target_repo else plan["target_repo"].get("path", ""),
        "output_path": str(output_path),
        "selected_modules": plan["selected_modules"],
        "planned_operations": _ops_for_result(bundle_files if not opts.apply else apply_ops),
        "applied_operations": [],
        "skipped_operations": [],
        "refused_operations": [],
        "safety_checks": [],
        "warnings": [],
        "no_target_repo_modification": not opts.apply,
        "plan": plan,
    }

    if opts.dry_run:
        result["safety_checks"].append({"check": "dry_run", "status": "passed", "detail": "No files were written."})
        return result

    if not opts.apply:
        _write_files(output_path, bundle_files, overwrite=True)
        result["applied_operations"] = _ops_for_result(bundle_files, base=output_path)
        result["safety_checks"].append({"check": "bundle_only", "status": "passed", "detail": "Only the explicit output directory was written."})
        return result

    if not opts.yes:
        result["refused_operations"].append({"path": str(target_repo), "reason": "apply requires explicit confirmation (--yes in non-interactive CLI mode)"})
        result["safety_checks"].append({"check": "approval", "status": "failed", "detail": "Missing --yes."})
        return result
    if not target_repo or not target_repo.exists() or not target_repo.is_dir():
        result["refused_operations"].append({"path": str(target_repo) if target_repo else "", "reason": "target repository path is unavailable"})
        result["safety_checks"].append({"check": "target_repo", "status": "failed", "detail": "Cannot apply without a local target repo."})
        return result

    dirty = _dirty_git_files(target_repo)
    if dirty and not opts.allow_dirty:
        result["refused_operations"] += [{"path": p, "reason": "dirty git working tree"} for p in dirty]
        result["safety_checks"].append({"check": "dirty_git", "status": "failed", "detail": "Refusing apply; pass --allow-dirty to override.", "files": dirty})
        return result
    result["safety_checks"].append({"check": "dirty_git", "status": "passed", "detail": "Clean or explicitly allowed.", "files": dirty})

    conflicts = [op for op in apply_ops if (target_repo / op["path"]).exists()]
    if conflicts and not opts.overwrite:
        result["refused_operations"] += [{"path": op["path"], "reason": "file exists; pass --overwrite to replace"} for op in conflicts]
        result["safety_checks"].append({"check": "overwrite", "status": "failed", "detail": "Refusing to overwrite existing files."})
        return result
    result["safety_checks"].append({"check": "overwrite", "status": "passed", "detail": "No conflicts or overwrite explicitly allowed."})

    files = {op["path"]: op["content"] for op in apply_ops if op.get("approved_low_risk")}
    _write_files(target_repo, files, overwrite=opts.overwrite)
    manifest = {
        "mode": "apply",
        "target_repo": str(target_repo),
        "selected_modules": plan["selected_modules"],
        "applied_files": sorted(files),
        "skipped_or_not_allowed": _not_allowed_notes(plan),
        "safety": _safety_notes(apply=True),
    }
    log_path = target_repo / "AGENTFORGE_APPLICATION_MANIFEST.json"
    if log_path.exists() and not opts.overwrite:
        result["skipped_operations"].append({"path": log_path.name, "reason": "application manifest already exists"})
    else:
        log_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        files[log_path.name] = json.dumps(manifest, indent=2) + "\n"
    result["applied_operations"] = [{"path": p, "operation": "write", "risk": "low"} for p in sorted(files)]
    result["skipped_operations"] += [{"path": n, "reason": "not allowed in v0.8.2 apply mode"} for n in _not_allowed_notes(plan)]
    result["no_target_repo_modification"] = False
    return result


def render_prepare_result(result: dict[str, Any], format: str = "text") -> str:
    if format == "json":
        slim = {k: v for k, v in result.items() if k != "plan"}
        return json.dumps(slim, indent=2) + "\n"
    md = format == "md"
    h1 = "#" if md else ""
    h2 = "##" if md else ""
    lines = [f"{h1} AgentForge Prepare Extension Result".strip(), "", f"Mode: {result['mode']}", f"Target repo: {result['target_repo']}", f"Output path: {result['output_path']}", f"Selected modules: {', '.join(result['selected_modules']) or 'none'}", f"No target repo modification: {result['no_target_repo_modification']}", "", f"{h2} Planned Writes".strip()]
    lines += [f"- {op['path']} ({op.get('risk', 'low')})" for op in result["planned_operations"]] or ["- none"]
    lines += ["", f"{h2} Applied".strip()]
    lines += [f"- {op['path']}" for op in result["applied_operations"]] or ["- none"]
    lines += ["", f"{h2} Refused".strip()]
    lines += [f"- {op['path']}: {op['reason']}" for op in result["refused_operations"]] or ["- none"]
    lines += ["", f"{h2} Safety Checks".strip()]
    lines += [f"- {c['check']}: {c['status']} - {c['detail']}" for c in result["safety_checks"]] or ["- none"]
    return "\n".join(lines).strip() + "\n"


def _target_repo_path(plan: dict[str, Any]) -> Path | None:
    raw = plan.get("target_repo", {}).get("path")
    return Path(raw).expanduser() if raw else None


def _bundle_files(plan: dict[str, Any]) -> dict[str, str]:
    manifest = {
        "bundle_version": "v0.8.1",
        "target_repo": plan["target_repo"],
        "selected_modules": plan["selected_modules"],
        "planned_operations": _ops_for_result(_apply_files(plan)),
        "safety_notes": _safety_notes(apply=False),
        "no_target_repo_files_modified": True,
    }
    files = {
        "README.md": _bundle_readme(plan),
        "manifest.json": json.dumps(manifest, indent=2) + "\n",
        "extension-plan.md": render_extension_plan(plan, "md"),
        "file-impact.md": _file_impact_md(plan),
        "migration-phases.md": _migration_md(plan),
        "validation-checklist.md": _validation_md(plan),
        "patch-preview.md": _patch_preview_md(plan),
        "proposed-files/AGENTFORGE_MIGRATION.md": _migration_doc(plan),
        "proposed-files/AGENTFORGE_EXTENSION_PLAN.md": render_extension_plan(plan, "md"),
        "proposed-files/AGENTFORGE_VALIDATION_CHECKLIST.md": _validation_doc(plan),
        "proposed-files/AGENTFORGE_MODULE_TODOS.md": _module_todos(plan),
        "proposed-files/AGENTFORGE_ENV_EXAMPLE_SUGGESTIONS.md": _env_suggestions(plan),
    }
    if plan.get("blueprint_seed"):
        files[f"proposed-files/domain-packs/{plan['target_repo']['name']}/domain-pack.yaml"] = plan["blueprint_seed"].rstrip() + "\n"
    return files


def _apply_operations(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"path": p, "content": c, "operation": "write", "risk": "low", "approved_low_risk": True} for p, c in _apply_files(plan).items()]


def _apply_files(plan: dict[str, Any]) -> dict[str, str]:
    files = {
        "AGENTFORGE_MIGRATION.md": _migration_doc(plan),
        "AGENTFORGE_EXTENSION_PLAN.md": render_extension_plan(plan, "md"),
        "AGENTFORGE_VALIDATION_CHECKLIST.md": _validation_doc(plan),
        "AGENTFORGE_MODULE_TODOS.md": _module_todos(plan),
        "AGENTFORGE_ENV_EXAMPLE_SUGGESTIONS.md": _env_suggestions(plan),
    }
    if plan.get("blueprint_seed"):
        files[f"domain-packs/{plan['target_repo']['name']}/domain-pack.yaml"] = plan["blueprint_seed"].rstrip() + "\n"
    return files


def _write_files(base: Path, files: dict[str, str], overwrite: bool) -> None:
    for rel, content in files.items():
        path = base / rel
        if path.exists() and not overwrite:
            raise FileExistsError(f"refusing to overwrite existing file: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _ops_for_result(files: dict[str, str] | list[dict[str, Any]], base: Path | None = None) -> list[dict[str, Any]]:
    if isinstance(files, dict):
        return [{"path": str((base / p) if base else p), "operation": "write", "risk": "low"} for p in sorted(files)]
    return [{"path": op["path"], "operation": op.get("operation", "write"), "risk": op.get("risk", "low")} for op in files]


def _dirty_git_files(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    proc = subprocess.run(["git", "-C", str(root), "status", "--short"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return ["<git status failed>"]
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _bundle_readme(plan: dict[str, Any]) -> str:
    return f"""# AgentForge Safe Patch Bundle

Target repo analyzed: `{plan['target_repo'].get('path') or plan['target_repo']['name']}`
Selected modules: {', '.join(plan['selected_modules']) or 'none'}

This v0.8.1 bundle is a safe preview. **No target repo files were modified.**

## What would be added now if explicitly applied

- App Blueprint seed, when analyzer produced one.
- `AGENTFORGE_MIGRATION.md`
- `AGENTFORGE_EXTENSION_PLAN.md`
- validation checklist docs
- module TODO/checklist docs
- environment example suggestions as documentation only

## What would be modified later

Runtime integration files, routers, package files, lockfiles, frontend components, backend business logic, and CI workflow changes remain future patch groups only.

## Manual steps

{chr(10).join('- ' + s for s in plan['manual_steps'])}

## Risks

{chr(10).join('- ' + r['risk'] + ': ' + r['detail'] for r in plan['risks'])}

## Validation commands

{chr(10).join('- ' + c for c in sorted({cmd for mp in plan['module_plans'] for cmd in mp['validation_commands']})) or '- python -m pytest'}

## Rollback notes

Delete the copied AgentForge docs/blueprint files. AgentForge does not stage, commit, push, install dependencies, run target scripts, deploy, or edit runtime files.
"""


def _file_impact_md(plan: dict[str, Any]) -> str:
    impact = plan["file_impact"]
    return "# File Impact\n\nLikely files to add later:\n" + "\n".join(f"- {p}" for p in impact["likely_files_to_add"]) + "\n\nLikely files to modify later:\n" + "\n".join(f"- {p}" for p in impact["likely_files_to_modify"]) + "\n"


def _migration_md(plan: dict[str, Any]) -> str:
    return "# Migration Phases\n\n" + "\n".join(f"- **{p['phase']}: {p['title']}** — {'; '.join(p['steps'])}" for p in plan["migration_phases"]) + "\n"


def _validation_md(plan: dict[str, Any]) -> str:
    return _validation_doc(plan)


def _patch_preview_md(plan: dict[str, Any]) -> str:
    return "# Patch Preview\n\nAllowed v0.8.2 apply writes are docs/blueprint/checklist files only. Runtime integration ideas remain notes, not patches.\n\n" + "\n".join(f"- write `{p}`" for p in sorted(_apply_files(plan))) + "\n"


def _migration_doc(plan: dict[str, Any]) -> str:
    return _migration_md(plan) + "\nNo target repo scripts, installs, commits, pushes, or deploys are performed by AgentForge.\n"


def _validation_doc(plan: dict[str, Any]) -> str:
    cmds = sorted({cmd for mp in plan["module_plans"] for cmd in mp["validation_commands"]}) or ["python -m pytest"]
    return "# AgentForge Validation Checklist\n\n" + "\n".join(f"- [ ] {cmd}" for cmd in cmds) + "\n- [ ] Review skipped runtime patch groups manually.\n"


def _module_todos(plan: dict[str, Any]) -> str:
    lines = ["# AgentForge Module TODOs", ""]
    for mp in plan["module_plans"]:
        lines.append(f"## {mp['module']} ({mp['status']}, {mp['risk_level']} risk)")
        lines += [f"- [ ] {p}" for p in mp["prerequisites"]]
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _env_suggestions(plan: dict[str, Any]) -> str:
    return "# .env.example Suggestions\n\nReview before copying into `.env.example`; v0.8.2 apply writes this as notes only and does not overwrite env files.\n\n```dotenv\n# Add only if relevant to selected modules.\nAGENTFORGE_PROVIDER_MODE=fixture\nAGENTFORGE_LLM_PROVIDER=scripted\n```\n"


def _safety_notes(apply: bool) -> list[str]:
    base = [
        "Default mode does not modify target repositories.",
        "No commits, staging, pushes, deploys, dependency installs, or target scripts are run.",
        "No live LLM/API dependency is introduced.",
        "Runtime code integration remains future work.",
    ]
    if apply:
        base += ["Apply requires --apply and approval.", "Dirty git repos and overwrites are refused unless explicitly allowed.", "Only low-risk docs/blueprint/checklist files are written."]
    return base


def _not_allowed_notes(plan: dict[str, Any]) -> list[str]:
    return sorted({p for mp in plan["module_plans"] for p in mp["likely_files_to_modify"] + mp["likely_files_to_add"] if not p.startswith(("AGENTFORGE", "domain-packs/", "agentforge/"))})[:50]
