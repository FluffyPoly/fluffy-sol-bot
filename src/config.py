"""
Configuration Management Module

This module loads and validates all configuration settings from environment variables.
Centralizes all configurable parameters for the trading bot.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Centralized configuration for the trading bot.
    
    All trading parameters, API endpoints, and operational settings
    are loaded here for easy access and modification.
    """
    
    # === SOLANA NETWORK ===
    RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    # === WALLET ===
    WALLET_PATH = Path(os.getenv("WALLET_PATH", "./config/wallet.json"))
    
    # === TRADING PARAMETERS ===
    # Maximum size of any single position in USDC
    MAX_POSITION_SIZE_USDC = float(os.getenv("MAX_POSITION_SIZE_USDC", 50))
    
    # Maximum number of positions we can hold simultaneously
    MAX_SIMULTANEOUS_POSITIONS = int(os.getenv("MAX_SIMULTANEOUS_POSITIONS", 3))
    
    # Stop loss percentage (negative value, e.g., -15 means 15% loss)
    STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", -15))
    
    # Take profit percentage (positive value, e.g., 30 means 30% gain)
    TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", 30))
    
    # Portfolio-wide stop loss in USDC (total loss limit)
    PORTFOLIO_STOP_LOSS_USDC = float(os.getenv("PORTFOLIO_STOP_LOSS_USDC", 150))
    
    # Starting capital for tracking performance
    STARTING_CAPITAL_USDC = float(os.getenv("STARTING_CAPITAL_USDC", 300))
    
    # === MARKET SCANNING ===
    # Minimum liquidity in USD for a token to be considered
    MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", 1_000_000))
    
    # Minimum token age in hours (avoids rug pulls on new tokens)
    MIN_TOKEN_AGE_HOURS = int(os.getenv("MIN_TOKEN_AGE_HOURS", 24))
    
    # How often to scan markets for new opportunities (seconds)
    SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", 15))
    
    # How often to check existing positions for stop loss/take profit (seconds)
    POSITION_CHECK_INTERVAL_SECONDS = int(os.getenv("POSITION_CHECK_INTERVAL_SECONDS", 10))
    
    # === JUPITER API ===
    JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
    JUPITER_SWAP_URL = "https://quote-api.jup.ag/v6/swap"
    JUPITER_PRICE_URL = "https://api.jup.ag/price/v2"
    
    # === TELEGRAM ALERTS ===
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    
    # === LOGGING ===
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = Path(os.getenv("LOG_FILE", "./logs/bot.log"))
    HEARTBEAT_INTERVAL_MINUTES = int(os.getenv("HEARTBEAT_INTERVAL_MINUTES", 5))
    
    # === STATE MANAGEMENT ===
    STATE_FILE = Path("./data/bot_state.json")
    TRADES_LOG_FILE = Path("./data/trades.jsonl")
    
    # === USDC MINT ADDRESS (Solana mainnet) ===
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # === SOL MINT ADDRESS ===
    SOL_MINT = "So11111111111111111111111111111111111111112"
    
    @classmethod
    def validate(cls):
        """
        Validate configuration on startup.
        
        Returns:
            tuple: (is_valid: bool, errors: list)
        """
        errors = []
        
        # Check wallet file exists
        if not cls.WALLET_PATH.exists():
            errors.append(f"Wallet file not found: {cls.WALLET_PATH}")
        
        # Validate trading parameters
        if cls.MAX_POSITION_SIZE_USDC <= 0:
            errors.append("MAX_POSITION_SIZE_USDC must be positive")
        
        if cls.MAX_SIMULTANEOUS_POSITIONS <= 0:
            errors.append("MAX_SIMULTANEOUS_POSITIONS must be positive")
        
        if cls.STOP_LOSS_PERCENT >= 0:
            errors.append("STOP_LOSS_PERCENT must be negative (e.g., -15)")
        
        if cls.TAKE_PROFIT_PERCENT <= 0:
            errors.append("TAKE_PROFIT_PERCENT must be positive (e.g., 30)")
        
        # Check if we have enough capital for at least one position
        if cls.STARTING_CAPITAL_USDC < cls.MAX_POSITION_SIZE_USDC:
            errors.append("STARTING_CAPITAL_USDC must be >= MAX_POSITION_SIZE_USDC")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("✅ Configuration validated successfully")
        else:
            logger.error(f"❌ Configuration errors: {errors}")
        
        return is_valid, errors
    
    @classmethod
    def log_summary(cls):
        """Log a summary of current configuration."""
        logger.info("=" * 50)
        logger.info("📊 TRADING CONFIGURATION")
        logger.info("=" * 50)
        logger.info(f"💰 Starting Capital: ${cls.STARTING_CAPITAL_USDC} USDC")
        logger.info(f"📈 Max Position Size: ${cls.MAX_POSITION_SIZE_USDC} USDC")
        logger.info(f"🔢 Max Simultaneous Positions: {cls.MAX_SIMULTANEOUS_POSITIONS}")
        logger.info(f"🛑 Stop Loss: {cls.STOP_LOSS_PERCENT}%")
        logger.info(f"🎯 Take Profit: {cls.TAKE_PROFIT_PERCENT}%")
        logger.info(f"⚠️  Portfolio Stop Loss: ${cls.PORTFOLIO_STOP_LOSS_USDC} USDC")
        logger.info(f"💧 Min Liquidity: ${cls.MIN_LIQUIDITY_USD:,.0f} USD")
        logger.info(f"⏰ Token Age Min: {cls.MIN_TOKEN_AGE_HOURS}h")
        logger.info(f"📡 Scan Interval: {cls.SCAN_INTERVAL_SECONDS}s")
        logger.info(f"🔔 Telegram Alerts: {'Enabled' if cls.TELEGRAM_ENABLED else 'Disabled'}")
        logger.info("=" * 50)


# Create a singleton instance
config = Config()
