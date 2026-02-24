"""
Indicator Arena - Parallel testing of multiple indicators
Tracks win rates, promotes/demotes based on performance
"""
import json
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict
import asyncio

@dataclass
class IndicatorStats:
    name: str
    params: Dict
    trades: int = 0
    wins: int = 0
    win_rate: float = 0.0
    sharpe: float = 0.0
    pnl: float = 0.0
    last_updated: str = ""

class IndicatorArena:
    def __init__(self):
        self.indicators: List[IndicatorStats] = [
            IndicatorStats('RSI', {'period': 14, 'low': 57, 'high': 63}),
            IndicatorStats('MACD', {'fast': 12, 'slow': 26, 'signal': 9}),
            IndicatorStats('Bollinger', {'period': 20, 'std': 2.0}),
            IndicatorStats('Volume', {'mult': 1.38, 'lookback': 20}),
            IndicatorStats('StochRSI', {'k': 14, 'd': 3, 'low': 20, 'high': 80}),
            IndicatorStats('VWAP', {'deviation': 0.02}),
            IndicatorStats('EMA_Cross', {'fast': 8, 'slow': 21}),
            IndicatorStats('ATR_Stop', {'mult': 1.85}),
        ]
        self.leaderboard_path = 'data/indicator_leaderboard.json'
        
    def record_trade(self, indicator_name: str, params: Dict, pnl: float):
        """Record a trade result for an indicator"""
        for ind in self.indicators:
            if ind.name == indicator_name and ind.params == params:
                ind.trades += 1
                if pnl > 0:
                    ind.wins += 1
                ind.win_rate = ind.wins / ind.trades if ind.trades > 0 else 0
                ind.pnl += pnl
                ind.last_updated = datetime.utcnow().isoformat()
                
                # Simple Sharpe calc (annualized)
                if ind.trades > 10:
                    ind.sharpe = (ind.pnl / ind.trades) / 0.05  # Simplified
                break
        
        self._save_leaderboard()
    
    def get_top_indicators(self, n: int = 3) -> List[IndicatorStats]:
        """Get top N performing indicators"""
        sorted_inds = sorted(self.indicators, key=lambda x: x.win_rate, reverse=True)
        return sorted_inds[:n]
    
    def get_bottom_indicators(self, n: int = 2) -> List[IndicatorStats]:
        """Get bottom N indicators (for benching)"""
        sorted_inds = sorted(self.indicators, key=lambda x: x.win_rate)
        return sorted_inds[:n]
    
    def promote_variant(self, base_name: str, new_params: Dict, win_rate: float):
        """Add a new variant if it performs well"""
        if win_rate > 0.70:  # 70% threshold
            new_ind = IndicatorStats(
                name=base_name,
                params=new_params,
                win_rate=win_rate
            )
            self.indicators.append(new_ind)
            print(f"✅ Promoted {base_name} {new_params} with {win_rate*100:.1f}% win rate")
    
    def demote_variant(self, name: str, params: Dict):
        """Remove underperforming variant"""
        self.indicators = [
            ind for ind in self.indicators 
            if not (ind.name == name and ind.params == params)
        ]
        print(f"❌ Benched {name} {params}")
    
    def _save_leaderboard(self):
        """Save leaderboard to file"""
        data = {
            'updated': datetime.utcnow().isoformat(),
            'indicators': [asdict(ind) for ind in self.indicators]
        }
        with open(self.leaderboard_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def display_leaderboard(self):
        """Print current leaderboard"""
        print("\n🏆 INDICATOR LEADERBOARD")
        print("=" * 60)
        sorted_inds = sorted(self.indicators, key=lambda x: x.win_rate, reverse=True)
        for i, ind in enumerate(sorted_inds, 1):
            emoji = "🔥" if i <= 3 else "❄️" if i >= 7 else ""
            print(f"{i}. {emoji} {ind.name} {ind.params}")
            print(f"   Trades: {ind.trades}, Win: {ind.win_rate*100:.1f}%, Sharpe: {ind.sharpe:.2f}, PnL: ${ind.pnl:.2f}")
        print("=" * 60)


async def run_arena_simulation():
    """Simulate arena with random trades"""
    arena = IndicatorArena()
    
    import random
    for _ in range(100):
        ind = random.choice(arena.indicators)
        pnl = random.gauss(0.5, 2.0)  # Random PnL
        arena.record_trade(ind.name, ind.params, pnl)
    
    arena.display_leaderboard()
    return arena


if __name__ == '__main__':
    asyncio.run(run_arena_simulation())
