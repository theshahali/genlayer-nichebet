# NicheBet On-Chain Test Log & Verification Matrix

Contract: `0x25e76E732c3d80385897C0748458B6E6897dD942`
Network: GenLayer Studio Devnet

## Test Matrix:

### 1. Test Case 01: Autonomous Resolution (YES Verdict)
- **Method**: `resolve_market("NICHE_MARKET_001")`
- **Result**: `SUCCESS`
- **Verdict**: `YES`
- **Extracted Metric**: `12,450 Reviews`
- **Confidence**: `100%`
- **Payout**: Disbursed 200 Native Collateral to winner.

### 2. Test Case 02: Post-Expiry Bet Guard
- **Method**: `place_bet("NICHE_MARKET_002", "NO")` on expired market (expiry: `2026-08-16`)
- **Result**: `REVERTED` with `[ERR_EXPIRED_01] Post-expiry bets blocked: Current UTC date is past market expiry.`

### 3. Test Case 03: Anti-Self-Matching Invariant
- **Method**: `place_bet("NICHE_MARKET_003", "NO")` called by creator/bettor_yes (`0x5c48...`)
- **Result**: `REVERTED` with `[ERR_SELF_MATCH_02] Self-matching prohibited: You are already the registered YES bettor.`

### 4. Test Case 04: Unmatched Resolution Guard
- **Method**: `resolve_market("NICHE_MARKET_003")`
- **Result**: `REVERTED` with `[ERR_UNMATCHED_01] Cannot resolve unmatched market: Both YES and NO opposing bettors must be matched.`
