"""
AgentForge generator CLI.

Usage:
  agentforge generate <domain_pack_path> [--output <dir>] [--dry-run]
  agentforge plan    <domain_pack_path>
"""
import argparse
import json
import sys
from pathlib import Path

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
        if selection.gaps:
            print("  Gaps (explicit, not generated):")
            for gap in selection.gaps:
                print(f"    - {gap}")
        else:
            print("  Gaps: none")

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

    args = parser.parse_args()

    if args.command == "generate":
        sys.exit(cmd_generate(args))
    elif args.command == "plan":
        sys.exit(cmd_plan(args))


if __name__ == "__main__":
    main()
