from connors_strategies.strategies.ifr2 import IFR2_Strategy
from connors_strategies.strategies.lcrsi2 import LCRSI2_Strategy
from connors_strategies.strategies.lcrsi2_tpsl import LCRSI2_TPSL_Strategy
from connors_strategies.strategies.lcrsi2_atr import LCRSI2_ATR_Strategy
from connors_strategies.strategies.lcrsi2_talipp import LCRSI2TalippStrategy
from connors_strategies.strategies.lcrsi2_vectorized import LCRSI2VectorizedStrategy
from connors_strategies.strategies.rsi_crypto import (
    RSICryptoStrategy,
    RSICryptoFastStrategy,
    RSICryptoConservativeStrategy,
    RSICryptoNoFilterStrategy
)

# Multi-timeframe strategy support
try:
    from connors_strategies.strategies.multitimeframe import MultiTimeframeStrategy
    __all__ = [
        "LCRSI2_Strategy", "LCRSI2_TPSL_Strategy", "LCRSI2_ATR_Strategy",
        "LCRSI2TalippStrategy", "LCRSI2VectorizedStrategy", "IFR2_Strategy",
        "RSICryptoStrategy", "RSICryptoFastStrategy", "RSICryptoConservativeStrategy", "RSICryptoNoFilterStrategy",
        "MultiTimeframeStrategy"
    ]
except ImportError:
    __all__ = [
        "LCRSI2_Strategy", "LCRSI2_TPSL_Strategy", "LCRSI2_ATR_Strategy",
        "LCRSI2TalippStrategy", "LCRSI2VectorizedStrategy", "IFR2_Strategy",
        "RSICryptoStrategy", "RSICryptoFastStrategy", "RSICryptoConservativeStrategy", "RSICryptoNoFilterStrategy"
    ]
