"""
AgentForge generator CLI.

Usage:
  agentforge generate <domain_pack_path> [--output <dir>] [--dry-run]
  agentforge plan    <domain_pack_path>
  agentforge init-blueprint <name> [--output <path>]
  agentforge analyze-repo <path> [--format text|md|json]
  agentforge serve-builder [--host <host>] [--port <port>]
"""
import argparse
import json
import sys
from pathlib import Path

from agentforge.analyzer import AnalyzeOptions, analyze_repo, render_report, result_to_jsonable
from agentforge.blueprints import create_starter_blueprint, write_starter_blueprint
from agentforge.generator import generate
from agentforge.modules import select_modules
from agentforge.pack import load_pack
from agentforge.planner.scripted import ScriptedPlanner
from agentforge.planner.server import serve_builder


def cmd_generate(args: argparse.Namespace) -> int:
    pack_path = Path(args.pack)
    if not pack_path.exists():
        print(f"error: domain pack not found: {pack_path}", file=sys.stderr)
        return 1

    try:
        pack = load_pack(pack_path)
    except Exception as exc:
        print(f"error: invalid domain pack — {exc}", file=sys.stderr)
        return 1

    output_dir = Path(args.output) if args.output else Path("examples") / pack.name

    if output_dir.exists() and not args.force and not args.dry_run:
        print(f"error: output directory already exists: {output_dir}", file=sys.stderr)
        print("Use --force to overwrite.", file=sys.stderr)
        return 1

    try:
        result = generate(pack, output_dir, dry_run=args.dry_run)
    except Exception as exc:
        print(f"error: generation failed — {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        label = "[dry-run] " if result["dry_run"] else ""
        print(f"{label}Generated '{pack.display_name}' ({pack.app_archetype})")
        print(f"  Output:   {result['output_dir']}")
        print(f"  Template: {result['template']}")
        print(f"  Modules:  {', '.join(result['modules'])}")
        print(f"  Files:    {result['files_written']}")
        if result["gaps"]:
            print("  Gaps:")
            for gap in result["gaps"]:
                print(f"    - {gap}")
        if not result["dry_run"]:
            print(f"\n  Next: see {result['output_dir']}/run_commands.txt")

    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    pack_path = Path(args.pack)
    if not pack_path.exists():
        print(f"error: domain pack not found: {pack_path}", file=sys.stderr)
        return 1

    try:
        pack = load_pack(pack_path)
    except Exception as exc:
        print(f"error: invalid domain pack — {exc}", file=sys.stderr)
        return 1

    selection = select_modules(pack)

    if args.json:
        print(json.dumps({
            "name": pack.name,
            "display_name": pack.display_name,
            "archetype": selection.archetype,
            "required_modules": sorted(selection.required),
            "optional_modules": sorted(selection.optional),
            "active_modules": sorted(selection.active),
            "agent_runtime": pack.agent_runtime.model_dump() if pack.agent_runtime else None,
            "workspace": pack.workspace.model_dump() if pack.workspace else None,
            "template": selection.template,
            "gaps": selection.gaps,
        }, indent=2))
    else:
        print(f"Plan for: {pack.display_name} ({pack.name})")
        print(f"  Archetype:        {selection.archetype}")
        print(f"  Template:         {selection.template}")
        print(f"  Required modules: {', '.join(sorted(selection.required))}")
        if selection.optional:
            print(f"  Optional modules: {', '.join(sorted(selection.optional))}")
        print(f"  Active modules:   {', '.join(sorted(selection.active))}")
        if pack.agent_runtime and pack.agent_runtime.enabled:
            print(f"  Agent runtime:    enabled ({pack.agent_runtime.provider_mode})")
            if pack.agent_runtime.streaming:
                enabled = pack.agent_runtime.streaming.get("enabled", False)
                print(f"  Streaming:        {'enabled' if enabled else 'disabled'}")
        if pack.workspace and pack.workspace.enabled:
            print("  Workspace:        enabled")
            print(f"  Widgets:          {len(pack.widgets)} type(s)")
        if selection.gaps:
            print("  Gaps (explicit, not generated):")
            for gap in selection.gaps:
                print(f"    - {gap}")
        else:
            print("  Gaps: none")

    return 0


def cmd_init_blueprint(args: argparse.Namespace) -> int:
    try:
        blueprint = create_starter_blueprint(
            args.name,
            display_name=args.display_name,
            description=args.description,
            target_user=args.target_user,
            archetype=args.archetype,
            optional_modules=args.optional_module,
            workspace_enabled=not args.no_workspace,
            fixture_provider_enabled=not args.no_fixture_provider,
        )
    except Exception as exc:
        print(f"error: could not create starter blueprint - {exc}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else Path("domain-packs") / blueprint["name"] / "domain-pack.yaml"

    try:
        write_starter_blueprint(output, blueprint, force=args.force)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("Use --force to overwrite.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: could not write starter blueprint - {exc}", file=sys.stderr)
        return 1

    print(f"Created App Blueprint: {output}")
    print(f"Next: agentforge plan {output}")
    return 0


def cmd_draft_blueprint(args: argparse.Namespace) -> int:
    if args.planner != "scripted":
        print("error: only the scripted planner is available in v0.6", file=sys.stderr)
        return 1

    answers = None
    if args.answers:
        try:
            answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"error: could not read answers JSON - {exc}", file=sys.stderr)
            return 1

    result = ScriptedPlanner().draft(args.idea, answers)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.status in {"draft", "needs_clarification"} else 1

    if result.status == "needs_clarification":
        print("Clarification needed:")
        for question in result.questions:
            print(f"  - {question}")
        return 2
    if result.status == "error":
        print("error: planner failed", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    if args.out:
        output = Path(args.out)
        if output.exists() and not args.force:
            print(f"error: refusing to overwrite existing file: {output}", file=sys.stderr)
            print("Use --force to overwrite.", file=sys.stderr)
            return 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.yaml or "", encoding="utf-8")
        print(f"Drafted App Blueprint: {output}")
        for command in result.commands:
            print(f"Next: {command.replace('./domain-packs/' + result.blueprint['name'] + '/domain-pack.yaml', str(output))}")
    else:
        print(result.yaml or "")
    return 0


def cmd_analyze_repo(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: repository path not found: {path}", file=sys.stderr)
        return 1

    report_format = "json" if args.json else args.format
    try:
        result = analyze_repo(
            path,
            AnalyzeOptions(
                max_files=args.max_files,
                include_tests=args.include_tests,
                include_blueprint_draft=not args.no_blueprint_draft,
                report_format=report_format,
            ),
        )
        output = json.dumps(result_to_jsonable(result), indent=2) + "\n" if report_format == "json" else render_report(result, report_format)
    except Exception as exc:
        print(f"error: repo analysis failed - {exc}", file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output)
        if any(part in {"node_modules", ".git", ".venv", "venv", "dist", "build", ".next"} for part in output_path.parts):
            print(f"error: refusing to write report inside ignored/vendor path: {output_path}", file=sys.stderr)
            return 1
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
        except Exception as exc:
            print(f"error: could not write report - {exc}", file=sys.stderr)
            return 1
        print(f"Wrote repo analysis report: {output_path}")
    else:
        print(output, end="")
    return 0


def cmd_serve_builder(args: argparse.Namespace) -> int:
    try:
        serve_builder(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nStopped AgentForge builder server.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agentforge",
        description="AgentForge — generate Product Shell apps from Domain Packs",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate app from a Domain Pack")
    gen.add_argument("pack", help="Path to domain-pack.yaml")
    gen.add_argument("--output", "-o", help="Output directory (default: examples/<pack-name>)")
    gen.add_argument("--force", "-f", action="store_true", help="Overwrite existing output directory")
    gen.add_argument("--dry-run", action="store_true", help="Validate and plan without writing files")
    gen.add_argument("--json", action="store_true", help="Output result as JSON")

    plan = sub.add_parser("plan", help="Show module selection plan for a Domain Pack (no file output)")
    plan.add_argument("pack", help="Path to domain-pack.yaml")
    plan.add_argument("--json", action="store_true", help="Output as JSON")

    init = sub.add_parser("init-blueprint", help="Create a starter App Blueprint YAML file")
    init.add_argument("name", help="App Blueprint machine/display name")
    init.add_argument("--output", "-o", help="Output YAML path (default: domain-packs/<name>/domain-pack.yaml)")
    init.add_argument("--force", "-f", action="store_true", help="Overwrite existing output file")
    init.add_argument("--display-name", help="Human-readable display name")
    init.add_argument(
        "--description",
        default="A local AgentForge app created with the Blueprint Builder.",
        help="Product purpose text",
    )
    init.add_argument("--target-user", default="developer", help="Primary target user/persona")
    init.add_argument(
        "--archetype",
        default="ingestion_scoring_pipeline",
        choices=[
            "agent_dashboard_app",
            "ingestion_scoring_pipeline",
            "notification_triage_app",
            "hybrid_agent_pipeline",
            "deploy_planner_app",
        ],
        help="App archetype",
    )
    init.add_argument(
        "--optional-module",
        action="append",
        default=[],
        help="Optional feature module to include; repeat for multiple modules",
    )
    init.add_argument("--no-workspace", action="store_true", help="Do not include the workspace optional config")
    init.add_argument("--no-fixture-provider", action="store_true", help="Mark fixture provider seed data as disabled")

    draft = sub.add_parser("draft-blueprint", help="Draft an App Blueprint with the scripted planner")
    draft.add_argument("--idea", required=True, help="Short app idea to draft from")
    draft.add_argument("--answers", help="Optional JSON file with clarification answers")
    draft.add_argument("--out", help="Write YAML to this path instead of stdout")
    draft.add_argument("--force", action="store_true", help="Overwrite --out if it exists")
    draft.add_argument("--planner", default="scripted", choices=["scripted", "live"], help="Planner backend")
    draft.add_argument("--json", action="store_true", help="Output full PlannerResult JSON")

    analyze = sub.add_parser("analyze-repo", help="Analyze a local repository without modifying it")
    analyze.add_argument("path", help="Local repository or project directory to inspect")
    analyze.add_argument("--format", choices=["text", "md", "json"], default="text", help="Report format")
    analyze.add_argument("--json", action="store_true", help="Shortcut for --format json")
    analyze.add_argument("--output", "-o", help="Write report to this path instead of stdout")
    analyze.add_argument("--max-files", type=int, default=1000, help="Maximum files to scan")
    analyze.add_argument("--include-tests", action="store_true", help="Include deep test directory content sniffing")
    analyze.add_argument("--no-blueprint-draft", action="store_true", help="Omit the draft App Blueprint seed")

    serve = sub.add_parser("serve-builder", help="Serve the static builder with scripted planner endpoints")
    serve.add_argument("--host", default="127.0.0.1", help="Host to bind")
    serve.add_argument("--port", type=int, default=8765, help="Port to bind")

    args = parser.parse_args()

    if args.command == "generate":
        sys.exit(cmd_generate(args))
    elif args.command == "plan":
        sys.exit(cmd_plan(args))
    elif args.command == "init-blueprint":
        sys.exit(cmd_init_blueprint(args))
    elif args.command == "draft-blueprint":
        sys.exit(cmd_draft_blueprint(args))
    elif args.command == "analyze-repo":
        sys.exit(cmd_analyze_repo(args))
    elif args.command == "serve-builder":
        sys.exit(cmd_serve_builder(args))


if __name__ == "__main__":
    main()
