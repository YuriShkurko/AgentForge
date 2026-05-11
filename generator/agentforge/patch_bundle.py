"""Safe patch bundle and approved low-risk apply for AgentForge v0.8.1-v0.8.3."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import subprocess

from agentforge import __version__
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
    """Create a safe bundle preview, dry-run, or explicitly apply low-risk docs/blueprint files."""
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
    bundle_files = _bundle_files(plan, output_path)
    apply_ops = _apply_operations(plan)
    mode = "dry-run" if opts.dry_run else "apply" if opts.apply else "bundle"
    result = _base_result(mode, plan, target_repo, output_path, bundle_files, apply_ops)
    if opts.dry_run and opts.apply:
        result["planned_operations"] = _ops_for_result(apply_ops)
        result["next_steps"] = _next_steps(plan, output_path, "apply")

    _add_safety_context(result, target_repo, apply_ops, opts)

    if opts.dry_run:
        result["safety_checks"].append({"check": "dry_run", "status": "passed", "detail": "No files were written; bundle output and target repo are unchanged."})
        result["no_target_repo_modification"] = True
        return result

    if not opts.apply:
        _write_files(output_path, bundle_files, overwrite=True)
        result["applied_operations"] = _ops_for_result(bundle_files, base=output_path)
        result["safety_checks"].append({"check": "bundle_only", "status": "passed", "detail": "Only the explicit bundle output directory was written."})
        result["no_target_repo_modification"] = True
        return result

    if not opts.yes:
        result["refused_operations"].append({"path": str(target_repo) if target_repo else "", "reason": "apply requires explicit confirmation; type yes interactively or pass --yes"})
        result["safety_checks"].append({"check": "approval", "status": "failed", "detail": "Apply was not approved."})
        return result
    if not target_repo or not target_repo.exists() or not target_repo.is_dir():
        result["refused_operations"].append({"path": str(target_repo) if target_repo else "", "reason": "target repository path is unavailable"})
        result["safety_checks"].append({"check": "target_repo", "status": "failed", "detail": "Cannot apply without a local target repo."})
        return result

    dirty = result["dirty_repo_status"]["files"]
    if dirty and not opts.allow_dirty:
        result["refused_operations"] += [{"path": p, "reason": "dirty git working tree; commit/stash/revert or pass --allow-dirty"} for p in dirty]
        result["safety_checks"].append({"check": "dirty_git", "status": "failed", "detail": "Refusing apply because git status --short is dirty. Pass --allow-dirty only after review.", "files": dirty[:25]})
        return result
    result["safety_checks"].append({"check": "dirty_git", "status": "passed", "detail": "Clean or explicitly allowed.", "files": dirty[:25]})

    conflicts = result["overwrite_conflicts"]
    if conflicts and not opts.overwrite:
        result["refused_operations"] += [
            {"path": item["path"], "reason": "file exists; apply-eligible low-risk file would be overwritten", "apply_eligible": item["apply_eligible"], "suggestion": "Review content first; re-run with --overwrite only if replacing this AgentForge file is intended."}
            for item in conflicts
        ]
        result["safety_checks"].append({"check": "overwrite", "status": "failed", "detail": "Refusing to overwrite existing files.", "files": [item["path"] for item in conflicts]})
        return result
    result["safety_checks"].append({"check": "overwrite", "status": "passed", "detail": "No conflicts or overwrite explicitly allowed."})

    files = {op["path"]: op["content"] for op in apply_ops if op.get("approved_low_risk")}
    _write_files(target_repo, files, overwrite=opts.overwrite)
    manifest = _application_manifest(plan, result, sorted(files))
    log_path = target_repo / "AGENTFORGE_APPLICATION_MANIFEST.json"
    if log_path.exists() and not opts.overwrite:
        result["skipped_operations"].append({"path": log_path.name, "reason": "application manifest already exists"})
    else:
        log_text = json.dumps(manifest, indent=2) + "\n"
        log_path.write_text(log_text, encoding="utf-8")
        files[log_path.name] = log_text
    result["applied_operations"] = [{"path": p, "operation": "write", "risk": "low", "apply_eligible": True} for p in sorted(files)]
    result["skipped_operations"] += [{"path": n, "reason": "not allowed in v0.8.3 apply mode", "apply_eligible": False} for n in _not_allowed_notes(plan)]
    result["no_target_repo_modification"] = False
    return result


def render_prepare_result(result: dict[str, Any], format: str = "text") -> str:
    if format == "json":
        slim = {k: v for k, v in result.items() if k != "plan"}
        return json.dumps(slim, indent=2) + "\n"
    md = format == "md"
    h1 = "#" if md else ""
    h2 = "##" if md else ""
    lines = [
        f"{h1} AgentForge Prepare Extension Preview".strip(),
        "",
        f"{h2} Summary".strip(),
        f"- Mode: {result['mode']}",
        f"- Target repo: {result['target_repo']}",
        f"- Output path: {result['output_path']}",
        f"- No target repo modification: {result['no_target_repo_modification']}",
        f"- Dirty repo: {'yes' if result['dirty_repo_status']['dirty'] else 'no'}",
        "",
        f"{h2} Selected Modules".strip(),
        *(f"- {m}" for m in result["selected_modules"]),
    ]
    if not result["selected_modules"]:
        lines.append("- none")
    lines += ["", f"{h2} Planned Operations".strip()]
    lines += [f"- {op['operation']} `{op['path']}` ({op.get('risk', 'low')})" for op in result["planned_operations"]] or ["- none"]
    lines += ["", f"{h2} Apply-Eligible Files".strip()]
    lines += [f"- `{op['path']}`" for op in result["apply_eligible_operations"]] or ["- none"]
    lines += ["", f"{h2} Refused / Skipped Operations".strip()]
    refused = [f"- refused `{op['path']}`: {op['reason']}" for op in result["refused_operations"]]
    skipped = [f"- skipped `{op['path']}`: {op['reason']}" for op in result["skipped_operations"]]
    lines += refused + skipped or ["- none"]
    lines += ["", f"{h2} Safety Checks".strip()]
    lines += [f"- {c['check']}: {c['status']} — {c['detail']}" for c in result["safety_checks"]] or ["- none"]
    if result["overwrite_conflicts"]:
        lines += ["", "Overwrite conflicts:"] + [f"- `{c['path']}` (apply eligible: {c['apply_eligible']})" for c in result["overwrite_conflicts"]]
    if result["dirty_repo_status"]["files"]:
        lines += ["", "Dirty git entries:"] + [f"- `{p}`" for p in result["dirty_repo_status"]["files"][:25]]
    lines += ["", f"{h2} Validation Checklist".strip()]
    lines += [f"- [ ] {cmd}" for cmd in result["validation_commands"]] or ["- [ ] python -m pytest"]
    lines += ["", f"{h2} Next Steps".strip()]
    lines += [f"- {step}" for step in result["next_steps"]]
    if result["warnings"]:
        lines += ["", "Warnings:"] + [f"- {w}" for w in result["warnings"]]
    return "\n".join(lines).strip() + "\n"


def _base_result(mode: str, plan: dict[str, Any], target_repo: Path | None, output_path: Path, bundle_files: dict[str, str], apply_ops: list[dict[str, Any]]) -> dict[str, Any]:
    planned = _ops_for_result(apply_ops if mode == "apply" else bundle_files)
    return {
        "mode": mode,
        "target_repo": str(target_repo) if target_repo else plan["target_repo"].get("path", ""),
        "output_path": str(output_path),
        "selected_modules": plan["selected_modules"],
        "planned_operations": planned,
        "bundle_operations": _ops_for_result(bundle_files),
        "apply_eligible_operations": _ops_for_result(apply_ops),
        "applied_operations": [],
        "skipped_operations": [],
        "refused_operations": [],
        "overwrite_conflicts": [],
        "dirty_repo_status": {"is_git_repo": False, "dirty": False, "files": []},
        "safety_checks": [],
        "warnings": list(_safety_notes(apply=mode == "apply")),
        "validation_commands": _validation_commands(plan),
        "next_steps": _next_steps(plan, output_path, mode),
        "no_target_repo_modification": mode != "apply",
        "plan": plan,
    }


def _add_safety_context(result: dict[str, Any], target_repo: Path | None, apply_ops: list[dict[str, Any]], opts: PrepareExtensionOptions) -> None:
    if target_repo and target_repo.exists() and target_repo.is_dir():
        dirty = _dirty_git_files(target_repo)
        is_git = (target_repo / ".git").exists()
        result["dirty_repo_status"] = {"is_git_repo": is_git, "dirty": bool(dirty), "files": dirty[:50]}
        result["safety_checks"].append({"check": "dirty_git_preview", "status": "warning" if dirty else "passed", "detail": "Dirty entries detected; apply will refuse unless --allow-dirty is passed." if dirty else "No dirty git entries detected.", "files": dirty[:25]})
        result["overwrite_conflicts"] = [{"path": op["path"], "apply_eligible": bool(op.get("approved_low_risk")), "risk": op.get("risk", "low")} for op in apply_ops if (target_repo / op["path"]).exists()]
        result["safety_checks"].append({"check": "overwrite_preview", "status": "warning" if result["overwrite_conflicts"] else "passed", "detail": "Existing apply-eligible files would be refused without --overwrite." if result["overwrite_conflicts"] else "No apply overwrite conflicts detected.", "files": [c["path"] for c in result["overwrite_conflicts"]]})
    else:
        result["safety_checks"].append({"check": "target_repo", "status": "warning" if opts.from_report else "failed", "detail": "Target repo path is unavailable; bundle/dry-run is allowed but apply cannot run."})


def _target_repo_path(plan: dict[str, Any]) -> Path | None:
    raw = plan.get("target_repo", {}).get("path")
    return Path(raw).expanduser() if raw else None


def _bundle_files(plan: dict[str, Any], output_path: Path | None = None) -> dict[str, str]:
    apply_ops = _ops_for_result(_apply_files(plan))
    manifest = {
        "bundle_version": "v0.8.3",
        "generated_at": _now(),
        "agentforge_version": __version__,
        "target_repo_path": plan["target_repo"].get("path", ""),
        "target_repo": plan["target_repo"],
        "selected_modules": plan["selected_modules"],
        "operations": apply_ops,
        "planned_operations": apply_ops,
        "apply_eligibility": [{**op, "apply_eligible": True, "reason": "low-risk docs/blueprint/checklist file"} for op in apply_ops],
        "safety_checks": _safety_notes(apply=False),
        "warnings": _safety_notes(apply=False),
        "no_target_repo_files_modified": True,
    }
    files = {
        "README.md": _bundle_readme(plan, output_path),
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
    return [{"path": p, "content": c, "operation": "write", "risk": "low", "approved_low_risk": True, "apply_eligible": True, "reason": "low-risk docs/blueprint/checklist file"} for p, c in _apply_files(plan).items()]


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
        return [{"path": str((base / p) if base else p), "operation": "write", "risk": "low", "apply_eligible": True} for p in sorted(files)]
    return [{"path": op["path"], "operation": op.get("operation", "write"), "risk": op.get("risk", "low"), "apply_eligible": bool(op.get("apply_eligible", op.get("approved_low_risk", False))), **({"reason": op["reason"]} if op.get("reason") else {})} for op in files]


def _dirty_git_files(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    proc = subprocess.run(["git", "-C", str(root), "status", "--short"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return ["<git status failed>"]
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _bundle_readme(plan: dict[str, Any], output_path: Path | None = None) -> str:
    apply_cmd = f"agentforge prepare-extension {plan['target_repo'].get('path') or '<repo>'} --modules {','.join(plan['selected_modules'])} --apply"
    if output_path:
        bundle_cmd = f"agentforge prepare-extension {plan['target_repo'].get('path') or '<repo>'} --output {output_path}"
    else:
        bundle_cmd = f"agentforge prepare-extension {plan['target_repo'].get('path') or '<repo>'} --output agentforge-output/{plan['target_repo']['name']}-extension"
    validation = _validation_commands(plan)
    return f"""# AgentForge Safe Patch Bundle

