"""
Fluffy Solana Momentum Bot - Main Daemon Loop
24/7 autonomous trading with self-evolution
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from loguru import logger
import aiohttp

from config import Config
from wallet_manager import WalletManager
from jupiter_client import JupiterClient
from market_scanner import MarketScanner
from trade_manager import TradeManager
from telegram_alerts import TelegramAlerter
from backtest_engine import BacktestEngine
from indicator_arena import IndicatorArena
from strategy_evolver import StrategyEvolver
from regime_detector import RegimeDetector
from fee_manager import FeeManager

class MomentumBot:
    def __init__(self):
        self.config = Config()
        self.wallet_manager = WalletManager(self.config)
        self.jupiter_client = JupiterClient(self.config)
        self.scanner = MarketScanner(self.config)
        self.trade_manager = TradeManager(self.config, self.wallet_manager, self.jupiter_client)
        self.alerter = TelegramAlerter(self.config)
        
        # Training/evolution modules
        self.backtest_engine = BacktestEngine()
        self.arena = IndicatorArena()
        self.evolver = StrategyEvolver()
        self.regime_detector = RegimeDetector()
        self.fee_manager = FeeManager(self.wallet_manager, self.jupiter_client)
        
        self.running = False
        self.candles_cache = {}  # token -> candles
        self.heartbeat_interval = 300  # 5 min
        self.scan_interval = 15  # 15 sec
        self.evolution_interval = 3600  # 1 hour
        
        logger.add("logs/bot.log", rotation="10 MB", retention="7 days")
        logger.info("🐻 Fluffy Solana Momentum Bot initialized")
        
    async def start(self):
        """Start the bot daemon"""
        self.running = True
        logger.info("🚀 Bot starting...")
        
        # Initial checks
        await self.fee_manager.check_and_refill()
        
        # Start concurrent tasks
        await asyncio.gather(
            self._scan_loop(),
            self._position_check_loop(),
            self._evolution_loop(),
            self._heartbeat_loop(),
        )
    
    async def _scan_loop(self):
        """Scan markets every 15 seconds"""
        logger.info("📊 Market scanner started (15s interval)")
        
        while self.running:
            try:
                # Get current regime
                candles = await self._fetch_candles('SOL')
                regime = self.regime_detector.detect(candles)
                strategy = self.regime_detector.get_strategy_for_regime()
                
                # Scan all tokens
                opportunities = await self.scanner.scan_opportunities(
                    tokens=self.config.TOKEN_UNIVERSE,
                    strategy=strategy
                )
                
                # Execute best opportunities
                for opp in opportunities[:3]:  # Max 3 positions
                    if self.trade_manager.can_open_position():
                        await self.trade_manager.execute_trade(opp)
                
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(5)
    
    async def _position_check_loop(self):
        """Check positions every 10 seconds for SL/TP"""
        logger.info("📈 Position monitor started (10s interval)")
        
        while self.running:
            try:
                await self.trade_manager.check_positions()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Position check error: {e}")
                await asyncio.sleep(5)
    
    async def _evolution_loop(self):
        """Run strategy evolution every hour"""
        logger.info("🧬 Strategy evolution started (1h interval)")
        
        while self.running:
            try:
                # Generate and test variants
                variants = self.evolver.generate_variants(10)
                
                # Backtest each variant
                results = []
                for v in variants:
                    result = await self._backtest_variant(v.params)
                    results.append({
                        'params': v.params,
                        'win_rate': result['win_rate'],
                        'trades': result['total_trades'],
                        'sharpe': result.get('sharpe', 0)
                    })
                
                # Select best
                best = self.evolver.select_best(results)
                
                # Update arena with results
                for r in results:
                    self.arena.record_trade(
                        'RSI',  # Base indicator
                        r['params'],
                        r['win_rate'] * 100  # PnL proxy
                    )
                
                logger.info(f"🎯 Evolution complete - Best: {best.win_rate*100:.1f}%")
                
                # Save status
                self._save_status()
                
                await asyncio.sleep(self.evolution_interval)
                
            except Exception as e:
                logger.error(f"Evolution error: {e}")
                await asyncio.sleep(60)
    
    async def _heartbeat_loop(self):
        """Send heartbeat every 5 minutes"""
        logger.info("💓 Heartbeat started (5min interval)")
        
        while self.running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_candles(self, token: str) -> list:
        """Fetch candle data for token"""
        # Placeholder - integrate with Birdeye API
        import random
        return [
            {'close': 100 + i + random.gauss(0, 2), 'volume': 1000000, 'time': i, 'high': 105, 'low': 95}
            for i in range(100)
        ]
    
    async def _backtest_variant(self, params: dict) -> dict:
        """Backtest a strategy variant"""
        candles = await self._fetch_candles('SOL')
        return self.backtest_engine.run(candles, params)
    
    async def _send_heartbeat(self):
        """Send heartbeat with status"""
        status = self.get_status()
        
        message = f"""
💓 **Fluffy Bot Heartbeat**
━━━━━━━━━━━━━━━━━━━━━━
📊 Regime: {status['regime']}
🎯 Win Rate: {status['win_rate']*100:.1f}%
📈 Positions: {status['open_positions']}/{status['max_positions']}
💰 PnL: ${status['total_pnl']:.2f}
🧬 Generation: {status['evolution_generation']}
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        await self.alerter.send_alert(message)
        
        # Log to file
        with open('data/heartbeats.jsonl', 'a') as f:
            f.write(json.dumps(status) + '\n')
    
    def _save_status(self):
        """Save current status to file"""
        status = self.get_status()
        with open('data/accelerator_status.json', 'w') as f:
            json.dump(status, f, indent=2, default=str)
    
    def get_status(self) -> dict:
        """Get comprehensive bot status"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'regime': self.regime_detector.current_regime,
            'win_rate': self.evolver.best_win_rate,
            'open_positions': len(self.trade_manager.positions),
            'max_positions': self.config.MAX_CONCURRENT_POSITIONS,
            'total_pnl': sum(p['unrealized_pnl'] for p in self.trade_manager.positions.values()),
            'evolution_generation': self.evolver.generation,
            'variants_tested': len(self.evolver.variants),
            'indicator_leaderboard': [
                {'name': i.name, 'win_rate': i.win_rate}
                for i in self.arena.get_top_indicators(5)
            ],
            'fee_reserve': 'checked',
            'status': 'running' if self.running else 'stopped'
        }
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        logger.info("🛑 Bot stopping...")
        self._save_status()


async def main():
    bot = MomentumBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        bot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        bot.stop()


if __name__ == '__main__':
    asyncio.run(main())
