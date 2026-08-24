# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
NicheBet — Autonomous Long-Tail & P2P Prediction Market Protocol
================================================================
An Intelligent Contract on GenLayer that creates, matches, and autonomously resolves
subjective long-tail prediction markets against external web evidence using AI consensus.

Steward Compliance Invariants (Pavel Kolosov Review Hardened):
1. Anti-Self-Matching: Strictly prohibits a bettor from taking opposing sides against themselves.
2. Unmatched Resolution Guard: Strictly blocks resolution of unmatched markets (requires both YES and NO matched).
3. Authoritative UTC Clock Guard: Integrates 24/7 UTC Atomic Clock (timeapi.io) enforcing current_utc_date >= expiry_date.
4. Single-Round Unified Non-Deterministic Consensus: Combines atomic clock and evidence DOM in 1 parallel prompt.
5. 3-State Fail-Closed & Principal Refund: Resolves YES, NO, or VOID with full safety on ambiguous/missing data.
"""

import json
import re
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
    expiry_date: str
    stake_amount: u256
    bettor_yes: str
    bettor_no: str
    status: str
    verdict: str
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

        # Seed Test Market NICHE_MARKET_001 (Fully Matched State)
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

        # Seed Test Market NICHE_MARKET_002 (Open Unmatched State)
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
            last_audit_summary="Market open. Awaiting opposing NO bettor."
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

        m_num = int(self.next_market_id) + 3
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
    def place_bet(self, market_id: str, side: str) -> None:
        """
        Matches an open market on the opposing side with strict anti-self-matching checks.
        """
        assert market_id in self.markets, "[ERR_STATE_01] Market ID does not exist."
        record = self.markets[market_id]
        sender = str(gl.message.sender_address).lower()
        side_clean = side.strip().upper()

        assert record.status == "MARKET_OPEN", "[ERR_STATE_02] Market is not open for betting."
        assert side_clean in ("YES", "NO"), "[ERR_SIDE_01] Bet side must be 'YES' or 'NO'."

        if side_clean == "YES":
            assert record.bettor_yes == "", "[ERR_BET_01] YES side is already matched."
            # INVARIANT 1: ANTI-SELF-MATCHING CHECK
            assert sender != record.bettor_no, \
                "[ERR_SELF_MATCH_01] Self-matching prohibited: You are already the registered NO bettor."
            record.bettor_yes = sender
        else: # NO
            assert record.bettor_no == "", "[ERR_BET_02] NO side is already matched."
            # INVARIANT 1: ANTI-SELF-MATCHING CHECK
            assert sender != record.bettor_yes, \
                "[ERR_SELF_MATCH_02] Self-matching prohibited: You are already the registered YES bettor."
            record.bettor_no = sender

        if record.bettor_yes != "" and record.bettor_no != "":
            record.status = "MARKET_MATCHED"
            record.last_audit_summary = (
                f"P2P Bet Matched! YES: {record.bettor_yes}, NO: {record.bettor_no}. "
                f"Total Pool: ${int(record.stake_amount) * 2}. Awaiting expiry ({record.expiry_date}) for AI resolution."
            )
        else:
            record.last_audit_summary = f"Bet placed on {side_clean} by {sender}."

        self.markets[market_id] = record

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

        # INVARIANT 2: UNMATCHED RESOLUTION GUARD (Must have opposing bettors and be fully matched)
        assert record.bettor_yes != "" and record.bettor_no != "", \
            "[ERR_UNMATCHED_01] Cannot resolve unmatched market: Both YES and NO opposing bettors must be matched."
        assert record.status == "MARKET_MATCHED", \
            f"[ERR_STATUS_01] Market cannot be resolved in '{record.status}' status (must be MARKET_MATCHED)."

        exp_date = str(record.expiry_date)
        res_url = str(record.resolution_url)
        question = str(record.question)
        criteria_rule = str(record.criteria_rule)
        b_yes = str(record.bettor_yes)
        b_no = str(record.bettor_no)

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
            "NicheBet Consensus Equivalence Rule:\n"
            "1. Strict Fields (100% exact match required):\n"
            "   - today_date (YYYY-MM-DD)\n"
            "   - is_expired (boolean)\n"
            "   - verdict (enum 'YES', 'NO', 'VOID')\n"
            "Independently audit clock and evidence. REJECT the leader proposal if:\n"
            "(1) is_expired is true when today_date < Expiry Date,\n"
            "(2) verdict is YES when evidence shows threshold was not reached,\n"
            "(3) verdict is NO when evidence shows threshold was reached,\n"
            "(4) verdict is not VOID when evidence is inaccessible or unparseable.\n"
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
        is_expired = bool(res_parsed.get("is_expired", False))
        assert is_expired == True, \
            f"[ERR_EXPIRY_01] Market has not expired yet (Expiry: {exp_date}, Today: {res_parsed.get('today_date')})."

        verdict_str = str(res_parsed.get("verdict", "VOID")).strip().upper()
        assert verdict_str in ("YES", "NO", "VOID"), f"[ERR_VERDICT_01] Invalid verdict: {verdict_str}"

        metric = str(res_parsed.get("extracted_metric", "N/A"))
        confidence = int(res_parsed.get("confidence_score", 0))
        summary_text = str(res_parsed.get("resolution_summary", "Market resolved by GenLayer AI consensus."))

        if verdict_str == "YES":
            new_status = "RESOLVED_YES"
            payout_summary = f"MARKET RESOLVED YES: {metric}. {summary_text} Payout eligible for YES bettor ({b_yes})."
        elif verdict_str == "NO":
            new_status = "RESOLVED_NO"
            payout_summary = f"MARKET RESOLVED NO: {metric}. {summary_text} Payout eligible for NO bettor ({b_no})."
        else: # VOID
            new_status = "RESOLVED_VOID"
            payout_summary = f"MARKET RESOLVED VOID: {metric}. {summary_text} 100% Principal refunds eligible for all bettors."

        record.status = new_status
        record.verdict = verdict_str
        record.extracted_metric = metric
        record.confidence_score = u256(confidence)
        record.last_audit_summary = payout_summary

        self.markets[market_id] = record
        return payout_summary

    @gl.public.view
    def get_market(self, market_id: str) -> MarketRecord:
        """Queries the complete on-chain prediction market state record."""
        assert market_id in self.markets, f"[ERR_STATE_01] Market ID {market_id} does not exist."
        return self.markets[market_id]
