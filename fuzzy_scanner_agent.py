"""Fuzzy Scanner — AI-powered Solana smart contract auditor.

A 5-agent SequentialWorkflow that audits any Solana program by program address,
raw Rust/Anchor source code, or both. Calls the Swarms Cloud API
(https://api.swarms.world/v1/swarm/completions) to execute the pipeline.

Pipeline stages:
    1. FuzzyParser        — structural breakdown of instructions, accounts, PDAs, CPIs
    2. FuzzyVulnHunter    — scans for 14 vulnerability classes
    3. FuzzyCodeQuality   — rates code quality across 10 dimensions (A–F grade)
    4. FuzzyRiskAssessor  — 0–100 risk score + prioritized remediation roadmap
    5. FuzzyReportWriter  — publication-grade Markdown audit report

Usage:
    >>> from fuzzy_scanner_agent import run_audit
    >>> report = run_audit(program_address="JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4")
    >>> print(report)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL: str = os.getenv("FUZZY_MODEL", "gpt-4o")
SWARMS_API_BASE: str = os.getenv("SWARMS_API_BASE", "https://api.swarms.world")
SWARMS_ENDPOINT: str = f"{SWARMS_API_BASE}/v1/swarm/completions"


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

PARSER_AGENT: Dict[str, Any] = {
    "agent_name": "FuzzyParser",
    "description": "Solana smart contract structural parser",
    "system_prompt": (
        "You are an expert Solana and Anchor smart contract parser.\n\n"
        "Given a Solana program address with on-chain metadata, IDL data, and/or raw "
        "Rust/Anchor source code, produce a thorough structural breakdown.\n\n"
        "Identify: 1) Entry points / instructions, 2) Account structures and constraints, "
        "3) PDA derivations, 4) Cross-program invocations, 5) Token operations, "
        "6) Authority patterns, 7) State machines, 8) Math operations.\n\n"
        "Output a structured, clearly sectioned markdown report. If information is "
        "unavailable (no IDL, no source), note it explicitly and infer what you can."
    ),
    "model_name": DEFAULT_MODEL,
    "max_loops": 1,
    "temperature": 0.2,
}

VULN_HUNTER_AGENT: Dict[str, Any] = {
    "agent_name": "FuzzyVulnHunter",
    "description": "Solana smart contract vulnerability scanner",
    "system_prompt": (
        "You are a world-class Solana smart contract security researcher.\n\n"
        "Given a parsed Solana contract analysis, hunt for vulnerabilities. For each "
        "finding output: ID (VUL-001+), Type, Severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), "
        "Location, Description, Exploit Scenario.\n\n"
        "Vulnerability classes: 1) Missing Signer Check, 2) Missing Owner Check, "
        "3) Integer Overflow/Underflow, 4) PDA Seed Collision, 5) Reentrancy via CPI, "
        "6) Arbitrary CPI, 7) Account Data Confusion, 8) Lamport Drain, "
        "9) Flash Loan Vectors, 10) Privilege Escalation, 11) Unvalidated Account Closing, "
        "12) Missing Rent Check, 13) Upgrade Authority Risk, 14) Oracle Manipulation.\n\n"
        "If no vulnerability is found for a class, output it as INFO with 'Not detected.' "
        "Be thorough — missing findings is worse than false positives."
    ),
    "model_name": DEFAULT_MODEL,
    "max_loops": 1,
    "temperature": 0.3,
}

CODE_QUALITY_AGENT: Dict[str, Any] = {
    "agent_name": "FuzzyCodeQuality",
    "description": "Solana smart contract code quality assessor",
    "system_prompt": (
        "You are a senior Solana/Anchor smart contract engineer.\n\n"
        "Evaluate code quality across: 1) Anchor constraint coverage, 2) Error handling, "
        "3) Compute unit efficiency, 4) Account size management, 5) Event emission, "
        "6) Documentation, 7) Test infrastructure signals, 8) Upgrade safety, "
        "9) Dependency risk, 10) Best practice adherence.\n\n"
        "For each dimension provide: Score 1-5, Findings, Recommendation. "
        "End with an overall quality grade: A / B / C / D / F."
    ),
    "model_name": DEFAULT_MODEL,
    "max_loops": 1,
    "temperature": 0.3,
}

RISK_ASSESSOR_AGENT: Dict[str, Any] = {
    "agent_name": "FuzzyRiskAssessor",
    "description": "DeFi smart contract risk scorer and prioritizer",
    "system_prompt": (
        "You are a DeFi risk assessment specialist.\n\n"
        "Produce: 1) Overall Risk Score 0-100, 2) Risk Grade A-F, "
        "3) Risk Breakdown (Security/Operational/Upgrade/Economic each 0-100), "
        "4) Safe to Interact? YES/NO/WITH CAUTION + reason, "
        "5) Prioritized Remediation Roadmap (P0-P3, Low/Med/High effort, expected risk reduction), "
        "6) Integration Recommendations.\n\n"
        "Be precise, data-driven, and realistic. Justify every score with reference to specific findings."
    ),
    "model_name": DEFAULT_MODEL,
    "max_loops": 1,
    "temperature": 0.2,
}

REPORT_WRITER_AGENT: Dict[str, Any] = {
    "agent_name": "FuzzyReportWriter",
    "description": "Professional blockchain security audit report generator",
    "system_prompt": (
        "You are a professional blockchain security auditor at a top-tier firm.\n\n"
        "Synthesize all prior analysis into a comprehensive, publication-quality audit "
        "report in Markdown. Sections required:\n"
        "1. Executive Summary (program address, network, audit date, risk grade/score, "
        "findings counts by severity, bottom-line recommendation)\n"
        "2. Scope & Methodology\n"
        "3. Findings Summary Table (ID | Title | Severity | Status)\n"
        "4. Detailed Findings (description, impact, PoC, recommendation, references)\n"
        "5. Code Quality Assessment\n"
        "6. Risk Assessment\n"
        "7. Conclusion\n\n"
        "Use professional language. Be specific — reference instruction names, account "
        "names, line numbers when available."
    ),
    "model_name": DEFAULT_MODEL,
    "max_loops": 1,
    "temperature": 0.4,
}

ALL_AGENTS: List[Dict[str, Any]] = [
    PARSER_AGENT,
    VULN_HUNTER_AGENT,
    CODE_QUALITY_AGENT,
    RISK_ASSESSOR_AGENT,
    REPORT_WRITER_AGENT,
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SwarmsAPIError(Exception):
    """Raised when the Swarms Cloud API returns a non-200 response."""


# ---------------------------------------------------------------------------
# On-chain data fetchers
# ---------------------------------------------------------------------------


def fetch_program_account(program_address: str, rpc_url: str) -> Dict[str, Any]:
    """Fetch raw Solana account info for a program address via JSON-RPC.

    Args:
        program_address: Base58-encoded Solana program pubkey.
        rpc_url:         JSON-RPC endpoint (mainnet or devnet).

    Returns:
        Dict with keys: lamports, owner, executable, rent_epoch, data_size.
        Returns {"error": "..."} if the account is not found.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [program_address, {"encoding": "base64", "commitment": "confirmed"}],
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(rpc_url, json=payload)
        resp.raise_for_status()
        result = resp.json().get("result", {}) or {}
    value = result.get("value")
    if value is None:
        return {"error": f"Program {program_address} not found on-chain."}
    import base64
    data_field = value.get("data") or [""]
    return {
        "lamports": value.get("lamports"),
        "owner": value.get("owner"),
        "executable": value.get("executable", False),
        "rent_epoch": value.get("rentEpoch"),
        "data_size": len(base64.b64decode(data_field[0])) if data_field[0] else 0,
    }


