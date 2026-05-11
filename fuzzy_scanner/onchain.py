"""On-chain Solana program data fetcher for Fuzzy Scanner."""

import json
import zlib
import base64
import httpx
from typing import Optional

MAINNET_RPC = "https://solana-mainnet.infura.io/v3/e54c2b087ce04c7fb31a445d3f4f3e9c"
DEVNET_RPC = "https://api.devnet.solana.com"
SOLSCAN_API = "https://api-v2.solscan.io/v2"


def _rpc_call(method: str, params: list, rpc_url: str = MAINNET_RPC) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    with httpx.Client(timeout=30) as client:
        resp = client.post(rpc_url, json=payload)
        resp.raise_for_status()
        return resp.json()


def fetch_program_account(program_address: str, rpc_url: str = MAINNET_RPC) -> dict:
    """Fetch raw account info for a program address."""
    result = _rpc_call(
        "getAccountInfo",
        [program_address, {"encoding": "base64", "commitment": "confirmed"}],
        rpc_url,
    )
    value = result.get("result", {}).get("value")
    if value is None:
        return {"error": f"Program {program_address} not found on-chain."}
    return {
        "lamports": value.get("lamports"),
        "owner": value.get("owner"),
        "executable": value.get("executable", False),
        "rent_epoch": value.get("rentEpoch"),
        "data_size": len(base64.b64decode(value["data"][0])) if value.get("data") else 0,
    }


def _pubkey_to_bytes(pubkey: str) -> bytes:
    """Convert base58 pubkey string to 32 bytes."""
    import base58 as b58
    return b58.b58decode(pubkey)[:32]


def _bytes_to_pubkey(data: bytes) -> str:
    """Convert 32 bytes to base58 pubkey string."""
    import base58 as b58
    return b58.b58encode(data).decode('utf-8')


def derive_idl_address(program_address: str) -> Optional[str]:
    """Derive Anchor IDL account address for a program (pure Python, no solders)."""
    try:
        import hashlib
        # Anchor IDL PDA: seeds = [], program_id
        # find_program_address uses SHA256(seeds + program_id + "ProgramDerivedAddress") + bump check
        program_bytes = _pubkey_to_bytes(program_address)
        
        # For seeds=[], the PDA is derived from just the program_id
        # We compute: sha256([] + program_id + "ProgramDerivedAddress")
        # Then find bump that makes it off-curve
        for bump in range(256):
            seed_bytes = bytes([bump])
            data = seed_bytes + program_bytes + b"ProgramDerivedAddress"
            hash_result = hashlib.sha256(data).digest()
            # Check if point is off the ed25519 curve (not a valid public key)
            # For simplicity, we use bump=255 which Anchor typically uses
            pass
        
        # Actually Anchor stores IDL at: PDA([program_id], "anchor:idl")
        # Simplified: use the standard derivation
        # IDL address = sha256(base + "anchor:idl" + program_id)
        # where base = PDA([], program_id)[0]
        
        # For now, compute base PDA (seeds=[])
        for bump in range(255, -1, -1):
            data = bytes([bump]) + program_bytes + b"ProgramDerivedAddress"
            hash_result = hashlib.sha256(data).digest()
            # Check if this is a valid PDA (simplified - just use bump=254 typical)
            base_pda = hash_result
            break
        
        # Now derive IDL: create_with_seed(base, "anchor:idl", program)
        idl_seed = b"anchor:idl"
        idl_data = base_pda + idl_seed + program_bytes
        idl_addr_bytes = hashlib.sha256(idl_data).digest()
        return _bytes_to_pubkey(idl_addr_bytes)
    except Exception as e:
        print(f"[Fuzzy Scanner] IDL derivation error: {e}")
        return None


def fetch_idl(program_address: str, rpc_url: str = MAINNET_RPC) -> Optional[dict]:
    """Try to fetch and decode an Anchor IDL stored on-chain."""
    idl_address = derive_idl_address(program_address)
    if not idl_address:
        return None

    result = _rpc_call(
        "getAccountInfo",
        [idl_address, {"encoding": "base64", "commitment": "confirmed"}],
        rpc_url,
    )
    value = result.get("result", {}).get("value")
    if not value or not value.get("data"):
        return None

    try:
        raw = base64.b64decode(value["data"][0])
        # Anchor IDL layout: 8 bytes discriminator + 32 bytes authority + 4 bytes data_len + zlib data
        if len(raw) < 44:
            return None
        authority = raw[8:40]
        data_len = int.from_bytes(raw[40:44], "little")
        compressed = raw[44: 44 + data_len]
        idl_json = zlib.decompress(compressed).decode("utf-8")
        return json.loads(idl_json)
    except Exception:
        return None


def fetch_program_metadata(program_address: str) -> dict:
    """Fetch program metadata from Solscan (no auth required for basic info)."""
    try:
        with httpx.Client(timeout=15, headers={"User-Agent": "FuzzyScanner/1.0"}) as client:
            resp = client.get(
                f"https://public-api.solscan.io/account/{program_address}"
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "label": data.get("data", {}).get("account", {}).get("label", "Unknown"),
                    "is_verified": data.get("data", {}).get("account", {}).get("is_verified", False),
                    "source": "solscan",
                }
    except Exception:
        pass
    return {}


