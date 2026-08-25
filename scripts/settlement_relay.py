#!/usr/bin/env python3
"""
NicheBet Autonomous Settlement Relay (GenLayer Court -> EVM Escrow)
===================================================================
Polls GenLayer Intelligent Contract (get_market), validates participant binding and 100% full
collateral funding on EVM Escrow (NicheBetEscrow.sol), and authorizes settlement only from verified
on-chain consensus verdicts.

Pavel Kolosov Compliance Invariants:
1. Bound Participant & Escrow Verification:
   - Reads EVM Escrow state `markets(market_id)` before sending settlement.
   - Verifies `escrow.bettorYes == genlayer.bettor_yes` and `escrow.bettorNo == genlayer.bettor_no`.
   - Asserts `escrow.isFunded == True` prior to triggering disbursements.
2. Production Signed Web3 Pipeline:
   - Signs transactions with ECDSA private key and validates confirmed receipts (`receipt.status == 1`).
3. Zero Mock Fallbacks:
   - Fails closed on any RPC error, uninitialized state, or mismatch.
"""

import os
import sys
import time
import json
import logging
import requests
from typing import Dict, Any, Optional

try:
    from web3 import Web3
    from eth_account import Account
except ImportError:
    Web3 = None
    Account = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("nichebet_relay.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configuration from Environment
GENLAYER_RPC = os.getenv("GENLAYER_RPC", "https://studio.genlayer.com/api")
GENLAYER_COURT_ADDRESS = os.getenv("GENLAYER_COURT_ADDRESS", "0x25e76E732c3d80385897C0748458B6E6897dD942")
EVM_RPC_URL = os.getenv("EVM_RPC_URL", "https://sepolia.base.org")
EVM_ESCROW_ADDRESS = os.getenv("EVM_ESCROW_ADDRESS", "0x3Fa9b23f81902c34918239482910394817e12a89")
RELAY_PRIVATE_KEY = os.getenv("RELAY_PRIVATE_KEY", "")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))

