#!/bin/bash
# Solana Momentum Accelerator - 24/7 AI Training Script
# Runs continuously, learns/practices 100x faster than human

set -e

cd /home/fluffy/sol-bot

echo \"🐻 Solana Momentum Accelerator Started - 24/7 Mode\"

while true; do
  echo \"[$(date)] Cycle starting...\"
  
  # 1. Live market data pull (Birdeye free API)
  echo \"📊 Fetching live SOL/RAY/JUP data...\"
  curl -s \"https://public-api.birdeye.so/defi/price?address=So11111111111111111111111111111111111111112\" > data/sol_price.json
  
  # 2. Chart analysis simulation (TradingView ideas scraping)
  echo \"📈 Analyzing momentum setups...\"
  curl -s \"https://www.tradingview.com/symbols/SOLUSD/ideas/\" | grep -oP '(?<=SOLUSD).*?(?=USD)' > data/tv_ideas.txt
  
  # 3. Backtest 100 historical setups
  echo \"🔄 Backtesting 100 SOL setups...\"
  python src/backtest_accelerator.py
  
  # 4. Journal update + pattern recognition
  echo \"📚 Updating trading journal...\"
  python src/pattern_learner.py
  
  # 5. Performance metrics
  echo \"📊 Metrics update...\"
  python src/performance_tracker.py
  
  # Sleep 10min (24 cycles/day)
  sleep 600
done