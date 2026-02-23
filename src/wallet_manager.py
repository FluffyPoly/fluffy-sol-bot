"""
Wallet Manager Module

Handles loading the wallet keypair and managing SOL/USDC balances.
This is the interface between our bot and the Solana blockchain for balance queries.
"""

import json
from pathlib import Path
from solders.keypair import Keypair
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from loguru import logger

from config import config


class WalletManager:
    """
    Manages the trading wallet: loading keys, checking balances, and signing transactions.
    
    This class handles:
    - Loading the private key from secure storage
    - Querying SOL and USDC balances
    - Providing the keypair for transaction signing
    """
    
    def __init__(self, rpc_client: Client):
        """
        Initialize the wallet manager.
        
        Args:
            rpc_client: Solana RPC client for blockchain queries
        """
        self.rpc_client = rpc_client
        self.keypair = None
        self.public_key = None
        self._load_wallet()
    
    def _load_wallet(self):
        """
        Load wallet keypair from the configured file.
        
        Security: The wallet file should have 0600 permissions (owner read/write only).
        """
        wallet_path = config.WALLET_PATH
        
        if not wallet_path.exists():
            raise FileNotFoundError(f"Wallet file not found: {wallet_path}")
        
        # Read private key from JSON file
        with open(wallet_path, "r") as f:
            private_key = json.load(f)
        
        # Convert list of bytes back to Keypair
        self.keypair = Keypair.from_bytes(bytes(private_key))
        self.public_key = self.keypair.pubkey()
        
        logger.info(f"✅ Wallet loaded: {self.public_key}")
    
    def get_sol_balance(self) -> float:
        """
        Query SOL balance from the blockchain.
        
        Returns:
            float: SOL balance (lamports converted to SOL)
        """
        try:
            response = self.rpc_client.get_balance(
                self.public_key,
                commitment=Confirmed
            )
            # Convert lamports to SOL (1 SOL = 1,000,000,000 lamports)
            lamports = response.value
            sol_balance = lamports / 1_000_000_000
            logger.debug(f"SOL Balance: {sol_balance:.6f} SOL")
            return sol_balance
        except Exception as e:
            logger.error(f"Failed to get SOL balance: {e}")
            return 0.0
    
    def get_usdc_balance(self) -> float:
        """
        Query USDC token balance from the blockchain.
        
        USDC is an SPL token, so we need to find the token account
        associated with our wallet and the USDC mint.
        
        Returns:
            float: USDC balance (adjusted for 6 decimals)
        """
        try:
            from solders.pubkey import Pubkey
            
            # Find the USDC token account for this wallet
            usdc_mint = Pubkey.from_string(config.USDC_MINT)
            
            # Get token accounts by owner
            response = self.rpc_client.get_token_accounts_by_owner(
                self.public_key,
                mint=usdc_mint,
                commitment=Confirmed
            )
            
            if not response.value:
                logger.debug("No USDC token account found")
                return 0.0
            
            # Get the first token account (should only be one)
            token_account = response.value[0].pubkey
            
            # Get token balance
            balance_response = self.rpc_client.get_token_account_balance(
                token_account,
                commitment=Confirmed
            )
            
            # USDC has 6 decimals
            ui_amount = balance_response.value.ui_amount
            if ui_amount is None:
                return 0.0
            
            logger.debug(f"USDC Balance: {ui_amount:.2f} USDC")
            return float(ui_amount)
            
        except Exception as e:
            logger.error(f"Failed to get USDC balance: {e}")
            return 0.0
    
    def get_total_value_usd(self, sol_price_usd: float) -> float:
        """
        Calculate total portfolio value in USD.
        
        Args:
            sol_price_usd: Current SOL price in USD
            
        Returns:
            float: Total value (SOL + USDC) in USD
        """
        sol_balance = self.get_sol_balance()
        usdc_balance = self.get_usdc_balance()
        
        sol_value_usd = sol_balance * sol_price_usd
        total_value = sol_value_usd + usdc_balance
        
        logger.debug(f"Total Portfolio Value: ${total_value:.2f} USD (SOL: ${sol_value_usd:.2f}, USDC: ${usdc_balance:.2f})")
        return total_value
    
    def sign_transaction(self, transaction):
        """
        Sign a transaction with our wallet keypair.
        
        Args:
            transaction: The transaction to sign
            
        Returns:
            Signed transaction
        """
        transaction.sign_partial(self.keypair)
        return transaction


# Singleton pattern for easy access
_wallet_manager = None

def get_wallet_manager(rpc_client: Client) -> WalletManager:
    """
    Get or create the wallet manager singleton.
    
    Args:
        rpc_client: Solana RPC client
        
    Returns:
        WalletManager instance
    """
    global _wallet_manager
    if _wallet_manager is None:
        _wallet_manager = WalletManager(rpc_client)
    return _wallet_manager