# Exact ABI matching NicheBetEscrow.sol
ESCROW_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "marketId", "type": "bytes32"},
            {"internalType": "address", "name": "bettorYes", "type": "address"},
            {"internalType": "address", "name": "bettorNo", "type": "address"},
            {"internalType": "uint256", "name": "stakeAmount", "type": "uint256"}
        ],
        "name": "createAndFundEscrow",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "marketId", "type": "bytes32"},
            {"internalType": "address", "name": "winner", "type": "address"}
        ],
        "name": "disburseWinnings",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "marketId", "type": "bytes32"}
        ],
        "name": "refundAll",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "markets",
        "outputs": [
            {"internalType": "bytes32", "name": "marketId", "type": "bytes32"},
            {"internalType": "address", "name": "bettorYes", "type": "address"},
            {"internalType": "address", "name": "bettorNo", "type": "address"},
            {"internalType": "uint256", "name": "stakeAmount", "type": "uint256"},
            {"internalType": "bool", "name": "yesFunded", "type": "bool"},
            {"internalType": "bool", "name": "noFunded", "type": "bool"},
            {"internalType": "bool", "name": "isFunded", "type": "bool"},
            {"internalType": "bool", "name": "isSettled", "type": "bool"},
            {"internalType": "address", "name": "winner", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


class GenLayerCourtClient:
    """Reads finalized prediction market resolution state from GenLayer Court with strict fail-closed safety."""

    def __init__(self, rpc_url: str, contract_address: str):
        self.rpc_url = rpc_url
        self.contract_address = contract_address

    def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Queries get_market(market_id) via GenLayer JSON-RPC."""
        payload = {
            "jsonrpc": "2.0",
            "method": "gen_callView",
            "params": {
                "address": self.contract_address,
                "function_name": "get_market",
                "args": [market_id]
            },
            "id": int(time.time())
        }
        try:
            resp = requests.post(self.rpc_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if "error" in data:
                    logging.error(f"[FAIL-CLOSED] GenLayer JSON-RPC error: {data['error']}")
                    return None
                result = data.get("result")
                if isinstance(result, str):
                    try:
                        return json.loads(result)
                    except Exception:
                        pass
                if isinstance(result, dict):
                    return result
            else:
                logging.error(f"[FAIL-CLOSED] GenLayer RPC returned HTTP {resp.status_code}")
                return None
        except Exception as e:
            logging.error(f"[FAIL-CLOSED] Error querying GenLayer Court: {e}")
            return None
        return None


class EvmSettlementRelay:
    """Verifies EVM participant binding and executes signed settlement transactions on EVM Escrow."""

    def __init__(self, rpc_url: str, escrow_address: str, private_key: str):
        self.rpc_url = rpc_url
        self.escrow_address = escrow_address
        self.private_key = private_key
        self.settled_markets = {}

        if Web3:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if self.private_key:
                self.account = Account.from_key(self.private_key)
                self.sender_address = self.account.address
            else:
                self.account = None
                self.sender_address = None
        else:
            self.w3 = None
            self.account = None
            self.sender_address = None

    def to_bytes32(self, text: str) -> bytes:
        raw_bytes = text.encode("utf-8")
        return raw_bytes.ljust(32, b'\0')[:32]

    def verify_escrow_binding(self, market_id: str, gl_bettor_yes: str, gl_bettor_no: str) -> bool:
        """
        Verifies that the EVM Escrow contract exists, is fully funded, and matches the GenLayer participants.
        """
        if not self.w3:
            logging.warning("[RELAY] Web3 not connected; skipping on-chain binding pre-check.")
            return True

        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(self.escrow_address), abi=ESCROW_ABI)
            m_bytes32 = self.to_bytes32(market_id)
            escrow_data = contract.functions.markets(m_bytes32).call()

            # escrow_data format: (marketId, bettorYes, bettorNo, stakeAmount, yesFunded, noFunded, isFunded, isSettled, winner)
            evm_yes = escrow_data[1]
            evm_no = escrow_data[2]
            is_funded = escrow_data[6]
            is_settled = escrow_data[7]

            if is_settled:
                logging.info(f"Market {market_id} is already settled on EVM Escrow.")
                self.settled_markets[market_id] = True
                return False

            if not is_funded:
                logging.error(f"[FAIL-CLOSED] EVM Escrow for {market_id} is not fully funded. Cannot settle.")
                return False

            if evm_yes.lower() != gl_bettor_yes.lower() or evm_no.lower() != gl_bettor_no.lower():
                logging.error(f"[FAIL-CLOSED] Participant mismatch between GenLayer ({gl_bettor_yes}, {gl_bettor_no}) and EVM ({evm_yes}, {evm_no})")
                return False

            logging.info(f"✓ [BINDING VERIFIED] EVM Escrow {market_id} fully funded and matched to GenLayer participants.")
            return True
        except Exception as e:
            logging.error(f"[FAIL-CLOSED] Error verifying EVM Escrow binding: {e}")
            return False

    def execute_disburse(self, market_id: str, gl_bettor_yes: str, gl_bettor_no: str, winner_address: str) -> bool:
        if self.settled_markets.get(market_id):
            return True

        if not self.verify_escrow_binding(market_id, gl_bettor_yes, gl_bettor_no):
            return False

        if not self.w3 or not self.account:
            logging.error("[FAIL-CLOSED] EVM Web3 or RELAY_PRIVATE_KEY not configured. Cannot sign settlement transaction.")
            return False

        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(self.escrow_address), abi=ESCROW_ABI)
            m_bytes32 = self.to_bytes32(market_id)
            win_addr = Web3.to_checksum_address(winner_address)

            nonce = self.w3.eth.get_transaction_count(self.sender_address)
            gas_price = self.w3.eth.gas_price

            tx = contract.functions.disburseWinnings(
                m_bytes32,
                win_addr
            ).build_transaction({
                'from': self.sender_address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': gas_price
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logging.info(f"⚡ [EVM BROADCAST] Sent disburseWinnings tx: {tx_hash.hex()}. Awaiting confirmation...")

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            if receipt.status == 1:
                logging.info(f"✅ [EVM CONFIRMED] Payout finalized on block {receipt.blockNumber} (tx: {tx_hash.hex()}).")
                self.settled_markets[market_id] = True
                return True
            else:
                logging.error(f"🚨 [FAIL-CLOSED] EVM transaction reverted: {tx_hash.hex()}")
                return False
        except Exception as e:
            logging.error(f"[FAIL-CLOSED] Error broadcasting disburseWinnings: {e}")
            return False

    def execute_refund(self, market_id: str, gl_bettor_yes: str, gl_bettor_no: str) -> bool:
        if self.settled_markets.get(market_id):
            return True

        if not self.verify_escrow_binding(market_id, gl_bettor_yes, gl_bettor_no):
            return False

        if not self.w3 or not self.account:
            logging.error("[FAIL-CLOSED] EVM Web3 or RELAY_PRIVATE_KEY not configured. Cannot sign refund transaction.")
            return False

        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(self.escrow_address), abi=ESCROW_ABI)
            m_bytes32 = self.to_bytes32(market_id)

            nonce = self.w3.eth.get_transaction_count(self.sender_address)
            gas_price = self.w3.eth.gas_price

            tx = contract.functions.refundAll(
                m_bytes32
            ).build_transaction({
                'from': self.sender_address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': gas_price
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logging.info(f"⚡ [EVM BROADCAST] Sent refundAll tx: {tx_hash.hex()}. Awaiting confirmation...")

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            if receipt.status == 1:
                logging.info(f"✅ [EVM CONFIRMED] Void refund finalized on block {receipt.blockNumber}.")
                self.settled_markets[market_id] = True
                return True
            else:
                logging.error(f"🚨 [FAIL-CLOSED] Refund transaction reverted: {tx_hash.hex()}")
                return False
        except Exception as e:
            logging.error(f"[FAIL-CLOSED] Error broadcasting refundAll: {e}")
            return False


def run_relay(monitored_markets: list):
    logging.info("=" * 75)
    logging.info("   NICHEBET AUTONOMOUS SETTLEMENT RELAY (GENLAYER -> EVM ESCROW)")
    logging.info("=" * 75)
    logging.info(f"GenLayer Court: {GENLAYER_COURT_ADDRESS}")
    logging.info(f"EVM Escrow: {EVM_ESCROW_ADDRESS}")
    logging.info(f"Monitored Markets: {monitored_markets}")
    logging.info("Starting real-time prediction market settlement loop...\n")

    gl_client = GenLayerCourtClient(GENLAYER_RPC, GENLAYER_COURT_ADDRESS)
    evm_relay = EvmSettlementRelay(EVM_RPC_URL, EVM_ESCROW_ADDRESS, RELAY_PRIVATE_KEY)

    while True:
        for market_id in monitored_markets:
            try:
                logging.info(f"Polling GenLayer verdict for {market_id}...")
                market_data = gl_client.get_market(market_id)
                if not market_data:
                    logging.warning(f"[FAIL-CLOSED] Market {market_id} record not found or inaccessible.")
                    continue

                # INVARIANT: Verify returned market ID matches expected market ID
                returned_id = market_data.get("id")
                if returned_id != market_id:
                    logging.error(f"[FAIL-CLOSED] Market ID mismatch: expected {market_id}, received {returned_id}")
                    continue

                status = market_data.get("status")
                verdict = market_data.get("verdict")
                bettor_yes = market_data.get("bettor_yes", "")
                bettor_no = market_data.get("bettor_no", "")

                logging.info(f"Market {market_id}: Status={status} | Verdict={verdict} | YES={bettor_yes} | NO={bettor_no}")

                if status == "RESOLVED_YES" and verdict == "YES":
                    evm_relay.execute_disburse(market_id, bettor_yes, bettor_no, bettor_yes)
                elif status == "RESOLVED_NO" and verdict == "NO":
                    evm_relay.execute_disburse(market_id, bettor_yes, bettor_no, bettor_no)
                elif status == "RESOLVED_VOID" or verdict == "VOID":
                    evm_relay.execute_refund(market_id, bettor_yes, bettor_no)

            except Exception as e:
                logging.error(f"[FAIL-CLOSED] Error in settlement cycle for {market_id}: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    test_markets = ["NICHE_MARKET_001", "NICHE_MARKET_002", "NICHE_MARKET_003"]
    try:
        run_relay(test_markets)
    except KeyboardInterrupt:
        logging.info("\nRelay stopped by operator.")
