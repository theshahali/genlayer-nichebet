# NicheBet — Autonomous Long-Tail & P2P Prediction Market Protocol

> **"The world's first subjective, long-tail prediction market protocol powered by GenLayer AI consensus and native-currency EVM Escrow settlement."**

NicheBet enables trustless P2P prediction markets on arbitrary long-tail events (local elections, gaming milestones, creator targets) resolved in 60s by GenLayer AI consensus.

---

## 🔗 Verified Deployments & Links
- **GenLayer Explorer Contract**: [`0x2f0F8E897106cd20527d3ABfa31c3f213AA774e5`](https://explorer-studio.genlayer.com/address/0x2f0F8E897106cd20527d3ABfa31c3f213AA774e5)
- **GitHub Repository**: [`https://github.com/theshahali/genlayer-nichebet`](https://github.com/theshahali/genlayer-nichebet)
- **Live DApp Dashboard**: [`https://genlayer-nichebet.vercel.app/`](https://genlayer-nichebet.vercel.app/)

---

## 🛡️ Hardened Production Invariants (Pavel Kolosov Review Compliant)

1. **Native-Currency Escrow & Binding Pre-Check (`NicheBetEscrow.sol`)**:
   - Implements enforced native-currency funding with `createAndFundEscrow` / `fundBet`.
   - `relay/NicheBetRelay.py` queries `markets(marketId)` on EVM Escrow to verify that `bettorYes` and `bettorNo` match the GenLayer record, and that `isFunded == true` before broadcasting any disbursement.
2. **Anti-Self-Matching Invariant**:
   - `place_bet` in `NicheBetCourt.py` strictly blocks bettors from taking both YES and NO sides (`assert sender != record.bettor_no` / `assert sender != record.bettor_yes`).
3. **Unmatched Resolution Guard**:
   - `resolve_market` strictly reverts if a market is not fully matched (`assert record.bettor_yes != "" and record.bettor_no != ""` and `assert record.status == "MARKET_MATCHED"`).
4. **Authoritative UTC Clock & 3-State Void Safety**:
   - 24/7 UTC Atomic Clock (`timeapi.io`) guarantees `current_utc_date >= expiry_date` in a single unified consensus pass. Missing or ambiguous evidence triggers 100% principal refunds (`RESOLVED_VOID`).