def build_task_prompt(
    program_address: Optional[str],
    source_code: Optional[str],
    network: str,
    account_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the rich task prompt sent to the Swarms agent pipeline.

    Args:
        program_address: Optional Solana program pubkey.
        source_code:     Optional raw Rust/Anchor source code.
        network:         "mainnet" or "devnet".
        account_info:    Optional on-chain account info dict.

    Returns:
        A single Markdown-formatted prompt string.
    """
    lines: List[str] = ["# Solana Program Audit Target", ""]
    if program_address:
        lines += [
            f"**Program Address:** `{program_address}`",
            f"**Network:** {network}",
            "",
        ]
    if account_info:
        lines += [
            "## On-Chain Account Info",
            f"- Executable: {account_info.get('executable')}",
            f"- Owner (loader): `{account_info.get('owner')}`",
            f"- Data size: {account_info.get('data_size', 0):,} bytes",
            f"- Lamports: {account_info.get('lamports', 0):,}",
            "",
        ]
    if source_code:
        lines += ["## Source Code", "```rust", source_code, "```"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Swarms Cloud API client
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    """Resolve the Swarms API key from env vars (SWARMS_API_KEY, FUZZY_API_KEY, fuzzy)."""
    key = (
        os.environ.get("SWARMS_API_KEY")
        or os.environ.get("FUZZY_API_KEY")
        or os.environ.get("fuzzy")
    )
    if not key:
        raise SwarmsAPIError(
            "No Swarms API key found. Set SWARMS_API_KEY in your environment."
        )
    return key


def call_swarms_api(
    task: str,
    agents: List[Dict[str, Any]],
    swarm_type: str = "SequentialWorkflow",
) -> Dict[str, Any]:
    """POST to the Swarms Cloud /v1/swarm/completions endpoint.

    Args:
        task:       The task prompt to send to the swarm.
        agents:     List of agent configuration dicts.
        swarm_type: Swarm orchestration type (default: SequentialWorkflow).

    Returns:
        Parsed JSON response from the Swarms API.

    Raises:
        SwarmsAPIError: If the API returns a non-200 status.
    """
    headers = {"x-api-key": _get_api_key(), "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "name": "FuzzyScanner-AuditPipeline",
        "description": "5-stage Solana smart contract security audit",
        "swarm_type": swarm_type,
        "task": task,
        "agents": agents,
        "max_loops": 1,
    }
    with httpx.Client(timeout=600) as client:
        resp = client.post(SWARMS_ENDPOINT, headers=headers, json=payload)
    if resp.status_code != 200:
        raise SwarmsAPIError(f"Swarms API error {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def extract_final_report(api_response: Dict[str, Any]) -> str:
    """Extract the final agent's output (Report Writer) from a swarm response.

    Args:
        api_response: Raw JSON dict returned by call_swarms_api.

    Returns:
        The final Markdown audit report as a string.
    """
    import json
    output = api_response.get("output")
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        last = output[-1]
        if isinstance(last, dict):
            return last.get("content") or last.get("output") or json.dumps(last, indent=2)
        return str(last)
    if isinstance(output, dict):
        return output.get("content") or json.dumps(output, indent=2)
    return json.dumps(api_response, indent=2)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_audit(
    program_address: Optional[str] = None,
    source_code: Optional[str] = None,
    network: str = "mainnet",
) -> str:
    """Run a full Fuzzy Scanner audit via the Swarms Cloud API.

    Args:
        program_address: Solana program/contract address (base58 pubkey string).
                         At least one of program_address or source_code must be provided.
        source_code:     Raw Rust/Anchor source code string (optional).
        network:         "mainnet" or "devnet". Default: "mainnet".

    Returns:
        Full audit report as a Markdown string.

    Raises:
        ValueError:      If neither program_address nor source_code is provided.
        SwarmsAPIError:  If the Swarms API call fails.

    Example:
        >>> report = run_audit(program_address="JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4")
        >>> print(report[:200])
    """
    if not program_address and not source_code:
        raise ValueError("Provide at least a program_address or source_code.")

    rpc_url = (
        "https://solana-mainnet.infura.io/v3/e54c2b087ce04c7fb31a445d3f4f3e9c"
        if network == "mainnet"
        else "https://api.devnet.solana.com"
    )

    account_info: Optional[Dict[str, Any]] = None
    if program_address:
        try:
            account_info = fetch_program_account(program_address, rpc_url)
        except Exception as exc:
            account_info = {"error": f"On-chain fetch failed: {exc}"}

    task = build_task_prompt(program_address, source_code, network, account_info)
    response = call_swarms_api(task=task, agents=ALL_AGENTS, swarm_type="SequentialWorkflow")
    return extract_final_report(response)


if __name__ == "__main__":
    import sys
    addr = sys.argv[1] if len(sys.argv) > 1 else "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
    print(run_audit(program_address=addr))
