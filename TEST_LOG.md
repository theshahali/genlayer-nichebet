# NicheBet — GenLayer Studio Test Log & Validation Suite

This document records the test cases and execution log for **NicheBetCourt** in GenLayer Studio.

---

## 📋 Comprehensive Test Matrix

| Test Case | Description | Target DOM / Evidence | Expected Output | Expected Status |
|---|---|---|---|---|
| **TC-01** | Steam Milestone Met (12,450 >= 10,000) | `mock_market_resolved_yes.html` | Outcome: `YES`, Metric: `12,450 Reviews` | `RESOLVED_YES` |
| **TC-02** | Steam Milestone Failed (6,200 < 10,000) | `mock_market_resolved_no.html` | Outcome: `NO`, Metric: `6,200 Reviews` | `RESOLVED_NO` |
| **TC-03** | Ambiguous / Unreleased Title | `mock_market_ambiguous.html` | Outcome: `VOID`, Metric: `Unreleased` | `RESOLVED_VOID` (Refund) |

---

## 🛠️ Step-by-Step Studio Execution Template

### 1. Deploy Contract
* **Operator**: `"0x09fae1aafadb0a3b8382e43ed8d2d56ba92171c3"`

---

### 2. TC-01: Create & Resolve YES Market
1. Call `create_market`:
   * `question`: `"Will indie game 'Hollow Rift' reach 10,000 Steam reviews before expiry?"`
   * `criteria_rule`: `"Outcome is YES if total Steam reviews >= 10,000 on or before expiry."`
   * `resolution_url`: `"https://niche-bet-web.vercel.app/demo/mock_market_resolved_yes.html"`
   * `expiry_date`: `"2026-08-16"`
   * `stake_amount_usdc`: `100`
   * `side_choice`: `"YES"`
   > *Returns: `"NICHE_MARKET_001"`*
2. Call `place_bet("NICHE_MARKET_001", "NO")`
3. Call `resolve_market("NICHE_MARKET_001")`
4. Call `get_market("NICHE_MARKET_001")`:
   ```json
   {
     "id": "NICHE_MARKET_001",
     "status": "RESOLVED_YES",
     "verdict": "YES",
     "extracted_metric": "12,450 Reviews",
     "confidence_score": 95
   }
   ```
