"""
Telegram Alerts Module

Sends real-time notifications to Telegram for important trading events:
- Position opened
- Position closed (stop loss / take profit)
- Portfolio alerts
- Bot status/heartbeat

Uses Telegram Bot API for reliable, instant notifications.
"""

import aiohttp
from typing import Optional
from loguru import logger

from config import config


class TelegramAlerter:
    """
    Sends alerts to Telegram.
    
    Provides formatted messages for all trading events.
    Falls back gracefully if Telegram is not configured.
    """
    
    def __init__(self, session: aiohttp.ClientSession):
        """
        Initialize Telegram alerter.
        
        Args:
            session: aiohttp session for HTTP requests
        """
        self.session = session
        self.enabled = config.TELEGRAM_ENABLED
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        
        if self.enabled:
            logger.info(f"✅ Telegram alerts enabled (chat: {chat_id})")
        else:
            logger.warning("⚠️  Telegram alerts disabled (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
    
    async def send_alert(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send an alert message to Telegram.
        
        Args:
            message: Message text (supports HTML formatting)
            parse_mode: "HTML" or "Markdown"
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Alert (not sent): {message[:100]}...")
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            async with self.session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    logger.debug("✅ Telegram alert sent")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Telegram API error: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    async def alert_position_opened(self, symbol: str, entry_price: float, size_usdc: float, stop_loss: float, take_profit: float):
        """Alert when a new position is opened."""
        message = (
            f"📈 <b>POSITION OPENED</b>\n\n"
            f"🪙 Token: <b>{symbol}</b>\n"
            f"💰 Entry: <code>${entry_price:.6f}</code>\n"
            f"📊 Size: <code>${size_usdc:.2f} USDC</code>\n"
            f"🛑 Stop Loss: <code>${stop_loss:.6f}</code>\n"
            f"🎯 Take Profit: <code>${take_profit:.6f}</code>\n\n"
            f"#Trading #Solana"
        )
        await self.send_alert(message)
    
    async def alert_position_closed(self, symbol: str, pnl_usd: float, pnl_percent: float, reason: str):
        """Alert when a position is closed."""
        emoji = "🎯" if pnl_usd > 0 else "🛑"
        pnl_color = "green" if pnl_usd > 0 else "red"
        
        message = (
            f"{emoji} <b>POSITION CLOSED</b>\n\n"
            f"🪙 Token: <b>{symbol}</b>\n"
            f"💵 P&L: <b><{pnl_color}>{pnl_usd:+.2f} USDC ({pnl_percent:+.1f}%)</{pnl_color}></b>\n"
            f"📝 Reason: <code>{reason}</code>\n\n"
            f"#Trading #Solana"
        )
        await self.send_alert(message)
    
    async def alert_portfolio_status(self, total_value: float, total_pnl: float, pnl_percent: float, num_positions: int):
        """Alert with portfolio summary."""
        pnl_color = "green" if total_pnl >= 0 else "red"
        
        message = (
            f"📊 <b>PORTFOLIO UPDATE</b>\n\n"
            f"💰 Total Value: <code>${total_value:.2f} USDC</code>\n"
            f"📈 P&L: <b><{pnl_color}>${total_pnl:+.2f} ({pnl_percent:+.1f}%)</{pnl_color}></b>\n"
            f"📦 Open Positions: <code>{num_positions}</code>\n\n"
            f"#Portfolio #Solana"
        )
        await self.send_alert(message)
    
    async def alert_heartbeat(self, uptime_hours: float, trades_today: int, status: str = "healthy"):
        """Send periodic heartbeat status."""
        status_emoji = "✅" if status == "healthy" else "⚠️"
        
        message = (
            f"{status_emoji} <b>BOT HEARTBEAT</b>\n\n"
            f"⏱️  Uptime: <code>{uptime_hours:.1f} hours</code>\n"
            f"💹 Trades Today: <code>{trades_today}</code>\n"
            f"🟢 Status: <code>{status}</code>\n\n"
            f"#BotStatus"
        )
        await self.send_alert(message)
    
    async def alert_error(self, error_message: str):
        """Alert on critical error."""
        message = (
            f"🚨 <b>BOT ERROR</b>\n\n"
            f"<code>{error_message}</code>\n\n"
            f"#Error #Alert"
        )
        await self.send_alert(message)
    
    async def alert_startup(self):
        """Alert when bot starts."""
        message = (
            f"🚀 <b>SOLANA TRADING BOT STARTED</b>\n\n"
            f"📍 Wallet: <code>{config.WALLET_PATH.name}</code>\n"
            f"💰 Capital: <code>${config.STARTING_CAPITAL_USDC} USDC</code>\n"
            f"📊 Max Positions: <code>{config.MAX_SIMULTANEOUS_POSITIONS}</code>\n"
            f"🛑 Stop Loss: <code>{config.STOP_LOSS_PERCENT}%</code>\n"
            f"🎯 Take Profit: <code>{config.TAKE_PROFIT_PERCENT}%</code>\n\n"
            f"Ready to trade! 🐻\n\n"
            f"#BotStarted #Solana"
        )
        await self.send_alert(message)


# Helper function to create alerter with session
async def create_telegram_alerter() -> tuple[aiohttp.ClientSession, TelegramAlerter]:
    """
    Create a Telegram alerter with its own aiohttp session.
    
    Returns:
        Tuple of (session, alerter)
    """
    session = aiohttp.ClientSession()
    alerter = TelegramAlerter(session)
    return session, alerter