Generated at: {_now()}
AgentForge version: {__version__}
Target repo analyzed: `{plan['target_repo'].get('path') or plan['target_repo']['name']}`
Selected modules: {', '.join(plan['selected_modules']) or 'none'}

This v0.8.3 bundle is a safe preview. **No target repo files were modified.**

## What this bundle is

A review package produced from the v0.8 Repo Extension Planner. It contains the extension plan, file impact, migration phases, validation checklist, safety notes, and proposed low-risk files.

## What was not applied

Nothing was applied to the target repo by bundle generation. Runtime integration files, routers, package files, lockfiles, frontend components, backend business logic, and CI workflow changes remain future notes only.

## What can be applied safely

Only AgentForge docs, validation/TODO checklists, env suggestion docs, and an App Blueprint seed when available.

## Commands

Recreate this bundle:

```bash
{bundle_cmd}
```

Preview apply without writing:

```bash
{apply_cmd} --dry-run
```

Apply low-risk files after review:

```bash
{apply_cmd}
# type yes when prompted, or add --yes for scripted local workflows
```

## Validation commands

{chr(10).join('- ' + c for c in validation)}

## Rollback guidance

Delete the copied AgentForge docs/blueprint/checklist files. AgentForge does not stage, commit, push, install dependencies, run target scripts, deploy, or edit runtime files.

