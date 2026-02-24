"""
Regime Detector - Identifies market regime (bull/bear/chop)
Switches strategies based on conditions
"""
import json
from datetime import datetime
from typing import Dict, List
import asyncio

class RegimeDetector:
    def __init__(self):
        self.current_regime = 'unknown'
        self.regime_history = []
        self.confidence = 0.0
        
        # Regime thresholds
        self.bull_threshold = 0.6  # 60% bullish signals
        self.bear_threshold = 0.4  # 40% bullish signals (below = bear)
        
    def detect(self, candles: List[Dict]) -> str:
        """Detect current market regime from candle data"""
        if len(candles) < 50:
            return 'unknown'
        
        signals = {
            'trend': self._trend_signal(candles),
            'volatility': self._volatility_signal(candles),
            'momentum': self._momentum_signal(candles),
            'volume': self._volume_signal(candles)
        }
        
        # Calculate bullish score (0-1)
        bullish_score = sum(signals.values()) / len(signals)
        self.confidence = max(signals.values()) - min(signals.values())  # Agreement level
        
        if bullish_score > self.bull_threshold:
            regime = 'bull'
        elif bullish_score < self.bear_threshold:
            regime = 'bear'
        else:
            regime = 'chop'
        
        if regime != self.current_regime:
            print(f"🔄 REGIME SHIFT: {self.current_regime} → {regime} (confidence: {self.confidence:.2f})")
            self.current_regime = regime
            self._log_regime(regime, bullish_score, signals)
        
        return regime
    
    def _trend_signal(self, candles: List[Dict]) -> float:
        """1.0 = strong uptrend, 0.0 = strong downtrend"""
        closes = [c['close'] for c in candles[-50:]]
        
        # Simple: higher highs + higher lows = uptrend
        recent_high = max(closes[-20:])
        prev_high = max(closes[-50:-20])
        
        recent_low = min(closes[-20:])
        prev_low = min(closes[-50:-20])
        
        score = 0.5
        if recent_high > prev_high:
            score += 0.25
        if recent_low > prev_low:
            score += 0.25
        
        return score
    
    def _volatility_signal(self, candles: List[Dict]) -> float:
        """1.0 = low vol (stable), 0.0 = high vol (chaotic)"""
        closes = [c['close'] for c in candles[-50:]]
        
        # Calculate ATR-like measure
        changes = [abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        avg_change = sum(changes) / len(changes)
        
        # Low vol = bullish (stable growth)
        if avg_change < 0.02:  # <2% daily moves
            return 1.0
        elif avg_change > 0.05:  # >5% daily moves
            return 0.0
        else:
            return 0.5
    
    def _momentum_signal(self, candles: List[Dict]) -> float:
        """1.0 = strong momentum up, 0.0 = momentum down"""
        closes = [c['close'] for c in candles[-50:]]
        
        # RSI-like momentum
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        
        if avg_loss == 0:
            return 1.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi / 100  # Normalize to 0-1
    
    def _volume_signal(self, candles: List[Dict]) -> float:
        """1.0 = volume increasing (bullish), 0.0 = decreasing"""
        volumes = [c['volume'] for c in candles[-50:]]
        
        recent_vol = sum(volumes[-20:]) / 20
        prev_vol = sum(volumes[-50:-20]) / 30
        
        if recent_vol > prev_vol * 1.2:  # 20% increase
            return 1.0
        elif recent_vol < prev_vol * 0.8:  # 20% decrease
            return 0.0
        else:
            return 0.5
    
    def _log_regime(self, regime: str, score: float, signals: Dict):
        """Log regime change"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'regime': regime,
            'bullish_score': score,
            'confidence': self.confidence,
            'signals': signals
        }
        self.regime_history.append(entry)
        
        with open('data/regime_changes.jsonl', 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def get_strategy_for_regime(self) -> Dict:
        """Return optimal strategy params for current regime"""
        strategies = {
            'bull': {
                'bias': 'long',
                'rsi_low': 55,
                'rsi_high': 65,
                'vol_mult': 1.3,
                'position_size': 0.15  # 15% capital
            },
            'bear': {
                'bias': 'short',
                'rsi_low': 40,
                'rsi_high': 50,
                'vol_mult': 1.5,
                'position_size': 0.08  # 8% capital (riskier)
            },
            'chop': {
                'bias': 'neutral',
                'rsi_low': 50,
                'rsi_high': 55,
                'vol_mult': 1.8,
                'position_size': 0.05  # 5% capital (conservative)
            },
            'unknown': {
                'bias': 'neutral',
                'rsi_low': 57,
                'rsi_high': 63,
                'vol_mult': 1.38,
                'position_size': 0.0
            }
        }
        return strategies.get(self.current_regime, strategies['unknown'])
    
    def get_status(self) -> Dict:
        """Get regime detector status"""
        return {
            'current_regime': self.current_regime,
            'confidence': self.confidence,
            'recommended_strategy': self.get_strategy_for_regime(),
            'history_count': len(self.regime_history)
        }


async def test_regime_detector():
    """Test with simulated data"""
    detector = RegimeDetector()
    
    # Simulated candles
    import random
    candles = [
        {'close': 100 + i + random.gauss(0, 2), 'volume': 1000000 + random.randint(-100000, 100000)}
        for i in range(100)
    ]
    
    regime = detector.detect(candles)
    print(f"Detected regime: {regime}")
    print(f"Status: {detector.get_status()}")


if __name__ == '__main__':
    asyncio.run(test_regime_detector())
