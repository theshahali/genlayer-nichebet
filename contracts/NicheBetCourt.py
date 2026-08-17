# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
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
    stake_amount_usdc: u256
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

    @gl.public.write
    def create_market(
        self,
        question: str,
        criteria_rule: str,
        resolution_url: str,
        expiry_date: str,
        stake_amount_usdc: u256,
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
        assert int(stake_amount_usdc) > 0, "[ERR_STAKE_01] Stake amount must be greater than 0."
        assert side_clean in ("YES", "NO"), "[ERR_SIDE_01] Initial side choice must be 'YES' or 'NO'."

        m_num = int(self.next_market_id) + 1
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
            stake_amount_usdc=stake_amount_usdc,
            bettor_yes=bettor_yes_addr,
            bettor_no=bettor_no_addr,
            status="MARKET_OPEN",
            verdict="PENDING",
            extracted_metric="N/A",
            confidence_score=u256(0),
            last_audit_summary=f"Market created by {sender}. Awaiting counter-bettor for {side_clean} side."
        )

        self.markets[m_id] = new_market
        return m_id

    @gl.public.write
    def place_bet(self, market_id: str, side: str) -> None:
        assert market_id in self.markets, "[ERR_STATE_01] Market ID does not exist."
        record = self.markets[market_id]
        sender = str(gl.message.sender_address).lower()
        side_clean = side.strip().upper()

        assert record.status in ("MARKET_OPEN", "MARKET_MATCHED"), \
            "[ERR_STATE_02] Market is not open for betting."
        assert side_clean in ("YES", "NO"), "[ERR_SIDE_01] Bet side must be 'YES' or 'NO'."

        if side_clean == "YES":
            assert record.bettor_yes == "", "[ERR_BET_01] YES side is already matched."
            record.bettor_yes = sender
        else:
            assert record.bettor_no == "", "[ERR_BET_02] NO side is already matched."
            record.bettor_no = sender

        if record.bettor_yes != "" and record.bettor_no != "":
            record.status = "MARKET_MATCHED"
            record.last_audit_summary = (
                f"P2P Bet Matched! YES: {record.bettor_yes}, NO: {record.bettor_no}. "
                f"Total Pool: ${int(record.stake_amount_usdc) * 2} USDC. Awaiting expiry ({record.expiry_date}) for AI resolution."
            )
        else:
            record.last_audit_summary = f"Bet placed on {side_clean} by {sender}."

        self.markets[market_id] = record

    @gl.public.write
    def resolve_market(self, market_id: str) -> str:
        assert market_id in self.markets, "[ERR_STATE_01] Market ID does not exist."
        record = self.markets[market_id]
        sender = str(gl.message.sender_address).lower()

        # Access Control: Creator, Bettors, or Operator
        assert sender in (record.creator, record.bettor_yes, record.bettor_no, self.operator), \
            "[ERR_AUTH_01] Unauthorized: only market participants or operator can trigger resolution."

        assert record.status in ("MARKET_OPEN", "MARKET_MATCHED"), \
            "[ERR_STATE_03] Market is already resolved or cancelled."

        exp_date = record.expiry_date
        res_url = record.resolution_url
        question = record.question
        criteria_rule = record.criteria_rule

        # STEP 1: AUTHORITATIVE UTC CLOCK & EXPIRY GUARD
        time_url = "https://timeapi.io/api/time/current/zone?timeZone=UTC"

        def get_time_input() -> str:
            time_resp = gl.nondet.web.render(time_url, mode="text")
            return (
                f"=== AUTHORITATIVE UTC ATOMIC CLOCK FEED ===\n"
                f"{time_resp}\n\n"
                f"Market Expiry Date: {exp_date}"
            )

        time_task = (
            "You are an authoritative calendar clock auditor.\n"
            "Parse the live UTC Clock API response.\n"
            "Extract today's UTC date (YYYY-MM-DD format).\n"
            "Determine if today_date >= expiry_date.\n\n"
            "Output JSON format:\n"
            "{\n"
            '  "today_date": "<YYYY-MM-DD>",\n'
            '  "is_expired": true/false,\n'
            '  "clock_fresh": true/false\n'
            "}\n"
            "Respond ONLY with raw JSON."
        )

        time_criteria = (
            "Independently parse the live UTC Clock API JSON to extract today's date (YYYY-MM-DD). "
            "Compare today_date against expiry_date using standard ISO string comparison. "
            "REJECT the leader if: "
            "(1) today_date does not match the live UTC date in the API response, "
            "(2) is_expired boolean is inconsistent with (today_date >= expiry_date) in EITHER direction, or "
            "(3) clock_fresh is marked true when the clock API response is missing or unparseable."
        )

        time_result = gl.eq_principle.prompt_non_comparative(
            get_time_input,
            task=time_task,
            criteria=time_criteria
        )

        raw_time = time_result.strip()
        if "</think>" in raw_time:
            raw_time = raw_time.split("</think>")[-1].strip()
        if raw_time.startswith("```"):
            t_lines = raw_time.split("\n")
            if len(t_lines) >= 3 and t_lines[0].startswith("```") and t_lines[-1].startswith("```"):
                raw_time = "\n".join(t_lines[1:-1]).strip()
            else:
                raw_time = raw_time.replace("```json", "").replace("```", "").strip()

        time_parsed = json.loads(raw_time)
        is_expired = bool(time_parsed.get("is_expired", False))
        clock_fresh = bool(time_parsed.get("clock_fresh", False))
        today_str = str(time_parsed.get("today_date", ""))

        assert clock_fresh == True, "[ERR_CLOCK_01] Failed to retrieve fresh authoritative UTC clock."
        assert is_expired == True, \
            f"[ERR_EXPIRY_01] Market cannot be resolved before expiry date ({today_str} < {exp_date})."

        # STEP 2: NATURAL LANGUAGE WEB EVIDENCE RESOLUTION
        def get_resolution_input() -> str:
            try:
                web_data = gl.nondet.web.render(res_url, mode="text")
            except Exception as e:
                web_data = f"DATA_FETCH_ERROR: {str(e)}"

            return (
                f"=== NICHEBET PREDICTION MARKET RESOLUTION ===\n"
                f"Market ID: {record.id}\n"
                f"Question: \"{question}\"\n"
                f"Resolution Rule Criteria: \"{criteria_rule}\"\n"
                f"Resolution URL: \"{res_url}\"\n"
                f"Expiry Date: \"{exp_date}\"\n\n"
                f"=== RESOLUTION EVIDENCE DOM ===\n"
                f"{web_data}"
            )

        task = (
            "You are an impartial Prediction Market Resolution Judge.\n"
            "Audit the provided web evidence against the market question and resolution criteria.\n\n"
            "Determine the outcome:\n"
            "- YES: The condition described in the criteria was explicitly satisfied/achieved on or before expiry.\n"
            "- NO: The condition was NOT satisfied, threshold was not met, or negative outcome confirmed.\n"
            "- VOID: Target data is missing, page is 404/indeterminate, or source is irreparably ambiguous.\n\n"
            "Extract:\n"
            "1. outcome: Strict enum string ('YES', 'NO', 'VOID')\n"
            "2. extracted_metric: String description of key number or fact extracted (e.g. '12,450 Reviews', '6,200 Reviews', 'Unreleased')\n"
            "3. confidence_score: Integer 0 to 100\n"
            "4. reasoning: Concise 1-2 sentence explanation\n\n"
            "Output JSON format:\n"
            "{\n"
            '  "outcome": "<YES|NO|VOID>",\n'
            '  "extracted_metric": "<string>",\n'
            '  "confidence_score": <int 0-100>,\n'
            '  "reasoning": "<sentence>"\n'
            "}\n"
            "Respond ONLY with raw JSON."
        )

        criteria = (
            "NicheBet Market Resolution Equivalence Rule:\n"
            "1. Strict Fields (100% exact match required):\n"
            "   - outcome (enum 'YES', 'NO', 'VOID')\n"
            "2. Bounded Fuzzy Fields:\n"
            "   - confidence_score (+-10 points tolerance)\n"
            "Independently audit the web evidence against the criteria rule. REJECT the leader proposal if:\n"
            "(1) outcome is marked YES when the threshold metric was not achieved,\n"
            "(2) outcome is marked NO when the evidence confirms the condition occurred,\n"
            "(3) outcome is not marked VOID when the page is 404, unreleased, or missing.\n"
            "Output must be valid JSON matching the schema."
        )

        consensus_result = gl.eq_principle.prompt_non_comparative(
            get_resolution_input,
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
        outcome = str(res_parsed.get("outcome", "VOID")).strip().upper()
        metric = str(res_parsed.get("extracted_metric", "N/A")).strip()
        conf = int(res_parsed.get("confidence_score", 90))
        reasoning = str(res_parsed.get("reasoning", ""))

        if outcome == "YES":
            status = "RESOLVED_YES"
            verdict = "YES"
            summary = f"MARKET RESOLVED YES: {metric}. {reasoning} Payout eligible for YES bettor ({record.bettor_yes})."
        elif outcome == "NO":
            status = "RESOLVED_NO"
            verdict = "NO"
            summary = f"MARKET RESOLVED NO: {metric}. {reasoning} Payout eligible for NO bettor ({record.bettor_no})."
        else:
            status = "RESOLVED_VOID"
            verdict = "VOID"
            summary = f"MARKET VOIDED / REFUNDED: {metric}. {reasoning} 100% stake refunded to all bettors."

        record.status = status
        record.verdict = verdict
        record.extracted_metric = metric
        record.confidence_score = u256(conf)
        record.last_audit_summary = summary

        self.markets[market_id] = record
        return status

    @gl.public.view
    def get_market(self, market_id: str) -> MarketRecord:
        assert market_id in self.markets, "[ERR_STATE_01] Market ID does not exist."
        return self.markets[market_id]

    @gl.public.view
    def get_total_markets(self) -> u256:
        return self.next_market_id
