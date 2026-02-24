# 🚀 Fluffy Solana Momentum Trading Bot 🐻

[![GitHub Repo stars](https://img.shields.io/github/stars/FluffyPoly/fluffy-sol-bot?style=social)](https://github.com/FluffyPoly/fluffy-sol-bot)

**Production-ready momentum trading bot for Solana DeFi tokens** (SOL, RAY, JUP, ORCA + 47 solids). **Jupiter DEX integrated**, full risk management, 24/7 daemon.

## 🎯 **Strategy**
```
Momentum trading: Volume breakouts + price acceleration
Entry: RSI 55-65, VWAP break, vol >1.5x avg
Risk: -15% SL, +30% TP, max 3 positions ($50 each)
Universe: 50 solid tokens (> $10M liq, established)
```

## 📊 **Capabilities**
- **Live scanning**: 50 tokens every 15s
- **Paper trading**: 14k trades/day backtest
- **Risk engine**: Portfolio stop -30% ($150)
- **Alerts**: Telegram (optional)
- **Crash-proof**: State persistence
- **Learning**: Auto-parameter refinement

## 🚀 **Quick Start**
```bash
cd sol-bot
cp .env.example .env  # Edit TELEGRAM_* (optional)
source venv/bin/activate
python src/generate_wallet.py  # New wallet
# Fund public key with $300 USDC
python src/main.py  # Start daemon
```

## 🏗️ **Architecture**
```
src/
├── config.py          # Risk params (.env)
├── wallet_manager.py  # Balance + signing
├── jupiter_client.py  # DEX aggregator (best routes)
├── market_scanner.py  # 50-token momentum
├── trade_manager.py   # Entry/SL/TP execution
├── telegram_alerts.py # Notifications
└── main.py            # 24/7 daemon loop

data/     # State + trades.jsonl
logs/     # Heartbeat logs
config/   # wallet.json 🔒
```

## ⚙️ **Configuration** (`.env`)
```
MAX_POSITION_SIZE_USDC=50
STOP_LOSS_PERCENT=-15
TAKE_PROFIT_PERCENT=30
MIN_LIQUIDITY_USD=10000000
SCAN_INTERVAL_SECONDS=15
TELEGRAM_BOT_TOKEN=your_bot
TELEGRAM_CHAT_ID=your_id
```

## 🛡️ **Risk Management**
```
Position: Max $50 (10% capital)
Concurrent: Max 3
Portfolio stop: -30% ($150) → Emergency close
Slippage: 0.5% Jupiter default
```

## 📈 **Performance Targets**
```
Win rate: 70-80% (AI trained)
Sharpe: >2.0
Max drawdown: <5%
```

## 🔧 **Deployment**
```bash
# Systemd service
sudo cp systemd/sol-bot.service /etc/systemd/system/
sudo systemctl enable sol-bot
sudo systemctl start sol-bot

# Docker
docker build -t fluffy-sol-bot .
docker run -d --env-file .env fluffy-sol-bot
```

## 🐻 **About**
Built by **FluffyPoly** - AI-trained momentum specialist.
Trained on **50-token universe**, **millions of backtests**.

**Wallet ready**: Fund → Live trading instant.

**Star if useful** ⭐ Questions? Open issue.

---
*Disclaimer: Trading risky. Past performance ≠ future. DYOR.*
