# NicheBet — Protocol Architecture & System Design

## 1. Asymmetric Equivalence Principle Design

NicheBet partitions consensus verification into **Strict State-Driving Enums** and **Bounded Fuzzy Metrics**:

```
Consensus Payload
├── Strict Fields (100% Exact Match Required):
│   ├── outcome: enum ("YES", "NO", "VOID")
│   └── clock_fresh: bool (Must be live atomic UTC clock)
└── Bounded Fuzzy Fields (Allowed Variance):
    ├── confidence_score: int (±10 points tolerance)
    └── extracted_metric: string (Semantic descriptive match)
```

---

## 2. Threat Model & Exploit Mitigation

| Threat Vector | Exploit Attempt | How NicheBet Mitigates It |
|---|---|---|
| **Premature Resolution Attack** | Bettor attempts to resolve the market early while an outcome looks favorable. | Authoritative UTC Atomic Clock check runs first (`timeapi.io`). Rejects if `today_date < expiry_date` (`[ERR_EXPIRY_01]`). |
| **Missing / 404 URL Griefing** | Creator supplies a broken link or the target site goes offline. | 3-state resolution guarantees `RESOLVED_VOID` on missing data, refunding 100% of stakes to all bettors. |
| **Counter-Bettor Frontrunning** | Malicious party sees early outcome and places opposite bet. | Expiry date is fixed on creation; bets cannot be placed once expired. |
| **Centralized Custody Risk** | Contract or frontend holds private keys. | Zero custody: GenLayer operates purely as a decision oracle; funds stay locked in EVM escrow (`NicheBetEscrow.sol`). |

---

## 3. Anti-Hallucination & Deterministic Separation

```
Web Evidence DOM + UTC Clock Feed
            │
            ▼ (Non-Deterministic AI Consensus)
LLM Extraction Node (Outcome & Metric Extraction)
            │
            ▼ (Deterministic Smart Contract Logic)
Python Smart Contract Logic (Threshold enforcement, State transition, Winner assignment)
            │
            ▼
On-Chain Immutable Verdict (RESOLVED_YES / RESOLVED_NO / RESOLVED_VOID)
```
