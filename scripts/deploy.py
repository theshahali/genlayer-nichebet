#!/usr/bin/env python3
"""
NicheBet Contract Deployment Script for GenLayer Studio / Testnet
"""
import sys
import os

def main():
    print("=" * 60)
    print("   Deploying NicheBetCourt to GenLayer Testnet")
    print("=" * 60)
    
    contract_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "NicheBetCourt.py")
    if not os.path.exists(contract_path):
        print(f"Error: Contract file not found at {contract_path}")
        sys.exit(1)

    with open(contract_path, "r", encoding="utf-8") as f:
        code = f.read()

    print(f"Contract loaded successfully ({len(code)} bytes).")
    print("Deploy via GenLayer Studio UI:")
    print("1. Open https://studio.genlayer.com/")
    print("2. Paste contents of NicheBetCourt.py")
    print("3. Pass operator address")
    print("4. Click Deploy Intelligent Contract.")
    print("=" * 60)

if __name__ == "__main__":
    main()
