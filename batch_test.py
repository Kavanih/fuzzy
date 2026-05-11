"""Batch-test Fuzzy Scanner against 10 well-known Solana programs.

Runs audits in parallel via Swarms Cloud, saves each report to audit_reports/,
and prints a summary table.
"""

import os
import re
import time
import concurrent.futures as cf
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("SWARMS_API_KEY"):
    os.environ["SWARMS_API_KEY"] = os.environ.get("fuzzy", "")

from fuzzy_scanner.pipeline import run_audit


# 10 well-known Solana programs (mix of native + Anchor programs)
TARGETS = [
    ("SPL Token Program",        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
    ("Associated Token Account", "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"),
    ("System Program",           "11111111111111111111111111111111"),
    ("Stake Program",            "Stake11111111111111111111111111111111111111"),
    ("Marinade Liquid Staking",  "MarBmsSgKXdrN1egZf5sqe1TMThczhVPPQRFgZbjB7"),
    ("Jupiter Aggregator V6",    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"),
    ("Drift Protocol V2",        "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"),
    ("Pump.fun",                 "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"),
    ("Orca Whirlpool",           "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"),
    ("Raydium AMM V4",           "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"),
]

OUT_DIR = Path("audit_reports")
OUT_DIR.mkdir(exist_ok=True)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def audit_one(name: str, address: str) -> dict:
    start = time.time()
    try:
        report = run_audit(program_address=address, network="mainnet", verbose=False)
        path = OUT_DIR / f"{slugify(name)}.md"
        path.write_text(report, encoding="utf-8")
        return {
            "name": name,
            "address": address,
            "status": "OK",
            "duration": round(time.time() - start, 1),
            "size": len(report),
            "report_path": str(path),
            "grade": extract_grade(report),
            "score": extract_score(report),
        }
    except Exception as e:
        return {
            "name": name,
            "address": address,
            "status": f"ERR: {str(e)[:80]}",
            "duration": round(time.time() - start, 1),
        }


def extract_grade(report: str):
    m = re.search(r"(?:risk\s*grade|grade)[:\s\*]+([A-F])\b", report, re.I)
    return m.group(1).upper() if m else "?"


def extract_score(report: str):
    m = re.search(r"(?:risk\s*score|overall\s*score)[:\s\*]+(\d{1,3})", report, re.I)
    return m.group(1) if m else "?"


def main():
    print(f"\n[Fuzzy Scanner] Batch testing {len(TARGETS)} Solana programs (parallel)...\n")
    overall_start = time.time()

    results = []
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(audit_one, name, addr): (name, addr) for name, addr in TARGETS}
        for fut in cf.as_completed(futures):
            r = fut.result()
            tag = "✅" if r["status"] == "OK" else "❌"
            print(f"{tag} {r['name']:30} {r['status']:6} grade={r.get('grade','-')} "
                  f"score={r.get('score','-')} {r['duration']}s")
            results.append(r)

    elapsed = round(time.time() - overall_start, 1)

    # Sort by original order
    order = {name: i for i, (name, _) in enumerate(TARGETS)}
    results.sort(key=lambda r: order.get(r["name"], 99))

    # Build summary report
    lines = [
        "# Fuzzy Scanner — Batch Audit Summary\n",
        f"**Programs audited:** {len(TARGETS)}",
        f"**Total elapsed:** {elapsed}s (parallel)",
        f"**Reports directory:** `audit_reports/`\n",
        "## Results\n",
        "| # | Program | Address | Status | Risk Grade | Risk Score | Duration | Report |",
        "|---|---------|---------|--------|------------|------------|----------|--------|",
    ]
    for i, r in enumerate(results, 1):
        addr_short = f"`{r['address'][:8]}...{r['address'][-4:]}`"
        report_link = f"[link]({r.get('report_path', '')})" if r.get("report_path") else "—"
        lines.append(
            f"| {i} | {r['name']} | {addr_short} | {r['status']} | "
            f"{r.get('grade', '-')} | {r.get('score', '-')} | {r['duration']}s | {report_link} |"
        )

    summary = "\n".join(lines)
    Path("BATCH_SUMMARY.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print("\n✅  Summary saved to BATCH_SUMMARY.md")


if __name__ == "__main__":
    main()
