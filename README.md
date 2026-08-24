# NicheBet — Autonomous Long-Tail & P2P Prediction Market Protocol

> **"The world's first subjective, long-tail prediction market protocol powered by GenLayer AI consensus and production EVM Escrow settlement."**

NicheBet enables trustless, micro-fee P2P prediction markets on arbitrary long-tail events (local elections, gaming milestones, creator targets) resolved in 60s by GenLayer AI consensus.

---

## 🔗 Verified Deployments & Links
- **GenLayer Explorer Contract**: [`0x69Dc02BCeF4573303F5853C274A0bd93b216f2BE`](https://explorer-studio.genlayer.com/address/0x69Dc02BCeF4573303F5853C274A0bd93b216f2BE)
- **GitHub Repository**: [`https://github.com/theshahali/genlayer-nichebet`](https://github.com/theshahali/genlayer-nichebet)
- **Live DApp Dashboard**: [`https://genlayer-nichebet.vercel.app/`](https://genlayer-nichebet.vercel.app/)

---

## 🛡️ Production Settlement Architecture & Anti-Fraud Invariants

1. **Strict Finalized Consensus Reads (Zero Local Substitutions)**:
   - Dashboard initializes in `OPEN_ACCEPTING_BETS` state and only updates upon real `gen_callView` contract state synchronization. Fails closed on RPC errors.
2. **Bound Market ID Verification**:
   - The relay strictly asserts `returned_id == expected_id` before evaluating settlement conditions, eliminating cross-market spoofing.
3. **Production Signed Web3 EVM Escrow Relay**:
   - `relay/NicheBetRelay.py` constructs, signs with ECDSA private key (`Account.sign_transaction`), broadcasts via `send_raw_transaction`, and validates on-chain transaction receipts (`receipt.status == 1`) against `NicheBetEscrow.sol`.
4. **Authoritative UTC Clock Guard**:
   - Ingests 24/7 UTC Atomic Clock (`timeapi.io`) verifying `current_utc_date >= expiry_date` prior to market resolution.
5. **3-State Void Safety**:
   - Resolves to `RESOLVED_VOID` and refunds 100% of user stakes if target evidence is missing or inaccessible.
