# Dune Momentum Traders Research - Solana Edition 🐻

**Mission**: Reverse-engineer top 30 most profitable momentum traders on Solana. Analyze their:
- Trading style & selection criteria
- Position sizing & risk management
- Holding periods & exit strategies
- Token categories & timing
- On-chain transaction patterns

**Methodology**:
1. Find top Dune dashboards → extract top wallets
2. For each wallet → deep tx analysis (Solscan/Dune queries)
3. Document patterns → build statistical profile
4. Update after each trader → avoid context overflow

**API Key**: `bCzNyXIzqXcSatjVOxkJtB3voY1IIv5D` (TOOLS.md)

**Status**: Dune.com blocked by Cloudflare (403). API calls failing (no results).

---

## 📊 Key Dashboards Found (Web Research)

### 1. **Solana Top Traders** - 0xverin
- https://dune.com/0xverin/solana-top-traders
- Query ID attempt: 3194115 → No data

### 2. **Top Traders** - couldbebasic
- https://dune.com/couldbebasic/top-traders
- Copy-trading leaderboard

### 3. **Solana Alpha Wallet Signals** - pixelz
- https://dune.com/pixelz/solana-alpha-wallet-signals
- Trojan/bullX/photon bot traders

### 4. **Solmemecoins Profitable Wallets** - maditim
- https://dune.com/maditim/solmemecoinstradewallets

### 5. **Sol Trading Bot Analysis** - Query 3832067
- Top traders by volume

## 🔍 Dune API Issues
```
curl -H \"X-Dune-API-Key: ...\" → Empty responses
Cloudflare blocking browser access
Need: Working query IDs or dashboard exports
```

## 🛠️ Pivot Plan
1. **Solscan wallet leaderboards** (public PnL rankings)
2. **DexScreener top traders** (volume-based)
3. **Twitter alpha calls** (public wallet lists)
4. **Manual Dune query execution** via API

**Next**: Extracting from Solscan + DexScreener top 30 wallets.

--- 

*Updated: `2026-02-23 18:35 UTC`*"
