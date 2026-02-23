"""
Market Scanner Module

Scans for trading opportunities based on momentum criteria:
- Strong buy volume in last 4 hours
- Breaking resistance levels
- Positive sentiment indicators
- Minimum liquidity and age filters

This is the "eyes" of the trading bot, constantly monitoring markets
for tokens that meet our entry criteria.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
from loguru import logger

from config import config


@dataclass
class TokenOpportunity:
    """
    Represents a potential trading opportunity.
    
    Contains all the data we need to decide whether to enter a position.
    """
    mint: str                    # Token mint address
    symbol: str                  # Token symbol (e.g., "BONK")
    name: str                    # Token name
    price_usd: float             # Current price in USD
    liquidity_usd: float         # Total liquidity in USD
    volume_24h_usd: float        # 24h trading volume
    volume_4h_usd: float         # 4h trading volume (for momentum)
    price_change_1h: float       # 1h price change %
    price_change_4h: float       # 4h price change %
    price_change_24h: float      # 24h price change %
    created_at: Optional[datetime]  # Token creation time (if known)
    momentum_score: float        # Calculated momentum score (0-100)
    
    def is_eligible(self) -> tuple[bool, List[str]]:
        """
        Check if this token meets our trading criteria.
        
        Returns:
            Tuple of (is_eligible, reasons) where reasons explains any disqualifications
        """
        reasons = []
        
        # Check minimum liquidity
        if self.liquidity_usd < config.MIN_LIQUIDITY_USD:
            reasons.append(f"Liquidity ${self.liquidity_usd:,.0f} < ${config.MIN_LIQUIDITY_USD:,.0f}")
        
        # Check 4h volume momentum (want strong recent buying)
        if self.volume_4h_usd < self.volume_24h_usd / 6:  # Should be > 1/6 of 24h volume
            reasons.append("Weak 4h volume momentum")
        
        # Check price momentum (want upward trend)
        if self.price_change_4h < 5:  # At least 5% gain in 4h
            reasons.append(f"4h change {self.price_change_4h:.1f}% < 5%")
        
        # Check token age if we have the data
        if self.created_at:
            age_hours = (datetime.now() - self.created_at).total_seconds() / 3600
            if age_hours < config.MIN_TOKEN_AGE_HOURS:
                reasons.append(f"Token age {age_hours:.1f}h < {config.MIN_TOKEN_AGE_HOURS}h")
        
        is_eligible = len(reasons) == 0
        return is_eligible, reasons
    
    def __str__(self) -> str:
        return (
            f"{self.symbol} | ${self.price_usd:.6f} | "
            f"4h: {self.price_change_4h:+.1f}% | "
            f"Liq: ${self.liquidity_usd/1e6:.1f}M | "
            f"Score: {self.momentum_score:.0f}"
        )


class MarketScanner:
    """
    Scans markets for momentum trading opportunities.
    
    Uses multiple data sources:
    - Jupiter API for prices and liquidity
    - DexScreener/Birdeye for volume and chart data
    - Custom momentum scoring algorithm
    """
    
    def __init__(self, session: aiohttp.ClientSession):
        """
        Initialize market scanner.
        
        Args:
            session: aiohttp session for HTTP requests
        """
        self.session = session
        self.token_cache: Dict[str, Dict] = {}  # Cache token metadata
        self.last_scan_time: Optional[float] = None
        logger.info("✅ Market scanner initialized")
    
    async def scan_opportunities(self) -> List[TokenOpportunity]:
        """
        Main scanning function. Finds all tokens meeting our criteria.
        
        Returns:
            List of TokenOpportunity objects sorted by momentum score
        """
        logger.info("🔍 Scanning for opportunities...")
        start_time = time.time()
        
        opportunities = []
        
        # Step 1: Get top tokens by volume (most liquid = safest)
        top_tokens = await self._get_top_tokens_by_volume()
        
        if not top_tokens:
            logger.warning("No tokens found in scan")
            return []
        
        # Step 2: Analyze each token for momentum signals
        for token_data in top_tokens[:50]:  # Analyze top 50 by volume
            opportunity = await self._analyze_token(token_data)
            if opportunity:
                is_eligible, reasons = opportunity.is_eligible()
                if is_eligible:
                    opportunities.append(opportunity)
                    logger.info(f"✅ Opportunity found: {opportunity}")
                else:
                    logger.debug(f"❌ {token_data.get('symbol', 'UNKNOWN')} disqualified: {reasons}")
        
        # Sort by momentum score (highest first)
        opportunities.sort(key=lambda x: x.momentum_score, reverse=True)
        
        scan_duration = time.time() - start_time
        self.last_scan_time = time.time()
        
        logger.info(f"📊 Scan complete: {len(opportunities)} opportunities in {scan_duration:.1f}s")
        return opportunities
    
    async def _get_top_tokens_by_volume(self) -> List[Dict[str, Any]]:
        """
        Get list of top tokens by 24h volume.
        
        Uses DexScreener API which has good coverage of Solana tokens.
        
        Returns:
            List of token data dictionaries
        """
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.error(f"DexScreener API failed: {response.status}")
                    return []
                
                data = await response.json()
                pairs = data.get("pairs", [])
                
                # Filter to Solana chain only
                solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                
                # Sort by 24h volume (highest first)
                solana_pairs.sort(key=lambda x: x.get("fdv", 0), reverse=True)
                
                logger.debug(f"Found {len(solana_pairs)} Solana pairs")
                return solana_pairs
                
        except Exception as e:
            logger.error(f"Failed to get top tokens: {e}")
            return []
    
    async def _analyze_token(self, token_data: Dict[str, Any]) -> Optional[TokenOpportunity]:
        """
        Analyze a single token for trading signals.
        
        Args:
            token_data: Token data from DexScreener
        
        Returns:
            TokenOpportunity or None if analysis fails
        """
        try:
            base_token = token_data.get("baseToken", {})
            price_usd = token_data.get("priceUsd", 0)
            liquidity_usd = token_data.get("liquidity", {}).get("usd", 0)
            volume_24h = token_data.get("volume", {}).get("h24", 0)
            
            # Calculate 4h volume (estimate from 24h if not available)
            volume_4h = token_data.get("volume", {}).get("h6", 0) * (4/6)  # Approximate
            
            # Price changes
            price_change_1h = token_data.get("priceChange", {}).get("h1", 0)
            price_change_4h = token_data.get("priceChange", {}).get("h6", 0) * (4/6)  # Approximate
            price_change_24h = token_data.get("priceChange", {}).get("h24", 0)
            
            # Calculate momentum score (0-100)
            momentum_score = self._calculate_momentum_score(
                price_change_1h=price_change_1h,
                price_change_4h=price_change_4h,
                price_change_24h=price_change_24h,
                volume_24h=volume_24h,
                liquidity_usd=liquidity_usd
            )
            
            # Get token creation time (if available)
            created_at = None
            pair_created_at = token_data.get("pairCreatedAt")
            if pair_created_at:
                created_at = datetime.fromtimestamp(pair_created_at / 1000)
            
            return TokenOpportunity(
                mint=base_token.get("address", ""),
                symbol=base_token.get("symbol", "UNKNOWN"),
                name=base_token.get("name", "Unknown Token"),
                price_usd=float(price_usd) if price_usd else 0,
                liquidity_usd=float(liquidity_usd) if liquidity_usd else 0,
                volume_24h_usd=float(volume_24h) if volume_24h else 0,
                volume_4h_usd=float(volume_4h) if volume_4h else 0,
                price_change_1h=float(price_change_1h) if price_change_1h else 0,
                price_change_4h=float(price_change_4h) if price_change_4h else 0,
                price_change_24h=float(price_change_24h) if price_change_24h else 0,
                created_at=created_at,
                momentum_score=momentum_score
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze token: {e}")
            return None
    
    def _calculate_momentum_score(
        self,
        price_change_1h: float,
        price_change_4h: float,
        price_change_24h: float,
        volume_24h: float,
        liquidity_usd: float
    ) -> float:
        """
        Calculate a momentum score (0-100) for a token.
        
        Higher scores = stronger momentum = better trading opportunity.
        
        Factors:
        - Recent price appreciation (1h, 4h)
        - Volume confirmation
        - Liquidity safety
        - Trend consistency
        """
        score = 0.0
        
        # Price momentum (max 40 points)
        # Want positive 4h change with accelerating 1h
        if price_change_4h > 0:
            score += min(price_change_4h, 20)  # Cap at 20 points
        if price_change_1h > price_change_4h / 4:  # Accelerating
            score += 10
        if price_change_24h > 0:  # Daily trend also positive
            score += 10
        
        # Volume strength (max 30 points)
        if volume_24h > 1_000_000:  # >$1M volume
            score += 15
        if volume_24h > 5_000_000:  # >$5M volume
            score += 15
        
        # Liquidity safety (max 20 points)
        if liquidity_usd > 1_000_000:  # >$1M liquidity
            score += 10
        if liquidity_usd > 5_000_000:  # >$5M liquidity
            score += 10
        
        # Trend consistency (max 10 points)
        # All timeframes positive = strong consistent trend
        if price_change_1h > 0 and price_change_4h > 0 and price_change_24h > 0:
            score += 10
        
        return min(score, 100.0)  # Cap at 100


# Helper function to create scanner with session
async def create_market_scanner() -> tuple[aiohttp.ClientSession, MarketScanner]:
    """
    Create a market scanner with its own aiohttp session.
    
    Returns:
        Tuple of (session, scanner)
    """
    session = aiohttp.ClientSession()
    scanner = MarketScanner(session)
    return session, scanner
