# NicheBet — Autonomous Long-Tail & P2P Prediction Market Protocol

> **"P2P prediction markets on arbitrary real-world events resolved in 60s by GenLayer AI consensus with native-currency EVM escrow settlement."**

---

## 🔗 Verified Deployments & Links
- **GenLayer Explorer Contract**: [`0x25e76E732c3d80385897C0748458B6E6897dD942`](https://explorer-studio.genlayer.com/address/0x25e76E732c3d80385897C0748458B6E6897dD942)
- **Live DApp Dashboard**: [`https://genlayer-nichebet.vercel.app/`](https://genlayer-nichebet.vercel.app/)
- **GitHub Repository**: [`https://github.com/theshahali/genlayer-nichebet`](https://github.com/theshahali/genlayer-nichebet)
- **Resolution Evidence Snapshot**: [`https://genlayer-nichebet.vercel.app/demo/mock_market_resolved_yes.html`](https://genlayer-nichebet.vercel.app/demo/mock_market_resolved_yes.html)

---

## 🛡️ Production Invariants & Reviewer Safeguards (Pavel Kolosov Updates)
1. **Post-Expiry Bet Guard (`[ERR_EXPIRED_01]`)**:
   - `place_bet` audits the authoritative 24/7 UTC Atomic Clock (`timeapi.io`). Strictly reverts if the current date is past `expiry_date`.
2. **Anti-Self-Matching Invariant (`[ERR_SELF_MATCH_02]`)**:
   - Strictly blocks a user from betting against themselves on opposing sides. Revert verified on-chain.
3. **Unmatched Resolution Guard (`[ERR_UNMATCHED_01]`)**:
   - Strictly blocks resolving open, unmatched markets (`assert status == 'MARKET_MATCHED'`). Revert verified on-chain.
4. **Native-Currency Escrow & Binding Relay**:
   - Full native-currency funding on `NicheBetEscrow.sol`. `relay/NicheBetRelay.py` validates participant bindings before signing and broadcasting disbursements.
5. **Single-Round Consensus (0 Rotations)**:
   - Evaluates UTC Atomic Clock and resolution evidence in 1 parallel prompt.