## Safety limitations

{chr(10).join('- ' + s for s in _safety_notes(apply=True))}
"""


def _file_impact_md(plan: dict[str, Any]) -> str:
    impact = plan["file_impact"]
    return "# File Impact\n\nLikely files to add later:\n" + "\n".join(f"- {p}" for p in impact["likely_files_to_add"]) + "\n\nLikely files to modify later:\n" + "\n".join(f"- {p}" for p in impact["likely_files_to_modify"]) + "\n"


def _migration_md(plan: dict[str, Any]) -> str:
    return "# Migration Phases\n\n" + "\n".join(f"- **{p['phase']}: {p['title']}** — {'; '.join(p['steps'])}" for p in plan["migration_phases"]) + "\n"


def _validation_md(plan: dict[str, Any]) -> str:
    return _validation_doc(plan)


def _patch_preview_md(plan: dict[str, Any]) -> str:
    return "# Patch Preview\n\nAllowed v0.8.3 apply writes are docs/blueprint/checklist files only. Runtime integration ideas remain notes, not patches.\n\n## Apply-Eligible Files\n\n" + "\n".join(f"- write `{p}`" for p in sorted(_apply_files(plan))) + "\n\n## Not Applied\n\n" + "\n".join(f"- `{p}`" for p in _not_allowed_notes(plan)) + "\n"


def _migration_doc(plan: dict[str, Any]) -> str:
    return _migration_md(plan) + "\nNo target repo scripts, installs, commits, pushes, or deploys are performed by AgentForge.\n"


def _validation_doc(plan: dict[str, Any]) -> str:
    cmds = _validation_commands(plan)
    return "# AgentForge Validation Checklist\n\n" + "\n".join(f"- [ ] {cmd}" for cmd in cmds) + "\n- [ ] Review skipped runtime patch groups manually.\n"


def _module_todos(plan: dict[str, Any]) -> str:
    lines = ["# AgentForge Module TODOs", ""]
    for mp in plan["module_plans"]:
        lines.append(f"## {mp['module']} ({mp['status']}, {mp['risk_level']} risk)")
        lines += [f"- [ ] {p}" for p in mp["prerequisites"]]
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _env_suggestions(plan: dict[str, Any]) -> str:
    return "# .env.example Suggestions\n\nReview before copying into `.env.example`; v0.8.3 apply writes this as notes only and does not overwrite env files by default.\n\n```dotenv\n# Add only if relevant to selected modules.\nAGENTFORGE_PROVIDER_MODE=fixture\nAGENTFORGE_LLM_PROVIDER=scripted\n```\n"


def _safety_notes(apply: bool) -> list[str]:
    base = [
        "Default mode does not modify target repositories.",
        "No commits, staging, pushes, deploys, dependency installs, or target scripts are run.",
        "No live LLM/API dependency is introduced.",
        "Runtime code integration remains future work.",
    ]
    if apply:
        base += ["Apply requires --apply and an interactive yes or --yes.", "Dirty git repos and overwrites are refused unless explicitly allowed.", "Only low-risk docs/blueprint/checklist files are written."]
    return base


def _not_allowed_notes(plan: dict[str, Any]) -> list[str]:
    return sorted({p for mp in plan["module_plans"] for p in mp["likely_files_to_modify"] + mp["likely_files_to_add"] if not p.startswith(("AGENTFORGE", "domain-packs/", "agentforge/"))})[:50]


def _validation_commands(plan: dict[str, Any]) -> list[str]:
    return sorted({cmd for mp in plan["module_plans"] for cmd in mp["validation_commands"]}) or ["python -m pytest"]


def _next_steps(plan: dict[str, Any], output_path: Path, mode: str) -> list[str]:
    target = plan["target_repo"].get("path") or "<repo>"
    modules = f" --modules {','.join(plan['selected_modules'])}" if plan["selected_modules"] else ""
    if mode == "bundle":
        return [f"Review {output_path}/README.md and manifest.json.", f"Dry-run apply: agentforge prepare-extension {target}{modules} --dry-run", f"Apply low-risk files only: agentforge prepare-extension {target}{modules} --apply"]
    if mode == "dry-run":
        return ["Review planned/refused operations above.", f"Create bundle: agentforge prepare-extension {target}{modules} --output {output_path}", f"Apply low-risk files only after review: agentforge prepare-extension {target}{modules} --apply"]
    return ["Review planned writes and safety checks.", "Type yes when prompted or use --yes only for scripted local workflows.", "Run validation commands after apply."]


def _application_manifest(plan: dict[str, Any], result: dict[str, Any], applied_files: list[str]) -> dict[str, Any]:
    return {
        "mode": "apply",
        "generated_at": _now(),
        "agentforge_version": __version__,
        "target_repo": result["target_repo"],
        "selected_modules": plan["selected_modules"],
        "operations": result["apply_eligible_operations"],
        "applied_files": applied_files,
        "skipped_or_not_allowed": _not_allowed_notes(plan),
        "safety_checks": result["safety_checks"],
        "warnings": result["warnings"],
        "safety": _safety_notes(apply=True),
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
