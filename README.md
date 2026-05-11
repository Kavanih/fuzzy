# 🔍 Fuzzy Scanner — Solana Smart Contract Auditor

> **AI-powered Solana smart contract security auditor built on the Swarms framework.**
> Audit any Solana program by address or source code in seconds.

---

## What It Does

Fuzzy Scanner runs a **5-stage multi-agent audit pipeline** against any Solana smart contract:

| Stage | Agent | Output |
|---|---|---|
| 1 | **Parser** | Structural breakdown — instructions, accounts, PDAs, CPIs |
| 2 | **Vuln Hunter** | Severity-graded vulnerability findings (14 vuln classes) |
| 3 | **Code Quality** | Quality scores across 10 dimensions |
| 4 | **Risk Assessor** | Risk score (0–100), grade (A–F), remediation roadmap |
| 5 | **Report Writer** | Full professional audit report in Markdown |

### Two Input Modes

1. **Program Address** — paste any Solana program address and Fuzzy Scanner fetches on-chain data (account info, Anchor IDL if available, recent transactions) and audits it automatically.
2. **Source Code** — paste or load a `.rs` Rust/Anchor file for deep static analysis.
3. **Both** — combine address + source for maximum coverage.

---

## Vulnerabilities Detected

- Missing signer / owner checks
- Integer overflow / underflow
- PDA seed collisions
- Reentrancy via CPI
- Arbitrary CPI
- Account data confusion / type confusion
- Lamport drain vulnerabilities
- Flash loan attack vectors
- Privilege escalation
- Unsafe account closing
- Missing rent checks
- Upgrade authority risks
- Oracle manipulation vectors
- And more...

---

## Quick Start

### Install

```bash
pip install -U swarms python-dotenv httpx solders base58
```

### Configure

```bash
# .env
OPENAI_API_KEY=sk-...
```

### Run

```bash
# Audit by program address
python -m fuzzy_scanner.main --address <PROGRAM_ADDRESS>

# Audit by source code
python -m fuzzy_scanner.main --source ./my_contract/src/lib.rs

# Both + save report
python -m fuzzy_scanner.main --address <ADDR> --source ./lib.rs --output report.md

# Use devnet
python -m fuzzy_scanner.main --address <ADDR> --network devnet
```

---

## Example Output

```
Risk Grade: C  |  Risk Score: 58/100
Findings: 1 CRITICAL  |  2 HIGH  |  3 MEDIUM  |  4 LOW

CRITICAL — VUL-001: Missing Signer Check on `withdraw` instruction
HIGH     — VUL-002: Unchecked arithmetic in `calculate_reward`
...
```

---

## Use Cases

- **Protocol teams**: Audit your own contracts before mainnet deployment
- **Investors/LPs**: Quickly assess risk before depositing into a new protocol
- **Security researchers**: Automated first-pass triage of on-chain programs
- **Auditors**: Accelerate manual review with AI-generated findings baseline

---

## Built With

- [Swarms](https://swarms.world) — multi-agent orchestration framework
- [OpenAI GPT-4o](https://openai.com) — powering all audit agents
- [Solana RPC](https://docs.solana.com/api/http) — on-chain data fetching
- [Anchor IDL](https://www.anchor-lang.com) — structured program interface decoding

---

## License

MIT — built for the [Swarms ACM Hackathon](https://docs.swarms.ai/docs/marketplace/acm-hackathon)
