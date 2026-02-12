"""
📊 MARKET SCANNER AGENT - Head of Market Intelligence
========================================================
Monitorea mercados 24/7, identifica oportunidades y filtra activos prometedores.

Responsabilidades:
- Escaneo continuo de mercados (Coinbase + externos)
- Análisis de volumen, volatilidad, momentum
- Filtrado de señales prometedoras
- Detección de patrones técnicos
- Identificación de tendencias macro
- Ranking de oportunidades por potencial

Author: OpenClaw Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from statistics import mean

# Importar del proyecto
from agents.base_agent import (
    BaseAgent, AgentConfig, AgentMessage, AgentState, 
    MessageType, TaskPriority
)

# Trading libraries
import pandas as pd
import numpy as np
import ccxt

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL SCANNER
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MarketScannerConfig:
    """Configuración del Market Scanner"""
    scan_interval: int = 60  # Segundos entre escaneos
    exchanges: List[str] = field(default_factory=lambda: ["coinbase"])
    watchlist: List[str] = field(default_factory=lambda: [
        "BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", 
        "DOT/USD", "LINK/USD", "AVAX/USD", "MATIC/USD"
    ])
    min_volume_24h: float = 1000000  # Volume mínimo en USD
    min_volatility: float = 0.02  # 2% volatilidad mínima
    max_volatility: float = 0.15  # 15% volatilidad máxima
    scoring_weights: Dict[str, float] = field(default_factory=lambda: {
        "volume": 0.25,
        "momentum": 0.30,
        "volatility": 0.20,
        "trend": 0.25
    })
    alert_threshold: float = 0.7  # Score mínimo para alerta

# ═══════════════════════════════════════════════════════════════════
# SCORING DE OPORTUNIDADES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class OpportunityScore:
    """Score de oportunidad de trading"""
    symbol: str
    exchange: str
    
    # Scores individuales
    volume_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    trend_score: float = 0.0
    
    # Score compuesto
    total_score: float = 0.0
    
    # Métricas
    volume_24h: float = 0.0
    price_change_24h: float = 0.0
    volatility_24h: float = 0.0
    rsi: float = 50.0
    trend_direction: str = "NEUTRAL"
    
    # Datos de precio
    current_price: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "total_score": self.total_score,
            "breakdown": {
                "volume": self.volume_score,
                "momentum": self.momentum_score,
                "volatility": self.volatility_score,
                "trend": self.trend_score
            },
            "metrics": {
                "volume_24h": self.volume_24h,
                "price_change_24h": self.price_change_24h,
                "volatility_24h": self.volatility_24h,
                "rsi": self.rsi,
                "trend_direction": self.trend_direction
            },
            "price": {
                "current": self.current_price,
                "high_24h": self.high_24h,
                "low_24h": self.low_24h
            }
        }

# ═══════════════════════════════════════════════════════════════════
# MARKET SCANNER AGENT
# ═══════════════════════════════════════════════════════════════════

class MarketScannerAgent(BaseAgent):
    """
    Market Scanner - Identifica oportunidades de trading en tiempo real.
    
    Monitorea mercados, analiza métricas clave y genera una lista
    priorizada de activos para análisis adicional.
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        scanner_config = AgentConfig(
            agent_id="MARKET_SCANNER",
            agent_name="Head of Market Intelligence",
            agent_type="ANALYSIS",
            log_level="INFO",
            cycle_interval=60,
            custom_config=config or {}
        )
        
        super().__init__(scanner_config, message_bus)
        
        self.scanner_config = MarketScannerConfig()
        
        # Conexiones a exchanges
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        
        # Estado del scanner
        self.watchlist: List[str] = []
        self.opportunities: List[OpportunityScore] = []
        self.last_scan_time: Optional[datetime] = None
        self.market_regime: str = "UNKNOWN"
        
        # Métricas de mercado
        self.global_market_sentiment: float = 0.5  # 0-1, 0.5 neutral
        self.active_trends: Dict[str, str] = {}
        
        self.logger.info("📊 Market Scanner Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Inicializar conexiones a exchanges"""
        self.logger.info("🚀 Iniciando Market Scanner...")
        
        # Inicializar Coinbase
        try:
            coinbase = ccxt.coinbase({
                'enableRateLimit': True,
                'timeout': 30000
            })
            self.exchanges["coinbase"] = coinbase
            self.logger.info("✅ Coinbase conectado")
        except Exception as e:
            self.logger.error(f"❌ Error conectando a Coinbase: {e}")
        
        # Configurar watchlist
        self.watchlist = self.scanner_config.watchlist.copy()
        
        # Suscribirse a mensajes relevantes
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                task_types=["UPDATE_WATCHLIST", "SCAN_NOW", "GET_OPPORTUNITIES"]
            )
        
        self.logger.info(f"✅ Market Scanner listo. Vigilanfo: {len(self.watchlist)} activos")
    
    async def on_shutdown(self):
        """Cerrar conexiones"""
        self.logger.info("🛑 Deteniendo Market Scanner...")
        for name, exchange in self.exchanges.items():
            try:
                exchange.close()
            except:
                pass
        self.logger.info("✅ Market Scanner detenido")
    
    async def run_cycle(self):
        """Ciclo principal de escaneo"""
        await self._full_market_scan()
    
    # ═══════════════════════════════════════════════════════════════
    # ESCANEO PRINCIPAL
    # ═══════════════════════════════════════════════════════════════
    
    async def _full_market_scan(self):
        """Realizar escaneo completo del mercado"""
        self.logger.info("🔍 Iniciando escaneo de mercado...")
        start_time = datetime.now()
        
        opportunities = []
        
        # Escanear cada símbolo en la watchlist
        for symbol in self.watchlist:
            try:
                score = await self._analyze_symbol(symbol, "coinbase")
                if score:
                    opportunities.append(score)
            except Exception as e:
                self.logger.warning(f"Error analizando {symbol}: {e}")
        
        # Ordenar por score
        opportunities.sort(key=lambda x: x.total_score, reverse=True)
        
        # Guardar resultados
        self.opportunities = opportunities
        self.last_scan_time = datetime.now()
        
        # Loggear top oportunidades
        top_5 = opportunities[:5]
        if top_5:
            self.logger.info(f"📈 Top 5 oportunidades:")
            for i, opp in enumerate(top_5, 1):
                self.logger.info(f"   {i}. {opp.symbol}: {opp.total_score:.2f} ( momentum: {opp.momentum_score:.2f}, vol: {opp.volatility_score:.2f})")
        
        # Enviar alertas si hay oportunidades de alta calidad
        high_quality = [o for o in opportunities if o.total_score >= self.scanner_config.alert_threshold]
        if high_quality:
            await self._alert_high_quality_opportunities(high_quality)
        
        # Determinar régimen de mercado
        await self._detect_market_regime(opportunities)
        
        # Reportar al CEO
        await self._report_to_ceo(opportunities, start_time)
        
        scan_duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"✅ Escaneo completado en {scan_duration:.2f}s | {len(opportunities)} analizados")
    
    async def _analyze_symbol(self, symbol: str, exchange_name: str) -> Optional[OpportunityScore]:
        """Analizar un símbolo específico"""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return None
        
        try:
            # Obtener datos de mercado
            ticker = await self._safe_api_call(
                exchange.fetch_ticker, symbol
            )
            
            if not ticker:
                return None
            
            # Calcular métricas
            volume_24h = ticker.get('quoteVolume', 0)
            price = ticker.get('last', 0)
            high_24h = ticker.get('high', 0)
            low_24h = ticker.get('low', 0)
            price_change_pct = ticker.get('percentage', 0)
            
            # Filtrar por volumen mínimo
            if volume_24h < self.scanner_config.min_volume_24h:
                return None
            
            # Obtener datos históricos para análisis
            ohlcv = await self._safe_api_call(
                exchange.fetch_ohlcv, symbol, '1d', limit=14
            )
            
            # Calcular scores
            score = OpportunityScore(
                symbol=symbol,
                exchange=exchange_name,
                volume_24h=volume_24h,
                price_change_24h=price_change_pct,
                current_price=price,
                high_24h=high_24h,
                low_24h=low_24h
            )
            
            if ohlcv:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                self._calculate_scores(df, score)
            else:
                # Sin datos históricos, usar solo ticker
                score.volume_score = self._score_volume(volume_24h)
                score.momentum_score = self._score_momentum(price_change_pct)
                score.total_score = mean([score.volume_score, score.momentum_score])
            
            return score
            
        except Exception as e:
            self.logger.warning(f"Error analizando {symbol}: {e}")
            return None
    
    def _calculate_scores(self, df: pd.DataFrame, score: OpportunityScore):
        """Calcular scores de oportunidad"""
        weights = self.scanner_config.scoring_weights
        
        # 1. Volume Score
        score.volume_score = self._score_volume(score.volume_24h)
        
        # 2. Momentum Score (basado en RSI y momentum)
        score.momentum_score = self._calculate_momentum_score(df, score.price_change_24h)
        
        # 3. Volatility Score
        daily_returns = df['close'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(365)  # Anualizada
        score.volatility_24h = volatility
        score.volatility_score = self._score_volatility(volatility)
        
        # 4. Trend Score
        trend_data = self._calculate_trend(df)
        score.trend_direction = trend_data["direction"]
        score.trend_score = trend_data["score"]
        score.rsi = trend_data.get("rsi", 50)
        
        # Calcular score total
        score.total_score = (
            weights["volume"] * score.volume_score +
            weights["momentum"] * score.momentum_score +
            weights["volatility"] * score.volatility_score +
            weights["trend"] * score.trend_score
        )
    
    def _score_volume(self, volume: float) -> float:
        """Score basado en volumen (0-1)"""
        if volume < 100000:
            return 0.1
        elif volume < 1000000:
            return 0.3
        elif volume < 10000000:
            return 0.5
        elif volume < 50000000:
            return 0.7
        elif volume < 100000000:
            return 0.85
        else:
            return 1.0
    
    def _score_momentum(self, change_pct: float) -> float:
        """Score basado en momentum (0-1)"""
        # Momentum moderado es mejor
        if change_pct < -20:
            return 0.2  # Caída muy fuerte
        elif change_pct < -10:
            return 0.35
        elif change_pct < -5:
            return 0.5
        elif change_pct < -2:
            return 0.6
        elif change_pct < 2:
            return 0.5  # Sin movimiento
        elif change_pct < 5:
            return 0.65
        elif change_pct < 10:
            return 0.8
        elif change_pct < 20:
            return 0.9
        else:
            return 0.7  # Subida muy fuerte puede ser señal de agotamiento
    
    def _calculate_momentum_score(self, df: pd.DataFrame, price_change: float) -> float:
        """Calcular score de momentum avanzado"""
        if len(df) < 5:
            return 0.5
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        score = 0.5
        
        # RSI extreme oversold - potencial de rebote
        if current_rsi < 25:
            score = 0.75
        elif current_rsi < 35:
            score = 0.7
        elif current_rsi < 45:
            score = 0.6
        elif current_rsi < 55:
            score = 0.55
        elif current_rsi < 65:
            score = 0.6
        elif current_rsi < 75:
            score = 0.65
        elif current_rsi > 75:
            score = 0.5  # Sobrecomprado
        
        # Combinar con precio
        momentum_weight = 0.6
        price_weight = 0.4
        
        price_score = self._score_momentum(price_change)
        
        return momentum_weight * score + price_weight * price_score
    
    def _score_volatility(self, volatility: float) -> float:
        """Score basado en volatilidad (0-1)"""
        # Buscamos volatilidad moderada
        min_vol = self.scanner_config.min_volatility
        max_vol = self.scanner_config.max_volatility
        
        if volatility < min_vol:
            return 0.2  # Muy poca volatilidad
        elif volatility < min_vol * 1.5:
            return 0.5
        elif volatility < max_vol * 0.7:
            return 0.8  # Volatilidad ideal
        elif volatility < max_vol:
            return 0.7
        else:
            return 0.3  # Demasiada volatilidad
    
    def _calculate_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcular score de tendencia"""
        if len(df) < 10:
            return {"direction": "NEUTRAL", "score": 0.5, "rsi": 50}
        
        # SMA comparison
        sma_fast = df['close'].rolling(window=10).mean().iloc[-1]
        sma_slow = df['close'].rolling(window=20).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Determinar dirección
        if current_price > sma_fast > sma_slow:
            direction = "BULLISH"
            score = 0.8
        elif current_price < sma_fast < sma_slow:
            direction = "BEARISH"
            score = 0.7
        elif sma_fast > sma_slow:
            direction = "WEAK_BULLISH"
            score = 0.55
        elif sma_fast < sma_slow:
            direction = "WEAK_BEARISH"
            score = 0.45
        else:
            direction = "NEUTRAL"
            score = 0.5
        
        # Ajustar score con RSI
        if direction.startswith("BULLISH") and 50 < rsi < 70:
            score = min(1.0, score + 0.1)
        elif direction.startswith("BEARISH") and 30 < rsi < 50:
            score = min(1.0, score + 0.1)
        
        return {"direction": direction, "score": score, "rsi": rsi}
    
    # ═══════════════════════════════════════════════════════════════
    # ALERTAS Y REPORTING
    # ═══════════════════════════════════════════════════════════════
    
    async def _alert_high_quality_opportunities(self, opportunities: List[OpportunityScore]):
        """Alertar sobre oportunidades de alta calidad"""
        self.logger.info(f"🚨 {len(opportunities)} oportunidades de ALTA CALIDAD detectadas")
        
        # Enviar al CEO
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="HIGH_QUALITY_OPPORTUNITIES",
            priority=TaskPriority.HIGH,
            payload={
                "opportunities": [o.to_dict() for o in opportunities],
                "count": len(opportunities),
                "timestamp": datetime.now().isoformat()
            }
        ))
        
        # Enviar al Analyst para análisis profundo
        await self.send_message(self.create_task_message(
            to_agent="ANALYST",
            task_type="DEEP_ANALYSIS_REQUEST",
            priority=TaskPriority.NORMAL,
            payload={
                "symbols": [o.symbol for o in opportunities],
                "priority": "HIGH"
            }
        ))
    
    async def _detect_market_regime(self, opportunities: List[OpportunityScore]):
        """Detectar régimen actual del mercado"""
        if not opportunities:
            self.market_regime = "UNKNOWN"
            return
        
        # Calcular distribución de tendencias
        trends = [o.trend_direction for o in opportunities]
        bullish_count = sum(1 for t in trends if "BULL" in t)
        bearish_count = sum(1 for t in trends if "BEAR" in t)
        total = len(trends)
        
        bullish_ratio = bullish_count / total
        bearish_ratio = bearish_count / total
        
        # Determinar régimen
        if bullish_ratio > 0.6:
            self.market_regime = "STRONG_BULL"
            self.global_market_sentiment = 0.75
        elif bullish_ratio > 0.4:
            self.market_regime = "BULLISH"
            self.global_market_sentiment = 0.6
        elif bearish_ratio > 0.6:
            self.market_regime = "STRONG_BEAR"
            self.global_market_sentiment = 0.25
        elif bearish_ratio > 0.4:
            self.market_regime = "BEARISH"
            self.global_market_sentiment = 0.4
        else:
            self.market_regime = "NEUTRAL"
            self.global_market_sentiment = 0.5
        
        self.active_trends = {
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": total - bullish_count - bearish_count
        }
        
        self.logger.info(f"📊 Régimen de mercado: {self.market_regime} | Sentimiento: {self.global_market_sentiment:.2f}")
    
    async def _report_to_ceo(self, opportunities: List[OpportunityScore], start_time: datetime):
        """Reportar resultados al CEO"""
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="MARKET_SCAN_COMPLETE",
            priority=TaskPriority.NORMAL,
            payload={
                "scan_duration": (datetime.now() - start_time).total_seconds(),
                "symbols_scanned": len(opportunities),
                "top_opportunity": opportunities[0].to_dict() if opportunities else None,
                "market_regime": self.market_regime,
                "sentiment": self.global_market_sentiment,
                "timestamp": datetime.now().isoformat()
            }
        ))
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes entrantes"""
        
        if message.task_type == "UPDATE_WATCHLIST":
            return await self._handle_update_watchlist(message)
        
        elif message.task_type == "SCAN_NOW":
            return await self._handle_scan_now(message)
        
        elif message.task_type == "GET_OPPORTUNITIES":
            return self._handle_get_opportunities(message)
        
        return None
    
    async def _handle_update_watchlist(self, message: AgentMessage) -> AgentMessage:
        """Actualizar watchlist"""
        new_symbols = message.payload.get("symbols", [])
        action = message.payload.get("action", "REPLACE")  # REPLACE, ADD, REMOVE
        
        if action == "REPLACE":
            self.watchlist = new_symbols
        elif action == "ADD":
            self.watchlist.extend([s for s in new_symbols if s not in self.watchlist])
        elif action == "REMOVE":
            self.watchlist = [s for s in self.watchlist if s not in new_symbols]
        
        self.logger.info(f"📝 Watchlist actualizada: {len(self.watchlist)} símbolos")
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "watchlist_size": len(self.watchlist),
                "symbols": self.watchlist
            }
        )
    
    async def _handle_scan_now(self, message: AgentMessage) -> AgentMessage:
        """Iniciar escaneo inmediato"""
        priority = message.payload.get("priority", "NORMAL")
        self.logger.info(f"🔍 Escaneo inmediato solicitado ({priority})")
        
        # Ejecutar escaneo
        await self._full_market_scan()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "scan_completed": True,
                "opportunities_found": len(self.opportunities),
                "top_score": self.opportunities[0].total_score if self.opportunities else 0
            }
        )
    
    def _handle_get_opportunities(self, message: AgentMessage) -> AgentMessage:
        """Obtener oportunidades actuales"""
        filters = message.payload or {}
        
        filtered = self.opportunities
        
        # Filtrar por score mínimo
        min_score = filters.get("min_score", 0)
        filtered = [o for o in filtered if o.total_score >= min_score]
        
        # Filtrar por tendencia
        trend = filters.get("trend")
        if trend:
            filtered = [o for o in filtered if trend in o.trend_direction]
        
        # Limitar cantidad
        limit = filters.get("limit", 10)
        filtered = filtered[:limit]
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "opportunities": [o.to_dict() for o in filtered],
                "total_count": len(filtered),
                "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
                "market_regime": self.market_regime
            }
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    async def _safe_api_call(self, func, *args, **kwargs):
        """Llamada segura a API con manejo de errores"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        except ccxt.RateLimitExceeded:
            self.logger.warning("Rate limit alcanzado, esperando...")
            await asyncio.sleep(5)
            return None
        except ccxt.NetworkError as e:
            self.logger.error(f"Error de red: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Error en API: {e}")
            return None
    
    def get_scanner_status(self) -> Dict[str, Any]:
        """Obtener estado del scanner"""
        return {
            "watchlist_size": len(self.watchlist),
            "opportunities_found": len(self.opportunities),
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "market_regime": self.market_regime,
            "sentiment": self.global_market_sentiment,
            "exchanges_connected": list(self.exchanges.keys()),
            "active_trends": self.active_trends
        }
    
    def __repr__(self) -> str:
        return f"<MarketScanner(regime={self.market_regime}, opportunities={len(self.opportunities)})>"
