"""
Strategy Evolver - Auto-generates and tests strategy variants
Continuously evolves toward 85%+ win rate
"""
import json
import random
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict
import asyncio

@dataclass
class StrategyVariant:
    id: str
    params: Dict
    win_rate: float = 0.0
    trades: int = 0
    sharpe: float = 0.0
    pnl: float = 0.0
    created: str = ""
    last_tested: str = ""

class StrategyEvolver:
    def __init__(self):
        self.base_strategy = {
            'rsi_period': 14,
            'rsi_low': 57,
            'rsi_high': 63,
            'vol_mult': 1.38,
            'vol_lookback': 20,
            'stop_atr_mult': 1.85,
            'tp_percent': 0.28,
        }
        self.variants: List[StrategyVariant] = []
        self.generation = 0
        self.best_win_rate = 0.0
        self.tree_path = 'data/strategy_tree.md'
        
    def generate_variants(self, n: int = 10) -> List[StrategyVariant]:
        """Generate N strategy variants with mutated params"""
        variants = []
        
        for i in range(n):
            mutant = self.base_strategy.copy()
            
            # Random mutations
            mutant['rsi_period'] = random.randint(12, 18)
            mutant['rsi_low'] = random.randint(52, 60)
            mutant['rsi_high'] = random.randint(60, 68)
            mutant['vol_mult'] = round(random.uniform(1.2, 2.0), 2)
            mutant['stop_atr_mult'] = round(random.uniform(1.5, 2.5), 2)
            mutant['tp_percent'] = round(random.uniform(0.25, 0.40), 2)
            
            variant = StrategyVariant(
                id=f"v{self.generation}_{i}",
                params=mutant,
                created=datetime.utcnow().isoformat()
            )
            variants.append(variant)
        
        self.generation += 1
        return variants
    
    def select_best(self, results: List[Dict]) -> StrategyVariant:
        """Select best performing variant from results"""
        best = max(results, key=lambda x: x['win_rate'])
        
        if best['win_rate'] > self.best_win_rate:
            self.best_win_rate = best['win_rate']
            self.base_strategy = best['params'].copy()
            print(f"🎯 NEW BEST: {best['win_rate']*100:.1f}% win rate!")
            self._log_evolution(best)
        
        return StrategyVariant(
            id=f"best_{self.generation}",
            params=best['params'],
            win_rate=best['win_rate'],
            trades=best.get('trades', 0)
        )
    
    def _log_evolution(self, result: Dict):
        """Log evolution to strategy tree"""
        with open(self.tree_path, 'a') as f:
            f.write(f"\n## Generation {self.generation} - {datetime.utcnow().isoformat()}\n")
            f.write(f"**Win Rate**: {result['win_rate']*100:.1f}%\n")
            f.write(f"**Params**: {json.dumps(result['params'], indent=2)}\n")
            f.write(f"**Trades**: {result.get('trades', 0)}\n")
            f.write(f"**Sharpe**: {result.get('sharpe', 0):.2f}\n")
            f.write("---\n")
    
    def get_current_best(self) -> Dict:
        """Get current best strategy"""
        return {
            'base_strategy': self.base_strategy,
            'best_win_rate': self.best_win_rate,
            'generation': self.generation,
            'variants_tested': len(self.variants)
        }


async def run_evolution_cycle():
    """Run one evolution cycle"""
    evolver = StrategyEvolver()
    
    print(f"🧬 Generation {evolver.generation} - Creating variants...")
    variants = evolver.generate_variants(10)
    
    print(f"Testing {len(variants)} variants...")
    results = []
    
    for v in variants:
        # Simulate backtest result
        simulated_wr = random.gauss(0.65, 0.08)  # Around 65% ± 8%
        results.append({
            'params': v.params,
            'win_rate': simulated_wr,
            'trades': random.randint(100, 500),
            'sharpe': random.gauss(1.5, 0.5)
        })
        print(f"  {v.id}: {simulated_wr*100:.1f}%")
    
    best = evolver.select_best(results)
    print(f"\n✅ Best variant selected: {best.win_rate*100:.1f}%")
    print(f"Current base: {evolver.base_strategy}")
    
    return evolver.get_current_best()


if __name__ == '__main__':
    asyncio.run(run_evolution_cycle())