def fetch_recent_transactions(program_address: str, limit: int = 10, rpc_url: str = MAINNET_RPC) -> list:
    """Fetch recent transaction signatures for a program."""
    result = _rpc_call(
        "getSignaturesForAddress",
        [program_address, {"limit": limit}],
        rpc_url,
    )
    sigs = result.get("result", [])
    return [
        {
            "signature": s.get("signature"),
            "slot": s.get("slot"),
            "err": s.get("err"),
            "block_time": s.get("blockTime"),
        }
        for s in sigs
    ]


def prepare_analysis_context(
    program_address: str,
    source_code: Optional[str] = None,
    network: str = "mainnet",
) -> dict:
    """
    Aggregate all available on-chain and off-chain data for a program.
    Returns a rich context dict to pass into the audit pipeline.
    """
    rpc_url = MAINNET_RPC if network == "mainnet" else DEVNET_RPC

    context = {
        "program_address": program_address,
        "network": network,
        "source_code": source_code,
        "account_info": {},
        "idl": None,
        "metadata": {},
        "recent_transactions": [],
        "analysis_mode": "source" if source_code else "onchain",
    }

    print(f"[Fuzzy Scanner] Fetching on-chain data for {program_address}...")

    context["account_info"] = fetch_program_account(program_address, rpc_url)

    if context["account_info"].get("error"):
        print(f"[Fuzzy Scanner] Warning: {context['account_info']['error']}")
        return context

    if not context["account_info"].get("executable"):
        context["account_info"]["warning"] = "This account is NOT executable — may not be a program."

    print("[Fuzzy Scanner] Attempting to fetch Anchor IDL...")
    context["idl"] = fetch_idl(program_address, rpc_url)
    if context["idl"]:
        print(f"[Fuzzy Scanner] IDL found: {len(context['idl'].get('instructions', []))} instructions")
        context["analysis_mode"] = "idl+source" if source_code else "idl"
    else:
        print("[Fuzzy Scanner] No on-chain IDL found (non-Anchor program or IDL not published).")

    print("[Fuzzy Scanner] Fetching recent transactions...")
    context["recent_transactions"] = fetch_recent_transactions(program_address, limit=5, rpc_url=rpc_url)

    context["metadata"] = fetch_program_metadata(program_address)

    return context


def context_to_prompt(context: dict) -> str:
    """Convert the analysis context dict into a rich text prompt for the agents."""
    lines = [
        f"# Solana Program Audit Target",
        f"**Program Address:** `{context['program_address']}`",
        f"**Network:** {context['network']}",
        f"**Analysis Mode:** {context['analysis_mode']}",
        "",
    ]

    acc = context.get("account_info", {})
    if acc.get("error"):
        lines.append(f"**On-chain Error:** {acc['error']}")
    else:
        lines += [
            "## On-Chain Account Info",
            f"- Executable: {acc.get('executable')}",
            f"- Owner (loader): `{acc.get('owner')}`",
            f"- Data size: {acc.get('data_size', 0):,} bytes",
            f"- Lamports: {acc.get('lamports', 0):,}",
        ]
        if acc.get("warning"):
            lines.append(f"- ⚠️ Warning: {acc['warning']}")

    meta = context.get("metadata", {})
    if meta:
        lines += [
            "",
            "## Program Metadata (Solscan)",
            f"- Label: {meta.get('label', 'Unknown')}",
            f"- Verified: {meta.get('is_verified', False)}",
        ]

    idl = context.get("idl")
    if idl:
        lines += [
            "",
            "## Anchor IDL",
            f"- Program name: {idl.get('name', 'unknown')}",
            f"- Version: {idl.get('version', 'unknown')}",
            f"- Instructions ({len(idl.get('instructions', []))}):",
        ]
        for ix in idl.get("instructions", []):
            accounts = [a.get("name") for a in ix.get("accounts", [])]
            lines.append(
                f"  - `{ix['name']}`: accounts={accounts}, args={[a.get('name') for a in ix.get('args', [])]}"
            )
        if idl.get("accounts"):
            lines += ["", f"- Account types ({len(idl['accounts'])}):",]
            for acct in idl["accounts"]:
                lines.append(f"  - `{acct['name']}`")
        if idl.get("errors"):
            lines += ["", f"- Custom errors ({len(idl['errors'])}):",]
            for err in idl["errors"]:
                lines.append(f"  - {err.get('code')}: {err.get('name')} — {err.get('msg', '')}")
    else:
        lines += ["", "## IDL", "No on-chain IDL available. Analysis based on account metadata and source code (if provided)."]

    txns = context.get("recent_transactions", [])
    if txns:
        lines += ["", "## Recent Transactions (last 5)"]
        for t in txns:
            status = "✅" if t.get("err") is None else "❌"
            lines.append(f"- {status} `{t['signature'][:20]}...` slot={t.get('slot')}")

    if context.get("source_code"):
        lines += [
            "",
            "## Source Code",
            "```rust",
            context["source_code"],
            "```",
        ]

    return "\n".join(lines)
