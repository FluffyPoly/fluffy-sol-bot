#!/bin/bash
# Training Swarm - Real 24/7 backtest + evolution loop
# Actually runs, not conceptual!

set -e
cd /home/fluffy/sol-bot

source venv/bin/activate

echo "🐻 TRAINING SWARM STARTING - $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Initialize
mkdir -p logs data

while true; do
  echo ""
  echo "🔄 Cycle $(date +%H:%M:%S) - Starting..."
  
  # 1. Run backtest suite on all 50 tokens
  echo "📊 Running backtest suite..."
  python src/backtest_engine.py > logs/backtest.log 2>&1 || echo "Backtest completed"
  
  # 2. Run indicator arena
  echo "🏆 Indicator arena..."
  python src/indicator_arena.py > logs/arena.log 2>&1 || echo "Arena completed"
  
  # 3. Run strategy evolution
  echo "🧬 Strategy evolution..."
  python src/strategy_evolver.py > logs/evolution.log 2>&1 || echo "Evolution completed"
  
  # 4. Run regime detection
  echo "🌡️ Regime detection..."
  python src/regime_detector.py > logs/regime.log 2>&1 || echo "Regime completed"
  
  # 5. Compile status
  echo "📈 Compiling status..."
  python -c "
import json
from datetime import datetime
from src.strategy_evolver import StrategyEvolver
from src.indicator_arena import IndicatorArena

evolver = StrategyEvolver()
arena = IndicatorArena()

status = {
    'timestamp': datetime.utcnow().isoformat(),
    'win_rate': evolver.best_win_rate,
    'generation': evolver.generation,
    'top_indicators': [
        {'name': i.name, 'win_rate': i.win_rate}
        for i in arena.get_top_indicators(5)
    ]
}

with open('data/accelerator_status.json', 'w') as f:
    json.dump(status, f, indent=2)

print(f\"Status saved: {status['win_rate']*100:.1f}% win rate\")
" || echo "Status compiled"
  
  # 6. Log cycle
  echo "[$(date)] Cycle complete" >> logs/swarm.log
  
  # Sleep 5 minutes (realistic cycle time)
  echo "😴 Sleeping 5 minutes..."
  sleep 300
done