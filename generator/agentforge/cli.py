"""
AgentForge generator CLI.

Usage:
  agentforge generate <domain_pack_path> [--output <dir>] [--dry-run]
  agentforge plan    <domain_pack_path>
  agentforge init-blueprint <name> [--output <path>]
"""
import argparse
import json
import sys
from pathlib import Path

from agentforge.blueprints import create_starter_blueprint, write_starter_blueprint
from agentforge.generator import generate
from agentforge.modules import select_modules
from agentforge.pack import load_pack


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

    args = parser.parse_args()

    if args.command == "generate":
        sys.exit(cmd_generate(args))
    elif args.command == "plan":
        sys.exit(cmd_plan(args))
    elif args.command == "init-blueprint":
        sys.exit(cmd_init_blueprint(args))


if __name__ == "__main__":
    main()
