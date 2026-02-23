"""
Jupiter API Client Module

Jupiter is Solana's leading DEX aggregator. It finds the best prices across
all Solana DEXes (Raydium, Orca, Serum, etc.) and routes trades optimally.

This module handles:
- Getting price quotes for token swaps
- Executing swaps via Jupiter's API
- Fetching token prices and metadata
"""

import aiohttp
import base64
from typing import Optional, Dict, Any, List
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey
from loguru import logger

from config import config


class JupiterClient:
    """
    Client for interacting with Jupiter API.
    
    Jupiter aggregates liquidity from all Solana DEXes to provide:
    - Best price routing across multiple pools
    - Minimal slippage execution
    - Access to all token pairs
    """
    
    def __init__(self, session: aiohttp.ClientSession):
        """
        Initialize Jupiter client.
        
        Args:
            session: aiohttp session for HTTP requests
        """
        self.session = session
        self.base_url = "https://quote-api.jup.ag/v6"
        logger.info("✅ Jupiter client initialized")
    
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        only_direct_routes: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a swap quote from Jupiter.
        
        Args:
            input_mint: Token mint address to swap FROM
            output_mint: Token mint address to swap TO
            amount: Amount in smallest units (e.g., lamports for SOL, 6 decimals for USDC)
            slippage_bps: Slippage tolerance in basis points (50 = 0.5%, 100 = 1%)
            only_direct_routes: If True, only use direct routes (faster, may miss better prices)
        
        Returns:
            Quote data including expected output amount, price impact, and route info
            None if quote fails
        """
        url = f"{self.base_url}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
            "onlyDirectRoutes": only_direct_routes,
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Jupiter quote failed: {response.status} - {await response.text()}")
                    return None
                
                quote_data = await response.json()
                
                # Log quote details
                in_amount = int(quote_data.get("inAmount", 0))
                out_amount = int(quote_data.get("outAmount", 0))
                price_impact = float(quote_data.get("priceImpactPct", 0))
                
                logger.info(
                    f"📊 Quote: {in_amount} → {out_amount} | "
                    f"Impact: {price_impact:.2f}% | "
                    f"Routes: {len(quote_data.get('routePlan', []))}"
                )
                
                return quote_data
                
        except Exception as e:
            logger.error(f"Failed to get Jupiter quote: {e}")
            return None
    
    async def get_swap_transaction(
        self,
        quote: Dict[str, Any],
        user_public_key: str,
        wrap_unwrap_sol: bool = True,
        use_shared_accounts: bool = True,
    ) -> Optional[bytes]:
        """
        Get a swap transaction from Jupiter.
        
        Args:
            quote: Quote data from get_quote()
            user_public_key: User's wallet public key (base58 string)
            wrap_unwrap_sol: Auto-wrap SOL to WSOL if needed
            use_shared_accounts: Use Jupiter's shared intermediate token accounts
        
        Returns:
            Serialized transaction bytes ready to sign
            None if swap generation fails
        """
        url = f"{self.base_url}/swap"
        
        payload = {
            "quoteResponse": quote,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": wrap_unwrap_sol,
            "useSharedAccounts": use_shared_accounts,
            "dynamicComputeUnitLimit": True,  # Auto-calculate compute units
            "prioritizationFeeLamports": "auto",  # Auto-prioritize for faster inclusion
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Jupiter swap failed: {response.status} - {await response.text()}")
                    return None
                
                swap_data = await response.json()
                
                # Transaction is returned as base64-encoded bytes
                swap_transaction = swap_data.get("swapTransaction")
                if not swap_transaction:
                    logger.error("No swap transaction in response")
                    return None
                
                # Decode from base64
                transaction_bytes = base64.b64decode(swap_transaction)
                
                logger.info("✅ Swap transaction generated")
                return transaction_bytes
                
        except Exception as e:
            logger.error(f"Failed to get swap transaction: {e}")
            return None
    
    async def get_token_price(self, mint: str) -> Optional[float]:
        """
        Get current USD price for a token.
        
        Args:
            mint: Token mint address
        
        Returns:
            Price in USD
            None if price fetch fails
        """
        url = "https://api.jup.ag/price/v2"
        params = {"ids": mint}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                price_data = data.get("data", {}).get(mint, {})
                price = price_data.get("price")
                
                if price:
                    logger.debug(f"Token {mint[:8]}... price: ${price:.6f}")
                    return float(price)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get token price: {e}")
            return None
    
    async def get_token_prices(self, mints: List[str]) -> Dict[str, float]:
        """
        Get USD prices for multiple tokens at once.
        
        Args:
            mints: List of token mint addresses
        
        Returns:
            Dict mapping mint addresses to USD prices
        """
        url = "https://api.jup.ag/price/v2"
        params = {"ids": ",".join(mints)}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return {}
                
                data = await response.json()
                prices = {}
                
                for mint in mints:
                    price_data = data.get("data", {}).get(mint, {})
                    price = price_data.get("price")
                    if price:
                        prices[mint] = float(price)
                
                return prices
                
        except Exception as e:
            logger.error(f"Failed to get token prices: {e}")
            return {}
    
    async def get_token_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all tokens supported by Jupiter.
        
        Returns:
            List of token metadata (address, symbol, name, decimals, logoURI)
        """
        url = "https://token.jup.ag/all"
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                tokens = await response.json()
                logger.info(f"Loaded {len(tokens)} tokens from Jupiter")
                return tokens
                
        except Exception as e:
            logger.error(f"Failed to get token list: {e}")
            return []


# Helper function to create client with session
async def create_jupiter_client() -> tuple[aiohttp.ClientSession, JupiterClient]:
    """
    Create a Jupiter client with its own aiohttp session.
    
    Returns:
        Tuple of (session, client) - both needed for async operations
    """
    session = aiohttp.ClientSession()
    client = JupiterClient(session)
    return session, client
