"""Fuzzy Scanner — audit pipeline executed via the Swarms Cloud API.

Calls https://api.swarms.world/v1/swarm/completions with swarm_type=SequentialWorkflow.
The Swarms platform handles all agent execution, model routing, and billing.
"""

import os
import json
import httpx
from typing import Optional

from fuzzy_scanner.agents import ALL_AGENTS
from fuzzy_scanner.onchain import prepare_analysis_context, context_to_prompt

SWARMS_API_BASE = os.getenv("SWARMS_API_BASE", "https://api.swarms.world")
SWARMS_ENDPOINT = f"{SWARMS_API_BASE}/v1/swarm/completions"


class SwarmsAPIError(Exception):
    pass


def _get_api_key() -> str:
    key = (
        os.environ.get("SWARMS_API_KEY")
        or os.environ.get("fuzzy")
        or os.environ.get("FUZZY_API_KEY")
    )
    if not key:
        raise SwarmsAPIError(
            "No Swarms API key found. Set SWARMS_API_KEY (or 'fuzzy') in your .env."
        )
    return key


def call_swarms_api(task: str, agents: list, swarm_type: str = "SequentialWorkflow") -> dict:
    """POST to the Swarms Cloud /v1/swarm/completions endpoint."""
    headers = {
        "x-api-key": _get_api_key(),
        "Content-Type": "application/json",
    }
    payload = {
        "name": "FuzzyScanner-AuditPipeline",
        "description": "5-stage Solana smart contract security audit",
        "swarm_type": swarm_type,
        "task": task,
        "agents": agents,
        "max_loops": 1,
    }

    print(f"[Fuzzy Scanner] Sending swarm to Swarms Cloud ({swarm_type}, {len(agents)} agents)...")

    with httpx.Client(timeout=600) as client:
        resp = client.post(SWARMS_ENDPOINT, headers=headers, json=payload)

    if resp.status_code != 200:
        raise SwarmsAPIError(
            f"Swarms API error {resp.status_code}: {resp.text[:500]}"
        )

    return resp.json()


def extract_final_report(api_response: dict) -> str:
    """Extract the final agent's output (Report Writer) from a SequentialWorkflow response."""
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


def format_full_transcript(api_response: dict) -> str:
    """Build a full transcript showing each agent's output for debugging/verbose mode."""
    output = api_response.get("output")
    if not isinstance(output, list):
        return extract_final_report(api_response)

    parts = []
    for i, step in enumerate(output, start=1):
        if isinstance(step, dict):
            role = step.get("role") or step.get("agent_name") or f"Agent {i}"
            content = step.get("content") or step.get("output") or ""
            parts.append(f"\n{'=' * 80}\n## [{i}] {role}\n{'=' * 80}\n\n{content}")
        else:
            parts.append(f"\n## Step {i}\n{step}")
    return "\n".join(parts)


def run_audit(
    program_address: Optional[str] = None,
    source_code: Optional[str] = None,
    network: str = "mainnet",
    verbose: bool = False,
) -> str:
    """
    Run a full Fuzzy Scanner audit via the Swarms Cloud API.

    Args:
        program_address: Solana program/contract address (pubkey string).
        source_code:     Raw Rust/Anchor source code string (optional).
        network:         'mainnet' or 'devnet'.
        verbose:         If True, return the full multi-agent transcript.

    Returns:
        Full audit report as a Markdown string.
    """
    if not program_address and not source_code:
        raise ValueError("Provide at least a program_address or source_code.")

    if program_address:
        context = prepare_analysis_context(program_address, source_code, network)
        task = context_to_prompt(context)
    else:
        task = (
            "# Solana Smart Contract — Source Code Audit\n\n"
            "No on-chain address provided. Analyzing source code only.\n\n"
            "## Source Code\n```rust\n" + source_code + "\n```"
        )

    print("\n[Fuzzy Scanner] Starting 5-stage audit pipeline (Swarms Cloud)...\n")
    response = call_swarms_api(task=task, agents=ALL_AGENTS, swarm_type="SequentialWorkflow")

    meta = response.get("metadata") or response.get("usage") or {}
    billing = meta.get("billing_info") or {}
    if billing:
        print(f"[Fuzzy Scanner] Cost: ${billing.get('total_cost', 'unknown')}")
    if meta.get("execution_time_seconds"):
        print(f"[Fuzzy Scanner] Execution time: {meta['execution_time_seconds']:.2f}s")

    if verbose:
        return format_full_transcript(response)
    return extract_final_report(response)
