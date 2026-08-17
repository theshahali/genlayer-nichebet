# NicheBet — Autonomous Long-Tail & P2P Prediction Market Protocol

> **"Bet on anything online. Resolved in 60 seconds by decentralized AI consensus."**

An Intelligent Contract protocol built on **GenLayer** that enables trustless, micro-fee P2P prediction markets on arbitrary long-tail events (local elections, Steam gaming milestones, YouTube creator goals, niche sports, and scientific milestones) without expensive oracle feeds or centralized dispute bonds.

---

## 🌟 The Core Problem

Polymarket and Augur only support massive global markets (e.g. US Presidential Elections, Super Bowl) because spinning up a new market requires $10,000+ UMA dispute bonds and 48-hour challenge delays.

Consequently, **99.9% of real-world bets cannot exist**:
1. **Local & Regional Events**: City council zoning votes, local ballot initiatives.
2. **Creator & Gaming Milestones**: Will an indie game hit 10,000 Steam reviews? Will a YouTuber cross 1M subscribers before a deadline?
3. **Micro-Communities & Esports**: Local tournament champions, hackathon winners, and community milestones.

**NicheBet solves this by utilizing GenLayer as an autonomous micro-oracle**: any two parties can create a natural-language prediction market with an authoritative resolution URL and resolve it objectively in under 60 seconds.

---

## 🛡️ The 4 Novel Anti-Fraud Layers

```
+--------------------------------------------------------------------------------------------------+
|                                    NICHEBET PROTOCOL SHIELD                                      |
+--------------------------------------------------------------------------------------------------+
| [Layer 1: Natural Language Resolution Gate] -> Plain-English criteria + immutable target URL.    |
| [Layer 2: Grounded UTC Clock Guard]        -> Authoritative timeapi.io enforces current >= expiry|
| [Layer 3: 3-State Ambiguity & Void Guard]  -> Resolves YES, NO, or VOID_REFUND on missing data.   |
| [Layer 4: Verified Cross-Chain Relay]      -> Relays GenLayer AI verdict to EVM Escrow.          |
+--------------------------------------------------------------------------------------------------+
```

1. **Layer 1 — Natural Language Market Creation**:
   - Creator defines the question (e.g., *"Will indie game 'Hollow Rift' reach 10,000 Steam reviews before expiry?"*), exact criteria rule, resolution URL, and expiry date.
2. **Layer 2 — Authoritative 24/7/365 UTC Atomic Clock Guard**:
   - Resolution executes a grounded calendar check (`https://timeapi.io/api/time/current/zone?timeZone=UTC`) enforcing `current_utc_date >= expiry_date` (`[ERR_EXPIRY_01]`) and `clock_fresh == True` before scraping.
3. **Layer 3 — 3-State Equivalence & Ambiguity Void Guard**:
   - AI validators evaluate the evidence into strict enums: `RESOLVED_YES`, `RESOLVED_NO`, or `RESOLVED_VOID`. If the source page 404s or is indeterminate, 100% of stakes are refunded to all bettors.
4. **Layer 4 — Verified Settlement Relay & EVM Escrow**:
   - `NicheBetRelay.py` reads on-chain GenLayer verdicts and triggers `disburseWinnings` or `refundAll` on `NicheBetEscrow.sol` on Base/Arbitrum.

---

## 🏗️ Technical Architecture & Separation of Concerns

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: FRONTEND UI                     │
│    Next.js + Tailwind (Method-Matched GenLayer JSON-RPC)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ GenLayer RPC (gen_sendTransaction / gen_callView)
┌──────────────────────────────▼──────────────────────────────┐
│            LAYER 2: GENLAYER INTELLIGENT CONTRACT           │
│                     NicheBetCourt.py                        │
│   • gl.nondet.web.render() DOM scraping                     │
│   • Authoritative UTC Atomic Clock Expiry Guard             │
│   • Asymmetric Equivalence Consensus Committee              │
│   • Immutable Verdict (RESOLVED_YES / NO / VOID)            │
└──────────────────────────────┬──────────────────────────────┘
                               │ Polls Resolution Verdict (get_market)
┌──────────────────────────────▼──────────────────────────────┐
│            LAYER 3: VERIFIED SETTLEMENT RELAY               │
│                 relay/NicheBetRelay.py                      │
│   • Reads GenLayer Court resolution outcome                 │
│   • Calls disburseWinnings / refundAll on EVM Escrow        │
└──────────────────────────────┬──────────────────────────────┘
                               │ EVM Transactions
┌──────────────────────────────▼──────────────────────────────┐
│             LAYER 4: EVM P2P STAGED ESCROW                  │
│                    NicheBetEscrow.sol                       │
│   • Holds 100% USDC P2P stakes on Base/Arbitrum             │
│   • Disburses total pool to winning bettor                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📖 Project Explorer: How to Try It (Step-by-Step)

### 1. Open the Live Terminal
Open the live dashboard at `https://niche-bet-web.vercel.app/` (or run locally).

### 2. Create a P2P Market (`create_market`)
* **Question**: `"Will indie game 'Hollow Rift' reach 10,000 Steam reviews before expiry?"`
* **Resolution Criteria**: `"Outcome is YES if total Steam reviews >= 10,000 on or before expiry."`
* **Resolution URL**: `"https://niche-bet-web.vercel.app/demo/mock_market_resolved_yes.html"`
* **Expiry Date**: `"2026-08-16"`
* **Stake Amount**: `100` USDC
* **Initial Side**: `YES`
> *Returns Market ID: `"NICHE_MARKET_001"`*

### 3. Match Counter-Bet (`place_bet`)
* Call `place_bet("NICHE_MARKET_001", "NO")`.
> *Status transitions to: `MARKET_MATCHED` (Total Pool: $200 USDC).*

### 4. Trigger AI Resolution (`resolve_market`)
* Call `resolve_market("NICHE_MARKET_001")`.
> *Result: `status: "RESOLVED_YES"`, `verdict: "YES"`, `extracted_metric: "12,450 Reviews"`. Total $200 USDC pool unlocked for YES bettor.*

---

## 🚀 Running the Verified Settlement Relay

```bash
# Set environment variables
export GENLAYER_RPC="https://studio.genlayer.com/api"
export GENLAYER_COURT_ADDRESS="[DEPLOYED_CONTRACT_ADDRESS]"
export EVM_RPC_URL="https://sepolia.base.org"
export EVM_ESCROW_ADDRESS="0x3Fa9b23f81902c34918239482910394817e12a89"

# Run autonomous relay
python3 relay/NicheBetRelay.py NICHE_MARKET_001
```
