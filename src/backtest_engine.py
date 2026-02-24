"""
Backtest Engine - Realistic fee-adjusted backtesting
"""
import json
from datetime import datetime
from typing import Dict, List
import asyncio

FEES = {
    'swap': 0.003,  # 0.30% Jupiter
    'slippage': 0.005,  # 0.5%
    'network': 0.000005,  # SOL per tx
}

class BacktestEngine:
    def __init__(self, initial_capital: float = 1000.0):
        self.capital = initial_capital
        self.trades = []
        self.equity_curve = []
        
    def run(self, candles: List[Dict], strategy: Dict) -> Dict:
        """Run backtest on historical candles"""
        position = None
        trades = []
        equity = self.capital
        
        for i, candle in enumerate(candles):
            signal = self._check_signal(candle, strategy, candles[:i])
            
            if signal == 'BUY' and not position:
                # Enter long
                entry = candle['close'] * (1 + FEES['slippage'])
                qty = (self.capital * 0.1) / entry  # 10% position
                fees = (qty * entry * FEES['swap']) + FEES['network']
                position = {
                    'type': 'long',
                    'entry': entry,
                    'qty': qty,
                    'fees': fees,
                    'sl': entry * 0.85,  # -15%
                    'tp': entry * 1.30,  # +30%
                }
                
            elif position:
                # Check exit
                if candle['low'] <= position['sl']:
                    # Stop loss
                    pnl = (position['sl'] - position['entry']) * position['qty']
                    pnl -= position['fees']
                    equity += pnl
                    trades.append({
                        'entry': position['entry'],
                        'exit': position['sl'],
                        'pnl': pnl,
                        'type': 'SL',
                        'timestamp': candle['time']
                    })
                    position = None
                    
                elif candle['high'] >= position['tp']:
                    # Take profit
                    pnl = (position['tp'] - position['entry']) * position['qty']
                    pnl -= position['fees']
                    equity += pnl
                    trades.append({
                        'entry': position['entry'],
                        'exit': position['tp'],
                        'pnl': pnl,
                        'type': 'TP',
                        'timestamp': candle['time']
                    })
                    position = None
        
        return {
            'total_trades': len(trades),
            'winning_trades': sum(1 for t in trades if t['pnl'] > 0),
            'win_rate': sum(1 for t in trades if t['pnl'] > 0) / len(trades) if trades else 0,
            'total_pnl': equity - self.capital,
            'final_equity': equity,
            'trades': trades
        }
    
    def _check_signal(self, candle: Dict, strategy: Dict, history: List[Dict]) -> str:
        """Check for buy/sell signal based on strategy params"""
        if not history:
            return 'HOLD'
        
        # RSI check
        rsi = self._calculate_rsi(history + [candle], strategy.get('rsi_period', 14))
        rsi_low = strategy.get('rsi_low', 57)
        rsi_high = strategy.get('rsi_high', 63)
        
        # Volume check
        avg_vol = sum(c['volume'] for c in history[-20:]) / 20 if len(history) >= 20 else candle['volume']
        vol_mult = strategy.get('vol_mult', 1.38)
        
        if rsi_low <= rsi <= rsi_high and candle['volume'] > avg_vol * vol_mult:
            return 'BUY'
        
        return 'HOLD'
    
    def _calculate_rsi(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate RSI"""
        if len(candles) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(candles)):
            change = candles[i]['close'] - candles[i-1]['close']
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


async def run_backtest_suite():
    """Run backtest suite for all 50 tokens"""
    engine = BacktestEngine()
    results = {}
    
    # Load candle data (placeholder - integrate with Birdeye API)
    tokens = ['SOL', 'RAY', 'JUP', 'ORCA', 'JTO', 'MNDE', 'PYTH', 'WEN', 'HNT', 'INJ']
    
    for token in tokens:
        # Simulated candles (replace with real API)
        candles = [{'close': 100 + i, 'volume': 1000000 + i*100, 'time': i} for i in range(1000)]
        
        strategy = {
            'rsi_period': 14,
            'rsi_low': 57,
            'rsi_high': 63,
            'vol_mult': 1.38
        }
        
        result = engine.run(candles, strategy)
        results[token] = result
        print(f"{token}: Win Rate {result['win_rate']*100:.1f}%, Trades: {result['total_trades']}")
    
    return results


if __name__ == '__main__':
    asyncio.run(run_backtest_suite())
