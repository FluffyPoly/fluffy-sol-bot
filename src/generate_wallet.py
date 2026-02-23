#!/usr/bin/env python3
"""
Generate a new Solana wallet for the trading bot.

This creates a new keypair and saves it securely.
The public key will be displayed for funding.
"""

import json
import os
from pathlib import Path
from solders.keypair import Keypair

def generate_wallet():
    """Generate a new Solana keypair and save it."""
    
    # Create new keypair
    keypair = Keypair()
    
    # Get public and private keys
    public_key = str(keypair.pubkey())
    private_key = list(keypair.secret())  # Convert to list for JSON serialization
    
    # Save directory
    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(exist_ok=True)
    
    # Save keypair to file (PRIVATE - keep secure!)
    keypair_path = config_dir / "wallet.json"
    with open(keypair_path, "w") as f:
        json.dump(private_key, f)
    
    # Set restrictive permissions (owner read/write only)
    os.chmod(keypair_path, 0o600)
    
    print("=" * 60)
    print("🎉 NEW SOLANA WALLET GENERATED")
    print("=" * 60)
    print(f"\n📍 PUBLIC KEY (for funding):")
    print(f"   {public_key}")
    print(f"\n💾 Private key saved to: {keypair_path.absolute()}")
    print(f"\n⚠️  SECURITY WARNING:")
    print(f"   - NEVER share your private key")
    print(f"   - Fund this wallet with USDC on Solana")
    print(f"   - Keep the wallet.json file secure!")
    print("=" * 60)
    
    return public_key, keypair_path

if __name__ == "__main__":
    generate_wallet()
