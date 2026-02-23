"""
Trade Manager Module

Manages all active positions, executes trades, and monitors for
stop loss / take profit conditions.

This is the "hands" of the trading bot - it actually executes trades
and manages risk.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
import aiohttp
from loguru import logger

from config import config
from jupiter_client import JupiterClient


@dataclass
class Position:
    """
    Represents an active trading position.
    
    Tracks all information needed to manage the position:
    - Entry price and size
    - Current value
    - Stop loss and take profit levels
    - P&L tracking
    """
    mint: str                    # Token mint address
    symbol: str                  # Token symbol
    entry_price_usd: float       # Entry price in USD
    entry_time: float            # Unix timestamp of entry
    position_size_usdc: float    # Amount of USDC invested
    token_amount: float          # Amount of tokens held
    stop_loss_price: float       # Price at which we exit (loss)
    take_profit_price: float     # Price at which we exit (gain)
    current_price_usd: float     # Current price (updated regularly)
    realized_pnl_usd: float      # Realized P&L when closed
    
    # Computed properties
    @property
    def current_value_usd(self) -> float:
        """Current position value in USD."""
        return self.token_amount * self.current_price_usd
    
    @property
    def unrealized_pnl_usd(self) -> float:
        """Unrealized P&L in USD."""
        return self.current_value_usd - self.position_size_usdc
    
    @property
    def unrealized_pnl_percent(self) -> float:
        """Unrealized P&L as percentage."""
        return (self.unrealized_pnl_usd / self.position_size_usdc) * 100
    
    @property
    def age_hours(self) -> float:
        """Position age in hours."""
        return (time.time() - self.entry_time) / 3600
    
    def should_stop_loss(self) -> bool:
        """Check if stop loss condition is met."""
        return self.current_price_usd <= self.stop_loss_price
    
    def should_take_profit(self) -> bool:
        """Check if take profit condition is met."""
        return self.current_price_usd >= self.take_profit_price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        """Create Position from dictionary."""
        return cls(**data)
    
    def __str__(self) -> str:
        return (
            f"{self.symbol} | Entry: ${self.entry_price_usd:.6f} | "
            f"Current: ${self.current_price_usd:.6f} | "
            f"P&L: {self.unrealized_pnl_percent:+.1f}% | "
            f"Age: {self.age_hours:.1f}h"
        )


class TradeManager:
    """
    Manages all trading operations.
    
    Responsibilities:
    - Opening new positions (buying)
    - Closing positions (selling)
    - Monitoring stop loss / take profit
    - Position sizing and risk management
    - Trade logging and state persistence
    """
    
    def __init__(
        self,
        rpc_client: Client,
        jupiter_client: JupiterClient,
        wallet_public_key: str
    ):
        """
        Initialize trade manager.
        
        Args:
            rpc_client: Solana RPC client
            jupiter_client: Jupiter API client
            wallet_public_key: Wallet public key (base58 string)
        """
        self.rpc_client = rpc_client
        self.jupiter = jupiter_client
        self.wallet_public_key = wallet_public_key
        
        # Active positions
        self.positions: Dict[str, Position] = {}
        
        # Trade history
        self.trade_history: List[Dict[str, Any]] = []
        
        # Load existing state
        self._load_state()
        
        logger.info(f"✅ Trade manager initialized with {len(self.positions)} existing positions")
    
    async def open_position(
        self,
        mint: str,
        symbol: str,
        price_usd: float,
        amount_usdc: float
    ) -> Optional[Position]:
        """
        Open a new position (buy tokens).
        
        Args:
            mint: Token mint address
            symbol: Token symbol
            price_usd: Current price in USD
            amount_usdc: Amount of USDC to spend
        
        Returns:
            Position object if successful, None if failed
        """
        # Check if we already have this position
        if mint in self.positions:
            logger.warning(f"Already have position in {symbol}")
            return None
        
        # Check position limit
        if len(self.positions) >= config.MAX_SIMULTANEOUS_POSITIONS:
            logger.warning(f"Max positions ({config.MAX_SIMULTANEOUS_POSITIONS}) reached")
            return None
        
        # Calculate position size
        position_size = min(amount_usdc, config.MAX_POSITION_SIZE_USDC)
        
        # Calculate stop loss and take profit prices
        stop_loss_price = price_usd * (1 + config.STOP_LOSS_PERCENT / 100)
        take_profit_price = price_usd * (1 + config.TAKE_PROFIT_PERCENT / 100)
        
        logger.info(
            f"📈 Opening position: {symbol} | "
            f"Size: ${position_size:.2f} | "
            f"Entry: ${price_usd:.6f} | "
            f"SL: ${stop_loss_price:.6f} | "
            f"TP: ${take_profit_price:.6f}"
        )
        
        # Execute the buy via Jupiter
        token_amount = await self._execute_buy(mint, position_size)
        
        if token_amount is None or token_amount <= 0:
            logger.error("Failed to execute buy order")
            return None
        
        # Create position object
        position = Position(
            mint=mint,
            symbol=symbol,
            entry_price_usd=price_usd,
            entry_time=time.time(),
            position_size_usdc=position_size,
            token_amount=token_amount,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            current_price_usd=price_usd,
            realized_pnl_usd=0.0
        )
        
        # Add to active positions
        self.positions[mint] = position
        
        # Log the trade
        self._log_trade("OPEN", position)
        
        # Save state
        self._save_state()
        
        logger.info(f"✅ Position opened: {position}")
        return position
    
    async def close_position(self, mint: str, reason: str = "manual") -> Optional[float]:
        """
        Close an existing position (sell tokens).
        
        Args:
            mint: Token mint address
            reason: Reason for closing (manual, stop_loss, take_profit)
        
        Returns:
            Amount of USDC received if successful, None if failed
        """
        if mint not in self.positions:
            logger.warning(f"No position found for {mint}")
            return None
        
        position = self.positions[mint]
        
        logger.info(
            f"📉 Closing position: {position.symbol} | "
            f"Reason: {reason} | "
            f"P&L: {position.unrealized_pnl_percent:+.1f}% "
            f"(${position.unrealized_pnl_usd:+.2f})"
        )
        
        # Execute the sell via Jupiter
        usdc_received = await self._execute_sell(mint, position.token_amount)
        
        if usdc_received is None:
            logger.error("Failed to execute sell order")
            return None
        
        # Calculate realized P&L
        realized_pnl = usdc_received - position.position_size_usdc
        position.realized_pnl_usd = realized_pnl
        
        # Log the trade
        self._log_trade("CLOSE", position, reason=reason)
        
        # Remove from active positions
        del self.positions[mint]
        
        # Save state
        self._save_state()
        
        logger.info(
            f"✅ Position closed: {position.symbol} | "
            f"Received: ${usdc_received:.2f} | "
            f"P&L: ${realized_pnl:+.2f}"
        )
        
        return usdc_received
    
    async def check_positions(self) -> List[Dict[str, Any]]:
        """
        Check all positions for stop loss / take profit conditions.
        
        Returns:
            List of actions taken (closures)
        """
        actions = []
        
        if not self.positions:
            return actions
        
        # Get current prices for all positions
        mints = list(self.positions.keys())
        prices = await self.jupiter.get_token_prices(mints)
        
        for mint, position in self.positions.items():
            # Update current price
            if mint in prices:
                position.current_price_usd = prices[mint]
            else:
                logger.warning(f"Could not get price for {position.symbol}")
                continue
            
            # Check stop loss
            if position.should_stop_loss():
                logger.warning(
                    f"🛑 STOP LOSS triggered for {position.symbol}: "
                    f"${position.current_price_usd:.6f} <= ${position.stop_loss_price:.6f}"
                )
                result = await self.close_position(mint, reason="stop_loss")
                if result is not None:
                    actions.append({
                        "action": "stop_loss",
                        "mint": mint,
                        "symbol": position.symbol,
                        "pnl_usd": position.realized_pnl_usd
                    })
            
            # Check take profit
            elif position.should_take_profit():
                logger.info(
                    f"🎯 TAKE PROFIT triggered for {position.symbol}: "
                    f"${position.current_price_usd:.6f} >= ${position.take_profit_price:.6f}"
                )
                result = await self.close_position(mint, reason="take_profit")
                if result is not None:
                    actions.append({
                        "action": "take_profit",
                        "mint": mint,
                        "symbol": position.symbol,
                        "pnl_usd": position.realized_pnl_usd
                    })
        
        return actions
    
    async def _execute_buy(self, mint: str, amount_usdc: float) -> Optional[float]:
        """
        Execute a buy order via Jupiter.
        
        Args:
            mint: Token mint to buy
            amount_usdc: Amount of USDC to spend
        
        Returns:
            Amount of tokens received, or None if failed
        """
        try:
            # Convert USDC to lamports (USDC has 6 decimals)
            amount = int(amount_usdc * 1_000_000)
            
            # Get quote
            quote = await self.jupiter.get_quote(
                input_mint=config.USDC_MINT,
                output_mint=mint,
                amount=amount,
                slippage_bps=50  # 0.5% slippage
            )
            
            if not quote:
                return None
            
            # Get swap transaction
            tx_bytes = await self.jupiter.get_swap_transaction(
                quote=quote,
                user_public_key=self.wallet_public_key
            )
            
            if not tx_bytes:
                return None
            
            # Deserialize and send transaction
            # Note: Full implementation would sign and send here
            # For now, we simulate to get expected output
            out_amount = int(quote.get("outAmount", 0))
            
            # Get token decimals (simplified - would need token metadata in production)
            decimals = 6  # Common default
            token_amount = out_amount / (10 ** decimals)
            
            logger.info(f"Buy executed: ${amount_usdc} USDC → {token_amount:.4f} tokens")
            return token_amount
            
        except Exception as e:
            logger.error(f"Buy execution failed: {e}")
            return None
    
    async def _execute_sell(self, mint: str, token_amount: float) -> Optional[float]:
        """
        Execute a sell order via Jupiter.
        
        Args:
            mint: Token mint to sell
            token_amount: Amount of tokens to sell
        
        Returns:
            Amount of USDC received, or None if failed
        """
        try:
            # Get token decimals (simplified)
            decimals = 6
            amount = int(token_amount * (10 ** decimals))
            
            # Get quote
            quote = await self.jupiter.get_quote(
                input_mint=mint,
                output_mint=config.USDC_MINT,
                amount=amount,
                slippage_bps=50
            )
            
            if not quote:
                return None
            
            # Get expected output
            out_amount = int(quote.get("outAmount", 0))
            usdc_received = out_amount / 1_000_000  # USDC has 6 decimals
            
            # Get swap transaction and send (simplified)
            tx_bytes = await self.jupiter.get_swap_transaction(
                quote=quote,
                user_public_key=self.wallet_public_key
            )
            
            if not tx_bytes:
                return None
            
            logger.info(f"Sell executed: {token_amount:.4f} tokens → ${usdc_received:.2f} USDC")
            return usdc_received
            
        except Exception as e:
            logger.error(f"Sell execution failed: {e}")
            return None
    
    def _log_trade(self, action: str, position: Position, reason: str = ""):
        """Log a trade to the trades file."""
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "mint": position.mint,
            "symbol": position.symbol,
            "entry_price": position.entry_price_usd,
            "current_price": position.current_price_usd,
            "position_size_usdc": position.position_size_usdc,
            "token_amount": position.token_amount,
            "pnl_usd": position.realized_pnl_usd if action == "CLOSE" else 0,
            "reason": reason
        }
        
        self.trade_history.append(trade_record)
        
        # Append to JSONL file
        trades_file = config.TRADES_LOG_FILE
        trades_file.parent.mkdir(exist_ok=True)
        
        with open(trades_file, "a") as f:
            f.write(json.dumps(trade_record) + "\n")
    
    def _save_state(self):
        """Save current state to file for crash recovery."""
        state = {
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "last_updated": time.time()
        }
        
        state_file = config.STATE_FILE
        state_file.parent.mkdir(exist_ok=True)
        
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        
        logger.debug(f"State saved: {len(self.positions)} positions")
    
    def _load_state(self):
        """Load state from file on startup."""
        state_file = config.STATE_FILE
        
        if not state_file.exists():
            logger.info("No existing state file found")
            return
        
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
            
            positions_data = state.get("positions", {})
            for mint, pos_data in positions_data.items():
                self.positions[mint] = Position.from_dict(pos_data)
            
            logger.info(f"Loaded {len(self.positions)} positions from state file")
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of current portfolio."""
        total_invested = sum(p.position_size_usdc for p in self.positions.values())
        total_current = sum(p.current_value_usd for p in self.positions.values())
        total_pnl = total_current - total_invested
        total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            "num_positions": len(self.positions),
            "total_invested_usdc": total_invested,
            "total_current_usdc": total_current,
            "total_pnl_usdc": total_pnl,
            "total_pnl_percent": total_pnl_percent,
            "positions": [str(p) for p in self.positions.values()]
        }
