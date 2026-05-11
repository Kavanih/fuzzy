# Fuzzy Scanner — Marketplace Listing Guide

## TL;DR — How to List on Swarms Marketplace

1. **Sign in** at [swarms.world/signin](https://swarms.world/signin) with the same account that owns your `SWARMS_API_KEY`.
2. **Open the launch page**: [swarms.world/launch?type=prompt&model=tokenized&frenzy=true](https://swarms.world/launch?type=prompt&model=tokenized&frenzy=true).


3. **Choose listing type**: **Agent** (recommended — Fuzzy Scanner is a multi-agent pipeline).
4. **Fill in the form**:
   - **Name**: `Fuzzy Scanner`
   - **Tagline**: `AI-powered Solana smart contract auditor — 5-agent security pipeline`
   - **Category**: `Developer Tools` / `DeFi` / `Security`
   - **Description**: paste the contents of `README.md`
   - **Logo**: upload `logo/fuzzy_scanner.svg`
   - **System prompt / agent config**: paste contents of `fuzzy_scanner/agents.py` (5 agents) or upload the whole `fuzzy_scanner/` package
5. **Enable Frenzy Mode** (toggle ON) — this tokenizes the agent so it qualifies for the ACM Hackathon.
6. **Set price** in $SWARMS / USDC / SOL — recommended starting price: $5–$15 per audit run, or list as a tokenized asset.
7. **Click Launch** — agent will be tokenized with a `…SWRM` contract address.
8. **Share the listing URL** on Twitter / Discord with `@swarms_corp` to drive traffic.

> **Hackathon deadline**: list and tokenize **before May 27, 2026** to be eligible for the $30,000 prize pool.

---

## What Fuzzy Scanner Can Do

### 🎯 Two Input Modes

| Mode | Input | Use Case |
|------|-------|----------|
| **On-chain** | Solana program address | Audit any deployed program with one click |
| **Source code** | Rust/Anchor `.rs` file | Pre-deployment audit during development |
| **Hybrid** | Both | Maximum analysis depth |

### 🤖 5-Agent Sequential Pipeline

1. **FuzzyParser** — structural breakdown of instructions, accounts, PDAs, CPIs, token ops, authority patterns
2. **FuzzyVulnHunter** — scans for **14 vulnerability classes** (see below)
3. **FuzzyCodeQuality** — evaluates code quality across 10 dimensions, gives A–F grade
4. **FuzzyRiskAssessor** — produces 0–100 risk score, grade A–F, prioritized remediation roadmap
5. **FuzzyReportWriter** — synthesizes everything into a publication-grade Markdown audit report

### 🛡️ Vulnerability Classes Detected

- Missing signer / owner checks
- Integer overflow / underflow (unchecked arithmetic)
- PDA seed collisions
- Reentrancy via CPI
- Arbitrary CPI (calling untrusted programs)
- Account data confusion / type confusion
- Lamport drain vulnerabilities
- Flash loan attack vectors
- Privilege escalation / authority confusion
- Unvalidated account closing
- Missing rent checks
- Upgrade authority risks (no timelock / multisig)
- Oracle manipulation vectors
- Frontrunning vulnerabilities

### 🔗 On-Chain Capabilities

- Fetches program account info from Solana mainnet via Infura RPC
- Auto-derives and decodes **Anchor IDL** when present (zlib-compressed JSON)
- Pulls recent transaction signatures
- Cross-references program metadata
- Falls back gracefully when source / IDL is unavailable

### 📊 Output

- Executive summary with risk grade and score
- Findings summary table (ID / severity / status)
- Detailed findings with description, impact, exploit scenario, and remediation
- Code quality assessment per dimension
- Risk breakdown (security / operational / governance / economic)
- Prioritized remediation roadmap with effort estimates
- Integration recommendations for protocols

### 💰 Cost & Performance

- **~$0.10 per full audit** (5 agents on Swarms Cloud)
- **~30–60 seconds** per audit
- Parallel batch mode supported (10 audits in ~1 minute)

### 🎯 Target Customers

- **Protocol teams** auditing before mainnet deployment
- **DeFi LPs / investors** assessing risk before depositing
- **Security researchers** doing first-pass triage
- **Auditors** accelerating manual review baselines
- **DAOs** evaluating contracts for treasury integration

---

## Suggested Marketplace Description (copy-paste ready)  

> *   *Fuzzy Scanner** is an AI-powered Solana smart contract auditor that runs a 5-agent security pipeline against any program — by address, source code, or both. In under a minute and for ~$0.10, it produces a publication-grade audit report covering 14 vulnerability classes, code quality scores, and a prioritized remediation roadmap. Powered entirely by the Swarms multi-agent framework. Perfect for protocol teams, DeFi investors, and security researchers who need fast, structured, on-demand contract analysis.
