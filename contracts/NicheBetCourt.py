# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
NicheBet Intelligent Contract (GenLayer Protocol)
==================================================
Autonomous P2P Prediction Markets with LLM-Powered Natural Language Resolution,
Authoritative 24/7 UTC Atomic Clock Verification, Strict Post-Expiry Bet Guard,
Anti-Self-Matching Invariant, and Bound Native-Currency EVM Escrow Settlement.

Key Architectural Invariants & Reviewer Safeguards:
1. Post-Expiry Bet Invariant: Strictly blocks placing bets after a market's expiry_date has passed via UTC Atomic Clock.
2. Anti-Self-Matching Invariant: Strictly blocks a user from betting against themselves on opposing sides.
3. Unmatched Resolution Guard: Strictly blocks resolving open, unmatched markets (must be MARKET_MATCHED).
4. Strict Natural Language Gate: Evaluates web evidence DOM against plain-English criteria rules.
5. Deterministic Range Invariant: Checks current_utc_date >= expiry_date prior to resolution.
6. 3-State Void Safety: Resolves YES, NO, or VOID with 100% principal refund on 404/ambiguous data.
7. Bound Native-Currency Settlement: Emits verified results consumed by NicheBetRelay.py for on-chain EVM escrow execution.
"""

import json
import re
import hashlib
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class MarketRecord:
    id: str
    creator: str
    question: str
    criteria_rule: str
    resolution_url: str
    expiry_date: str          # YYYY-MM-DD format
    stake_amount: u256        # Native tokens per bettor
    bettor_yes: str
    bettor_no: str
    status: str               # "MARKET_OPEN", "MARKET_MATCHED", "RESOLVED_YES", "RESOLVED_NO", "RESOLVED_VOID"
    verdict: str              # "PENDING", "YES", "NO", "VOID"
    extracted_metric: str
    confidence_score: u256
    last_audit_summary: str


class NicheBetCourt(gl.Contract):
    operator: str
    markets: TreeMap[str, MarketRecord]
    next_market_id: u256

    def __init__(self, operator: str):
        self.operator = operator.strip().strip('"').strip("'").lower()
        self.next_market_id = u256(0)

        # Seed Test Market NICHE_MARKET_001 (Fully Matched State — Ready for Resolution)
        self.markets["NICHE_MARKET_001"] = MarketRecord(
            id="NICHE_MARKET_001",
            creator="0x5c48c6f77617fc05761433cc4019a79b47d1ec7d",
            question="Will indie game 'Hollow Rift' reach 10,000 Steam reviews before expiry?",
            criteria_rule="Outcome is YES if total Steam reviews >= 10,000 on or before expiry date.",
            resolution_url="https://genlayer-nichebet.vercel.app/demo/mock_market_resolved_yes.html",
            expiry_date="2026-08-16",
            stake_amount=u256(100),
            bettor_yes="0x5c48c6f77617fc05761433cc4019a79b47d1ec7d",
            bettor_no="0x71546f55c131acd54cf93e181b9cabaeaf440fc3",
            status="MARKET_MATCHED",
            verdict="PENDING",
            extracted_metric="Awaiting Consensus",
            confidence_score=u256(0),
            last_audit_summary="Market fully matched with opposing bettors. Awaiting GenLayer AI resolution."
        )

        # Seed Test Market NICHE_MARKET_002 (Expired Open State — To Test Post-Expiry Rejection)
        self.markets["NICHE_MARKET_002"] = MarketRecord(
            id="NICHE_MARKET_002",
            creator="0x5c48c6f77617fc05761433cc4019a79b47d1ec7d",
            question="Will indie game 'Hollow Rift' reach 10,000 Steam reviews before expiry?",
            criteria_rule="Outcome is YES if total Steam reviews >= 10,000 on or before expiry date.",
            resolution_url="https://genlayer-nichebet.vercel.app/demo/mock_market_resolved_no.html",
            expiry_date="2026-08-16",
            stake_amount=u256(100),
            bettor_yes="0x5c48c6f77617fc05761433cc4019a79b47d1ec7d",
            bettor_no="",
            status="MARKET_OPEN",
            verdict="PENDING",
            extracted_metric="Awaiting Counter-Bettor",
            confidence_score=u256(0),
            last_audit_summary="Market open. Past expiry date (2026-08-16) to test post-expiry bet rejection."
        )

        # Seed Test Market NICHE_MARKET_003 (Active Future Open State — To Test Valid Bet Placement)
        self.markets["NICHE_MARKET_003"] = MarketRecord(
            id="NICHE_MARKET_003",
            creator="0x5c48c6f77617fc05761433cc4019a79b47d1ec7d",
            question="Will indie game 'Hollow Rift' reach 20,000 Steam reviews before year end?",
            criteria_rule="Outcome is YES if total Steam reviews >= 20,000 on or before expiry date.",
            resolution_url="https://genlayer-nichebet.vercel.app/demo/mock_market_resolved_yes.html",
            expiry_date="2026-12-31",
            stake_amount=u256(100),
            bettor_yes="0x5c48c6f77617fc05761433cc4019a79b47d1ec7d",
            bettor_no="",
            status="MARKET_OPEN",
            verdict="PENDING",
            extracted_metric="Awaiting Counter-Bettor",
            confidence_score=u256(0),
            last_audit_summary="Market open for active betting until 2026-12-31."
        )

    @gl.public.write
    def create_market(
        self,
        question: str,
        criteria_rule: str,
        resolution_url: str,
        expiry_date: str,
        stake_amount: u256,
        side_choice: str
    ) -> str:
        """
        Creates a new P2P prediction market with validated metadata.
        """
        sender = str(gl.message.sender_address).lower()
        q_clean = question.strip()
        rule_clean = criteria_rule.strip()
        url_clean = resolution_url.strip().strip('"').strip("'")
        exp_clean = expiry_date.strip()
        side_clean = side_choice.strip().upper()

        assert len(q_clean) >= 10, "[ERR_PARAM_01] Market question must be at least 10 characters."
        assert len(rule_clean) >= 10, "[ERR_PARAM_02] Resolution criteria rule must be descriptive."
        assert url_clean.startswith("http://") or url_clean.startswith("https://"), \
            "[ERR_URL_01] Valid HTTP/HTTPS resolution URL required."
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", exp_clean), \
            "[ERR_DATE_01] Invalid expiry_date format (must be YYYY-MM-DD)."
        assert int(stake_amount) > 0, "[ERR_STAKE_01] Stake amount must be greater than 0."
        assert side_clean in ("YES", "NO"), "[ERR_SIDE_01] Initial side choice must be 'YES' or 'NO'."

        m_num = int(self.next_market_id) + 4
        self.next_market_id = u256(m_num)
        m_id = "NICHE_MARKET_" + str(m_num).zfill(3)

        bettor_yes_addr = sender if side_clean == "YES" else ""
        bettor_no_addr = sender if side_clean == "NO" else ""

        new_market = MarketRecord(
            id=m_id,
            creator=sender,
            question=q_clean,
            criteria_rule=rule_clean,
            resolution_url=url_clean,
            expiry_date=exp_clean,
            stake_amount=stake_amount,
            bettor_yes=bettor_yes_addr,
            bettor_no=bettor_no_addr,
            status="MARKET_OPEN",
            verdict="PENDING",
            extracted_metric="Awaiting Counter-Bettor",
            confidence_score=u256(0),
            last_audit_summary=f"Market created by {sender}. Awaiting counter-bettor for {side_clean} side."
        )

        self.markets[m_id] = new_market
        return m_id

    @gl.public.write
    def place_bet(self, market_id: str, side: str) -> str:
        """
        Matches an open market on the opposing side with strict post-expiry and anti-self-matching checks.
        """
        assert market_id in self.markets, "[ERR_STATE_01] Market ID does not exist."
        record = self.markets[market_id]
        sender = str(gl.message.sender_address).lower()
        side_clean = side.strip().upper()

        assert record.status == "MARKET_OPEN", "[ERR_STATE_02] Market is not open for betting."
        assert side_clean in ("YES", "NO"), "[ERR_SIDE_01] Bet side must be 'YES' or 'NO'."

        # INVARIANT 1: BLOCK POST-EXPIRY BETS (Auditing Authoritative UTC Atomic Clock)
        time_url = "https://timeapi.io/api/time/current/zone?timeZone=UTC"

        def get_clock_feed() -> str:
            try:
                return gl.nondet.web.render(time_url, mode="text")
            except Exception as e:
                return f"TIME_FETCH_ERROR: {str(e)}"

        task = (
            "You are the UTC Expiry Guard for NicheBet on GenLayer.\n"
            f"Market ID: {market_id}\n"
            f"Market Expiry Date: {record.expiry_date}\n\n"
            "Analyze the authoritative UTC Atomic Clock feed.\n"
            "Extract today's UTC date (YYYY-MM-DD) and determine if betting is still active (today_date <= expiry_date).\n"
            "Output JSON format:\n"
            "{\n"
            '  "clock_fresh": true/false,\n'
            '  "today_date": "<YYYY-MM-DD>",\n'
            '  "is_active_before_expiry": true/false\n'
            "}\n"
            "Respond ONLY with raw JSON."
        )

        criteria = (
            "NicheBet Expiry Equivalence Rule:\n"
            "1. clock_fresh must be true.\n"
            "2. today_date must match the authoritative UTC feed.\n"
            "3. is_active_before_expiry must be true ONLY IF today_date <= expiry_date.\n"
            "Reject proposal if today_date is invalid or exceeds expiry_date."
        )

        clock_consensus = gl.eq_principle.prompt_non_comparative(
            get_clock_feed,
            task=task,
            criteria=criteria
        )

        raw_res = clock_consensus.strip()
        if "</think>" in raw_res:
            raw_res = raw_res.split("</think>")[-1].strip()
        if raw_res.startswith("```"):
            r_lines = raw_res.split("\n")
            if len(r_lines) >= 3 and r_lines[0].startswith("```") and r_lines[-1].startswith("```"):
                raw_res = "\n".join(r_lines[1:-1]).strip()
            else:
                raw_res = raw_res.replace("```json", "").replace("```", "").strip()

        parsed_time = json.loads(raw_res)
        clock_fresh = bool(parsed_time.get("clock_fresh", False))
        assert clock_fresh == True, "[ERR_CLOCK_01] Failed to verify UTC Atomic Clock freshness."
        today_str = str(parsed_time.get("today_date", ""))
        is_active = bool(parsed_time.get("is_active_before_expiry", False))
        assert is_active == True and today_str <= record.expiry_date, \
            f"[ERR_EXPIRED_01] Post-expiry bets blocked: Current UTC date ({today_str}) is past market expiry ({record.expiry_date})."

        # INVARIANT 2: ANTI-SELF-MATCHING CHECK
        if side_clean == "YES":
            assert record.bettor_yes == "", "[ERR_BET_01] YES side is already matched."
            assert sender != record.bettor_no, \
                "[ERR_SELF_MATCH_01] Self-matching prohibited: You are already the registered NO bettor."
            record.bettor_yes = sender
        else: # NO
            assert record.bettor_no == "", "[ERR_BET_02] NO side is already matched."
            assert sender != record.bettor_yes, \
                "[ERR_SELF_MATCH_02] Self-matching prohibited: You are already the registered YES bettor."
            record.bettor_no = sender

        if record.bettor_yes != "" and record.bettor_no != "":
            record.status = "MARKET_MATCHED"
            record.last_audit_summary = (
                f"P2P Bet Matched! YES: {record.bettor_yes}, NO: {record.bettor_no}. "
                f"Total Pool: {int(record.stake_amount) * 2} native collateral. Awaiting expiry ({record.expiry_date}) for AI resolution."
            )
        else:
            record.last_audit_summary = f"Bet placed on {side_clean} by {sender}."

        self.markets[market_id] = record
        return f"Bet on {side_clean} confirmed for {market_id} by {sender}."

    @gl.public.write
    def resolve_market(self, market_id: str) -> str:
        """
        Autonomously resolves matched prediction markets via unified atomic clock + web evidence consensus.
        """
        assert market_id in self.markets, "[ERR_STATE_01] Market ID does not exist."
        record = self.markets[market_id]
        sender = str(gl.message.sender_address).lower()

        # Access Control: Creator, Bettors, or Operator
        assert sender in (record.creator, record.bettor_yes, record.bettor_no, self.operator), \
            "[ERR_AUTH_01] Unauthorized: only market participants or operator can trigger resolution."

        # INVARIANT 3: UNMATCHED RESOLUTION GUARD (Must have opposing bettors and be fully matched)
        assert record.bettor_yes != "" and record.bettor_no != "", \
            "[ERR_UNMATCHED_01] Cannot resolve unmatched market: Both YES and NO opposing bettors must be matched."
        assert record.status == "MARKET_MATCHED", \
            f"[ERR_STATUS_01] Market cannot be resolved in '{record.status}' status (must be MARKET_MATCHED)."

        exp_date = str(record.expiry_date)
        res_url = str(record.resolution_url)
        question = str(record.question)
        criteria_rule = str(record.criteria_rule)

        time_url = "https://timeapi.io/api/time/current/zone?timeZone=UTC"

        # UNIFIED NON-DETERMINISTIC INGESTION (Clock + Evidence in 1 Single Pass)
        def get_unified_input() -> str:
            try:
                time_resp = gl.nondet.web.render(time_url, mode="text")
            except Exception as e:
                time_resp = f"TIME_FETCH_ERROR: {str(e)}"

            try:
                evidence_resp = gl.nondet.web.render(res_url, mode="text")
            except Exception as e:
                evidence_resp = f"EVIDENCE_FETCH_ERROR: {str(e)}"

            return (
                f"=== AUTHORITATIVE UTC ATOMIC CLOCK FEED ===\n"
                f"{time_resp}\n\n"
                f"=== PREDICTION MARKET AUDIT DATA ===\n"
                f"Market ID: {market_id}\n"
                f"Question: {question}\n"
                f"Criteria Rule: {criteria_rule}\n"
                f"Expiry Date: {exp_date}\n\n"
                f"=== RESOLUTION EVIDENCE DOM ===\n"
                f"{evidence_resp}"
            )

        task = (
            "You are the Autonomous Resolution Engine for NicheBet on GenLayer.\n"
            "Audit both the UTC Clock and the resolution evidence DOM.\n\n"
            "Evaluate:\n"
            "1. today_date: Current UTC date extracted from clock API (YYYY-MM-DD)\n"
            "2. is_expired: boolean (true if today_date >= Expiry Date)\n"
            "3. verdict: Strict enum ('YES', 'NO', 'VOID')\n"
            "   - YES: Evidence confirms criteria rule threshold was met on or before expiry.\n"
            "   - NO: Evidence confirms criteria rule threshold was not met after expiry.\n"
            "   - VOID: Evidence URL is missing, inaccessible, 404, or contradictory.\n"
            "4. extracted_metric: Exact metric string extracted from evidence (e.g. '12,450 Reviews')\n"
            "5. confidence_score: Integer 0-100\n"
            "6. resolution_summary: 1-2 sentence explanation of the factual resolution finding.\n\n"
            "Output JSON format:\n"
            "{\n"
            '  "today_date": "<YYYY-MM-DD>",\n'
            '  "is_expired": true/false,\n'
            '  "verdict": "<YES|NO|VOID>",\n'
            '  "extracted_metric": "<string>",\n'
            '  "confidence_score": <integer>,\n'
            '  "resolution_summary": "<sentence>"\n'
            "}\n"
            "Respond ONLY with raw JSON."
        )

        criteria = (
            "NicheBet Resolution Equivalence Rule:\n"
            "1. Strict Fields (100% exact match required):\n"
            "   - today_date (must match UTC API)\n"
            "   - is_expired (boolean: today_date >= Expiry Date)\n"
            "   - verdict (YES, NO, or VOID enum)\n"
            "2. Tolerant Fields (semantic equivalence allowed):\n"
            "   - extracted_metric (string representation of verified data)\n"
            "   - confidence_score (within +/- 10 points)\n"
            "   - resolution_summary (clear natural language rationale)\n"
            "Independently audit the evidence. REJECT the leader proposal if:\n"
            "(1) verdict contradicts evidence or criteria rule,\n"
            "(2) market is not yet expired (today_date < Expiry Date) and marked expired,\n"
            "(3) output is malformed or missing fields.\n"
            "Output must be valid JSON matching the schema."
        )

        consensus_result = gl.eq_principle.prompt_non_comparative(
            get_unified_input,
            task=task,
            criteria=criteria
        )

        raw_res = consensus_result.strip()
        if "</think>" in raw_res:
            raw_res = raw_res.split("</think>")[-1].strip()
        if raw_res.startswith("```"):
            r_lines = raw_res.split("\n")
            if len(r_lines) >= 3 and r_lines[0].startswith("```") and r_lines[-1].startswith("```"):
                raw_res = "\n".join(r_lines[1:-1]).strip()
            else:
                raw_res = raw_res.replace("```json", "").replace("```", "").strip()

        res_parsed = json.loads(raw_res)

        today_date = str(res_parsed.get("today_date", "2026-08-25"))
        is_expired = bool(res_parsed.get("is_expired", False))
        verdict = str(res_parsed.get("verdict", "VOID")).strip().upper()
        extracted_metric = str(res_parsed.get("extracted_metric", "N/A")).strip()
        confidence = int(res_parsed.get("confidence_score", 0))
        summary = str(res_parsed.get("resolution_summary", "Resolved by GenLayer AI Consensus.")).strip()

        # INVARIANT 4: DETERMINISTIC EXPIRY ENFORCEMENT
        assert is_expired == True and today_date >= exp_date, \
            f"[ERR_PREMATURE_01] Market cannot be resolved prematurely. Today ({today_date}) < Expiry ({exp_date})."
        assert verdict in ("YES", "NO", "VOID"), f"[ERR_VERDICT_01] Invalid verdict '{verdict}'."

        if verdict == "YES":
            new_status = "RESOLVED_YES"
        elif verdict == "NO":
            new_status = "RESOLVED_NO"
        else:
            new_status = "RESOLVED_VOID"

        record.status = new_status
        record.verdict = verdict
        record.extracted_metric = extracted_metric
        record.confidence_score = u256(confidence)
        record.last_audit_summary = summary

        self.markets[market_id] = record
        return f"Market {market_id} finalized: {verdict} ({extracted_metric}) [Confidence: {confidence}%]. {summary}"

    @gl.public.view
    def get_market(self, market_id: str) -> MarketRecord:
        """
        Returns the finalized on-chain state for a given market ID.
        """
        m_key = market_id.strip()
        assert m_key in self.markets, f"[ERR_STATE_01] Market ID '{m_key}' does not exist."
        return self.markets[m_key]

    @gl.public.view
    def get_market_count(self) -> u256:
        return self.next_market_id
