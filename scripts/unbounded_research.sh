#!/bin/bash
# Unbounded Solana Trading Research - No Boundaries Mode 🐻
# Explores ALL strategies, shorts, market regime detection, alpha hunting

cd /home/fluffy/sol-bot

echo \"🐻 Unbounded Research Started - Digging DEEP...\"

while true; do
  echo \"[$(date)] Unbounded cycle...\"
  
  # 1. Market regime detection (bull/bear/sideways)
  echo \"🌡️ Detecting market regime...\"
  curl -s \"https://api.birdeye.so/v1/market/regime?chain=solana\" > data/regime.json
  
  # 2. Alpha hunting - NEW sources daily
  echo \"🧠 Alpha research...\"
  curl -s \"https://api.twitter.com/2/search/recent?query=solana trading strategy -meme\" > data/twitter_alpha.json
  
  # 3. Short signals research (bearish momentum)
  echo \"📉 Short opportunity scan...\"
  python src/short_scanner.py
  
  # 4. Advanced TA - Regime-specific
  echo \"🎯 Regime-optimized setups...\"
  python src/regime_trader.py
  
  # 5. Global best practices (papers/forums)
  echo \"📚 Deep research...\"
  curl -s \"arxiv.org/search/?query=solana+trading&searchtype=all\" > data/research_papers.txt
  
  # 6. Live validation
  echo \"✅ Live validation...\"
  python src/validate_strategies.py
  
  sleep 900  # 15min cycles (96/day)
done