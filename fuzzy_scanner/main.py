"""Fuzzy Scanner — CLI entry point."""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Support key stored as 'fuzzy' in .env (project convention) -> SWARMS_API_KEY
if not os.environ.get("SWARMS_API_KEY"):
    _fuzzy_key = os.environ.get("fuzzy", "")
    if _fuzzy_key:
        os.environ["SWARMS_API_KEY"] = _fuzzy_key

from fuzzy_scanner.pipeline import run_audit


BANNER = r"""
███████╗██╗   ██╗███████╗███████╗██╗   ██╗
██╔════╝██║   ██║╚══███╔╝╚══███╔╝╚██╗ ██╔╝
█████╗  ██║   ██║  ███╔╝   ███╔╝  ╚████╔╝
██╔══╝  ██║   ██║ ███╔╝   ███╔╝    ╚██╔╝
██║     ╚██████╔╝███████╗███████╗   ██║
╚═╝      ╚═════╝ ╚══════╝╚══════╝   ╚═╝
███████╗ ██████╗ █████╗ ███╗   ██╗███╗  ██╗███████╗██████╗
██╔════╝██╔════╝██╔══██╗████╗  ██║████╗ ██║██╔════╝██╔══██╗
███████╗██║     ███████║██╔██╗ ██║██╔██╗██║█████╗  ██████╔╝
╚════██║██║     ██╔══██║██║╚██╗██║██║╚████║██╔══╝  ██╔══██╗
███████║╚██████╗██║  ██║██║ ╚████║██║ ╚███║███████╗██║  ██║
╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚══╝╚══════╝╚═╝  ╚═╝

  Solana Smart Contract Auditor — Powered by Swarms
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fuzzy-scanner",
        description="Fuzzy Scanner: AI-powered Solana smart contract auditor",
    )
    p.add_argument(
        "--address",
        "-a",
        type=str,
        default=None,
        help="Solana program address (pubkey) to audit on-chain",
    )
    p.add_argument(
        "--source",
        "-s",
        type=str,
        default=None,
        help="Path to a Rust/Anchor source file (.rs) to audit",
    )
    p.add_argument(
        "--network",
        "-n",
        type=str,
        default="mainnet",
        choices=["mainnet", "devnet"],
        help="Solana network (default: mainnet)",
    )
    p.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Save report to this file path (default: print to stdout)",
    )
    p.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="LLM model to use (default: gpt-4o)",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show full multi-agent transcript (all 5 agents) instead of just final report",
    )
    return p


def main():
    print(BANNER)

    parser = build_parser()
    args = parser.parse_args()

    if not args.address and not args.source:
        parser.print_help()
        print("\n❌  Please provide --address and/or --source.\n")
        sys.exit(1)

    if args.model:
        os.environ["FUZZY_MODEL"] = args.model

    source_code = None
    if args.source:
        src_path = Path(args.source)
        if not src_path.exists():
            print(f"❌  Source file not found: {args.source}")
            sys.exit(1)
        source_code = src_path.read_text(encoding="utf-8")
        print(f"[Fuzzy Scanner] Source file loaded: {src_path.name} ({len(source_code):,} chars)")

    try:
        report = run_audit(
            program_address=args.address,
            source_code=source_code,
            network=args.network,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"\n❌  Audit failed: {exc}")
        sys.exit(1)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(report, encoding="utf-8")
        print(f"\n✅  Report saved to: {out_path}")
    else:
        print("\n" + "=" * 80)
        print(report)
        print("=" * 80)


if __name__ == "__main__":
    main()
