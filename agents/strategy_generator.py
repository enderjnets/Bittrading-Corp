"""
🧪 STRATEGY GENERATOR AGENT - Chief Strategy Officer
======================================================
Genera, diseña y crea estrategias de trading únicas.

Responsabilidades:
- Generación de ideas de estrategias
- Diseño de reglas de entrada/salida
- Configuración de parámetros
- Diseño de money management
- Innovación en enfoques de trading
- Búsqueda de edge en el mercado

Author: OpenClaw Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from agents.base_agent import (
    BaseAgent, AgentConfig, AgentMessage, AgentState, 
    MessageType, TaskPriority
)

# ═══════════════════════════════════════════════════════════════════
# ENUMS Y ESTRUCTURAS
# ═══════════════════════════════════════════════════════════════════

class StrategyType(Enum):
    """Tipos de estrategias"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"
    SCALPING = "scalping"
    VOLATILITY = "volatility"
    ARBITRAGE = "arbitrage"
    PATTERN = "pattern"

class IndicatorType(Enum):
    """Tipos de indicadores disponibles"""
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"
    SMA = "sma"
    EMA = "ema"
    ATR = "atr"
    VOLUME = "volume"
    VWAP = "vwap"
    STOCHASTIC = "stochastic"
    ADX = "adx"

@dataclass
class StrategyTemplate:
    """Template para generación de estrategias"""
    strategy_type: StrategyType
    name_prefix: str
    description: str
    base_parameters: Dict[str, Any]
    indicator_combos: List[List[IndicatorType]]
    entry_rules: List[str]
    exit_rules: List[str]
    risk_rules: Dict[str, Any]

@dataclass
class GeneratedStrategy:
    """Estrategia generada"""
    strategy_id: str
    strategy_name: str
    strategy_type: str
    description: str
    parameters: Dict[str, Any]
    rules: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    generation_method: str  # "random", "template", "evolved"

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

@dataclass
class StrategyGeneratorConfig:
    """Configuración del generator"""
    generation_interval: int = 3600  # Generar cada hora
    strategies_per_batch: int = 5
    max_active_strategies: int = 50
    mutation_rate: float = 0.2
    crossover_rate: float = 0.3
    exploration_vs_exploitation: float = 0.3  # 0 = todo explotación, 1 = exploración
    enable_templates: bool = True
    enable_random: bool = True
    enable_evolution: bool = True

# ═══════════════════════════════════════════════════════════════════
# TEMPLATES DE ESTRATEGIAS
# ═══════════════════════════════════════════════════════════════════

STRATEGY_TEMPLATES = [
    StrategyTemplate(
        strategy_type=StrategyType.MOMENTUM,
        name_prefix="Momentum",
        description="Estrategia basada en fortaleza de tendencia",
        base_parameters={
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "sma_fast": 10,
            "sma_slow": 20,
            "atr_period": 14,
            "atr_multiplier": 2.0
        },
        indicator_combos=[
            [IndicatorType.RSI, IndicatorType.SMA],
            [IndicatorType.MACD, IndicatorType.RSI],
            [IndicatorType.ADX, IndicatorType.RSI]
        ],
        entry_rules=[
            "RSI cruza sobre nivel de sobreventa",
            "Precio cierra sobre SMA rápida",
            "ADX indica tendencia fuerte"
        ],
        exit_rules=[
            "RSI cruza sobre nivel de sobrecompra",
            "Precio cierra bajo SMA rápida",
            "Stop loss por ATR"
        ],
        risk_rules={
            "stop_loss_type": "atr",
            "stop_loss_multiplier": 2.0,
            "take_profit_type": "reward_risk",
            "reward_risk_ratio": 2.0,
            "max_position_size": 0.05
        }
    ),
    
    StrategyTemplate(
        strategy_type=StrategyType.MEAN_REVERSION,
        name_prefix="MeanRev",
        description="Estrategia basada en reversión a la media",
        base_parameters={
            "bollinger_period": 20,
            "bollinger_std": 2.0,
            "bbands_deviation": 2,
            "rsi_period": 14,
            "lookback_period": 20
        },
        indicator_combos=[
            [IndicatorType.BOLLINGER, IndicatorType.RSI],
            [IndicatorType.VWAP, IndicatorType.VOLUME],
            [IndicatorType.SMA, IndicatorType.VOLUME]
        ],
        entry_rules=[
            "Precio toca banda inferior de Bollinger",
            "RSI en territorio de sobreventa",
            "Volumen por debajo del promedio"
        ],
        exit_rules=[
            "Precio toca banda media de Bollinger",
            "RSI vuelve a nivel neutral",
            "Ratio riesgo/recompensa alcanzado"
        ],
        risk_rules={
            "stop_loss_type": "percentage",
            "stop_loss_multiplier": 0.02,
            "take_profit_type": "percentage",
            "take_profit_multiplier": 0.04,
            "max_position_size": 0.03
        }
    ),
    
    StrategyTemplate(
        strategy_type=StrategyType.BREAKOUT,
        name_prefix="Breakout",
        description="Estrategia de rupturas de rango",
        base_parameters={
            "lookback_period": 20,
            "volume_multiplier": 1.5,
            "atr_period": 14,
            "consolidation_threshold": 0.02
        },
        indicator_combos=[
            [IndicatorType.VOLUME, IndicatorType.ATR],
            [IndicatorType.SMA, IndicatorType.VOLUME],
            [IndicatorType.BOLLINGER, IndicatorType.VOLUME]
        ],
        entry_rules=[
            "Precio rompe resistencia con volumen",
            "Rango de consolidación cerrado",
            "Volumen por encima del promedio"
        ],
        exit_rules=[
            "Stop loss por debajo de soporte",
            "Objetivo de precio alcanzado",
            "Reversión de volumen"
        ],
        risk_rules={
            "stop_loss_type": "swing",
            "swing_period": 5,
            "take_profit_type": "swing",
            "reward_risk_ratio": 2.5,
            "max_position_size": 0.04
        }
    ),
    
    StrategyTemplate(
        strategy_type=StrategyType.TREND_FOLLOWING,
        name_prefix="TrendFollow",
        description="Seguidor de tendencias",
        base_parameters={
            "ema_fast": 9,
            "ema_slow": 21,
            "atr_period": 14,
            "trailing_stop_atr": 3.0,
            "trend_confirmation": 2
        },
        indicator_combos=[
            [IndicatorType.EMA, IndicatorType.ATR],
            [IndicatorType.MACD, IndicatorType.EMA],
            [IndicatorType.SMA, IndicatorType.ADX]
        ],
        entry_rules=[
            "EMA rápida cruza sobre EMA lenta",
            "Precio sobre EMA lenta",
            "ADX indica tendencia"
        ],
        exit_rules=[
            "EMA rápida cruza bajo EMA lenta",
            "Trailing stop activado",
            "Cambio de régimen detectado"
        ],
        risk_rules={
            "stop_loss_type": "trailing",
            "trailing_stop_type": "atr",
            "trailing_stop_atr_multiplier": 3.0,
            "max_position_size": 0.06
        }
    ),
    
    StrategyTemplate(
        strategy_type=StrategyType.VOLATILITY,
        name_prefix="Volatility",
        description="Estrategia basada en contracción/explosión de volatilidad",
        base_parameters={
            "bbands_period": 20,
            "bbands_squeeze_threshold": 0.1,
            "atr_period": 14,
            "volatility_lookback": 20,
            "breakout_confirmation": 3
        },
        indicator_combos=[
            [IndicatorType.BOLLINGER, IndicatorType.ATR],
            [IndicatorType.VOLATILITY, IndicatorType.VOLUME]
        ],
        entry_rules=[
            "Bollinger Bands en squeeze",
            "ATR bajo comparado con histórico",
            "Volumen aumentando"
        ],
        exit_rules=[
            "Bandas se expanden significativamente",
            "Objetivo de volatilidad alcanzado",
            "Stop por volatilidad"
        ],
        risk_rules={
            "stop_loss_type": "volatility",
            "volatility_multiplier": 2.0,
            "take_profit_type": "volatility",
            "volatility_target": 2.5,
            "max_position_size": 0.02
        }
    )
]

# ═══════════════════════════════════════════════════════════════════
# STRATEGY GENERATOR AGENT
# ═══════════════════════════════════════════════════════════════════

class StrategyGeneratorAgent(BaseAgent):
    """
    Strategy Generator - Creador de estrategias de trading.
    
    Utiliza múltiples métodos para generar estrategias:
    - Templates predefinidos (modificados)
    - Generación aleatoria
    - Algoritmos evolutivos
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        generator_config = AgentConfig(
            agent_id="STRATEGY_GENERATOR",
            agent_name="Chief Strategy Officer",
            agent_type="GENERATOR",
            log_level="INFO",
            cycle_interval=3600,
            custom_config=config or {}
        )
        
        super().__init__(generator_config, message_bus)
        
        self.gen_config = StrategyGeneratorConfig()
        
        # Base de estrategias generadas
        self.generated_strategies: List[GeneratedStrategy] = []
        self.strategy_history: List[GeneratedStrategy] = []
        
        # Contadores
        self.total_generated = 0
        self.total_submitted = 0
        self.total_rejected = 0
        
        # Database
        from shared.database import get_database, Strategy as DBStrategy
        self.db = get_database()
        self.DBStrategy = DBStrategy
        
        self.logger.info("🧪 Strategy Generator Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Inicializar generator"""
        self.logger.info("🚀 Iniciando Strategy Generator...")
        
        # Suscribirse a mensajes relevantes
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                task_types=[
                    "GENERATE_STRATEGIES",
                    "GENERATE_FROM_TEMPLATE",
                    "EVOLVE_STRATEGY",
                    "GET_STRATEGIES",
                    "GET_STRATEGY_STATUS"
                ]
            )
        
        # Cargar estrategias existentes de DB
        await self._load_existing_strategies()
        
        self.logger.info("✅ Strategy Generator listo")
    
    async def on_shutdown(self):
        """Shutdown"""
        self.logger.info("🛑 Deteniendo Strategy Generator...")
        self.logger.info(f"📊 Total generadas: {self.total_generated}")
        self.logger.info(f"✅ Enviadas a backtest: {self.total_submitted}")
        self.logger.info(f"❌ Rechazadas: {self.total_rejected}")
    
    async def run_cycle(self):
        """Ciclo principal de generación"""
        # Generar batch de estrategias
        await self._generate_batch()
    
    # ═══════════════════════════════════════════════════════════════
    # GENERACIÓN DE ESTRATEGIAS
    # ═══════════════════════════════════════════════════════════════
    
    async def _generate_batch(self):
        """Generar un batch de estrategias"""
        if len(self.generated_strategies) >= self.gen_config.max_active_strategies:
            self.logger.info("Límite de estrategias alcanzado")
            return
        
        strategies = []
        
        # Generación por templates
        if self.gen_config.enable_templates:
            template_strategies = await self._generate_from_templates()
            strategies.extend(template_strategies)
        
        # Generación aleatoria
        if self.gen_config.enable_random and len(strategies) < self.gen_config.strategies_per_batch:
            random_strategies = await self._generate_random()
            strategies.extend(random_strategies)
        
        # Evolución
        if self.gen_config.enable_evolution and self.generated_strategies:
            evolved = await self._evolve_strategies()
            strategies.extend(evolved)
        
        # Guardar estrategias
        for strategy in strategies:
            self.generated_strategies.append(strategy)
            self.total_generated += 1
        
        # Reportar al CEO
        await self._report_generation(strategies)
        
        # Enviar a backtest
        if strategies:
            await self._send_to_backtest(strategies)
    
    async def _generate_from_templates(self) -> List[GeneratedStrategy]:
        """Generar estrategias basadas en templates"""
        strategies = []
        
        # Seleccionar template aleatorio
        template = random.choice(STRATEGY_TEMPLATES)
        
        # Número de variantes a generar
        num_variants = random.randint(1, 3)
        
        for _ in range(num_variants):
            if len(self.generated_strategies) >= self.gen_config.max_active_strategies:
                break
            
            # Mutar parámetros
            parameters = self._mutate_parameters(template.base_parameters.copy())
            
            # Seleccionar combinación de indicadores
            indicators = random.choice(template.indicator_combos)
            
            # Crear estrategia
            strategy = GeneratedStrategy(
                strategy_id=f"strat_{uuid.uuid4().hex[:12]}",
                strategy_name=f"{template.name_prefix}_{random.randint(100,999)}",
                strategy_type=template.strategy_type.value,
                description=f"{template.description} - Variante generada",
                parameters=parameters,
                rules={
                    "entry": random.choice(template.entry_rules),
                    "exit": random.choice(template.exit_rules),
                    "indicators": [i.value for i in indicators],
                    "risk": template.risk_rules
                },
                metadata={
                    "template_used": template.strategy_type.value,
                    "mutation_count": random.randint(1, 5)
                },
                created_at=datetime.now(),
                generation_method="template"
            )
            
            strategies.append(strategy)
            self.logger.info(f"🧬 Estrategia generada: {strategy.strategy_name} ({strategy.strategy_type})")
        
        return strategies
    
    async def _generate_random(self) -> List[GeneratedStrategy]:
        """Generar estrategias aleatorias completamente nuevas"""
        strategies = []
        
        strategy_types = list(StrategyType)
        
        # Número de estrategias aleatorias
        num_random = random.randint(1, 2)
        
        for _ in range(num_random):
            if len(self.generated_strategies) >= self.gen_config.max_active_strategies:
                break
            
            strategy_type = random.choice(strategy_types)
            
            # Generar parámetros aleatorios
            parameters = self._generate_random_parameters(strategy_type)
            
            strategy = GeneratedStrategy(
                strategy_id=f"strat_{uuid.uuid4().hex[:12]}",
                strategy_name=f"Random_{strategy_type.value}_{random.randint(1000,9999)}",
                strategy_type=strategy_type.value,
                description=f"Estrategia {strategy_type.value} generada aleatoriamente",
                parameters=parameters,
                rules=self._generate_random_rules(strategy_type),
                metadata={
                    "is_random": True,
                    "complexity_score": random.uniform(0.3, 0.9)
                },
                created_at=datetime.now(),
                generation_method="random"
            )
            
            strategies.append(strategy)
        
        return strategies
    
    async def _evolve_strategies(self) -> List[GeneratedStrategy]:
        """Evolucionar estrategias existentes"""
        if not self.generated_strategies:
            return []
        
        evolved = []
        
        # Seleccionar mejores estrategias para evolucionar
        candidates = random.sample(
            self.generated_strategies,
            min(3, len(self.generated_strategies))
        )
        
        for parent in candidates:
            if len(self.generated_strategies) >= self.gen_config.max_active_strategies:
                break
            
            if random.random() < self.gen_config.mutation_rate:
                child = self._mutate_strategy(parent)
                evolved.append(child)
        
        return evolved
    
    def _mutate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mutar parámetros existentes"""
        mutation_count = 0
        
        for key in list(parameters.keys()):
            if random.random() < self.gen_config.mutation_rate:
                old_value = parameters[key]
                
                if isinstance(old_value, (int, float)):
                    # Mutación numérica
                    if isinstance(old_value, int):
                        change = random.randint(-3, 3)
                        new_value = max(1, old_value + change)
                    else:
                        change = random.uniform(-0.1, 0.1)
                        new_value = max(0.01, old_value * (1 + change))
                    
                    parameters[key] = new_value
                    mutation_count += 1
        
        return parameters
    
    def _generate_random_parameters(self, strategy_type: StrategyType) -> Dict[str, Any]:
        """Generar parámetros aleatorios para un tipo de estrategia"""
        base_params = {
            "period_1": random.randint(5, 20),
            "period_2": random.randint(10, 50),
            "multiplier": round(random.uniform(1.5, 3.0), 1),
            "threshold": round(random.uniform(0.01, 0.1), 3)
        }
        
        # Añadir parámetros específicos
        if strategy_type == StrategyType.MOMENTUM:
            base_params.update({
                "rsi_period": random.randint(7, 21),
                "rsi_overbought": random.randint(60, 80),
                "rsi_oversold": random.randint(20, 40),
                "sma_fast": random.randint(5, 15),
                "sma_slow": random.randint(15, 40)
            })
        elif strategy_type == StrategyType.BREAKOUT:
            base_params.update({
                "lookback_period": random.randint(10, 30),
                "volume_multiplier": round(random.uniform(1.2, 2.5), 1),
                "consolidation_threshold": round(random.uniform(0.01, 0.05), 3)
            })
        elif strategy_type == StrategyType.TREND_FOLLOWING:
            base_params.update({
                "ema_fast": random.randint(5, 15),
                "ema_slow": random.randint(15, 50),
                "atr_period": random.randint(7, 21)
            })
        
        return base_params
    
    def _generate_random_rules(self, strategy_type: StrategyType) -> Dict[str, Any]:
        """Generar reglas aleatorias"""
        entry_patterns = [
            "Indicador principal sobre umbral",
            "Cruce de indicadores",
            "Patrón de precio específico",
            "Confirmación de volumen",
            "Breakout de rango"
        ]
        
        exit_patterns = [
            "Cruce inverso de indicadores",
            "Objetivo de precio alcanzado",
            "Stop loss activado",
            "Cambio de condiciones",
            "Time exit"
        ]
        
        return {
            "entry": random.choice(entry_patterns),
            "exit": random.choice(exit_patterns),
            "indicators_used": [random.choice(list(IndicatorType)).value],
            "risk": {
                "stop_loss_type": random.choice(["percentage", "atr", "swing"]),
                "stop_loss_multiplier": round(random.uniform(0.01, 0.05), 3),
                "take_profit_type": random.choice(["reward_risk", "fixed"]),
                "reward_risk_ratio": round(random.uniform(1.5, 3.0), 1),
                "max_position_size": round(random.uniform(0.02, 0.08), 3)
            }
        }
    
    def _mutate_strategy(self, parent: GeneratedStrategy) -> GeneratedStrategy:
        """Mutar una estrategia existente"""
        # Crear copia con mutaciones
        new_params = self._mutate_parameters(parent.parameters.copy())
        
        # Mutar reglas
        new_rules = parent.rules.copy()
        if random.random() < 0.3:
            new_rules["entry"] = f"{new_rules['entry']} (modificado)"
        
        child = GeneratedStrategy(
            strategy_id=f"strat_{uuid.uuid4().hex[:12]}",
            strategy_name=f"{parent.strategy_name}_evolved",
            strategy_type=parent.strategy_type,
            description=f"Evolución de {parent.strategy_name}",
            parameters=new_params,
            rules=new_rules,
            metadata={
                "parent_id": parent.strategy_id,
                "generation": parent.metadata.get("generation", 1) + 1
            },
            created_at=datetime.now(),
            generation_method="evolved"
        )
        
        return child
    
    # ═══════════════════════════════════════════════════════════════
    # PERSISTENCIA Y BASE DE DATOS
    # ═══════════════════════════════════════════════════════════════
    
    async def _load_existing_strategies(self):
        """Cargar estrategias existentes de la base de datos"""
        try:
            strategies = await self.db.get_strategies(status="DRAFT")
            for s in strategies:
                self.generated_strategies.append(GeneratedStrategy(
                    strategy_id=s.strategy_id,
                    strategy_name=s.strategy_name,
                    strategy_type=s.strategy_type,
                    description=s.description or "",
                    parameters=s.parameters or {},
                    rules=s.rules or {},
                    metadata={},
                    created_at=s.created_at,
                    generation_method=s.generation_method or "unknown"
                ))
            self.logger.info(f"📂 Cargadas {len(strategies)} estrategias de la base de datos")
        except Exception as e:
            self.logger.warning(f"No se pudieron cargar estrategias: {e}")
    
    async def _save_strategy(self, strategy: GeneratedStrategy):
        """Guardar estrategia en base de datos"""
        try:
            db_strategy = self.DBStrategy(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.strategy_name,
                strategy_type=strategy.strategy_type,
                description=strategy.description,
                parameters=strategy.parameters,
                rules=strategy.rules,
                timeframes=["1h", "4h", "1d"],
                markets=["COINBASE"],
                status="DRAFT",
                generation_method=strategy.generation_method,
                metadata=strategy.metadata
            )
            await self.db.create(db_strategy)
        except Exception as e:
            self.logger.warning(f"No se pudo guardar estrategia: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # COMUNICACIÓN CON BACKTESTER
    # ═══════════════════════════════════════════════════════════════
    
    async def _send_to_backtest(self, strategies: List[GeneratedStrategy]):
        """Enviar estrategias al backtest orchestrator"""
        self.logger.info(f"📤 Enviando {len(strategies)} estrategias a backtest")
        self.total_submitted += len(strategies)
        
        for strategy in strategies:
            await self._save_strategy(strategy)
        
        await self.send_message(self.create_task_message(
            to_agent="BACKTEST_ORCHESTRATOR",
            task_type="BACKTEST_STRATEGIES",
            priority=TaskPriority.NORMAL,
            payload={
                "strategies": [
                    {
                        "strategy_id": s.strategy_id,
                        "strategy_name": s.strategy_name,
                        "parameters": s.parameters,
                        "rules": s.rules,
                        "strategy_type": s.strategy_type
                    }
                    for s in strategies
                ],
                "symbols": ["BTC/USD", "ETH/USD", "SOL/USD"],
                "timeframes": ["1h", "4h", "1d"],
                "priority": "NORMAL"
            }
        ))
    
    async def _report_generation(self, strategies: List[GeneratedStrategy]):
        """Reportar generación de estrategias al CEO"""
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="STRATEGIES_GENERATED",
            priority=TaskPriority.NORMAL,
            payload={
                "count": len(strategies),
                "strategy_ids": [s.strategy_id for s in strategies],
                "types": list(set(s.strategy_type for s in strategies)),
                "timestamp": datetime.now().isoformat()
            }
        ))
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes entrantes"""
        
        if message.task_type == "GENERATE_STRATEGIES":
            return await self._handle_generate_strategies(message)
        
        elif message.task_type == "GENERATE_FROM_TEMPLATE":
            return await self._handle_generate_from_template(message)
        
        elif message.task_type == "EVOLVE_STRATEGY":
            return await self._handle_evolve_strategy(message)
        
        elif message.task_type == "GET_STRATEGIES":
            return self._handle_get_strategies(message)
        
        elif message.task_type == "GET_STRATEGY_STATUS":
            return self._handle_get_status(message)
        
        return None
    
    async def _handle_generate_strategies(self, message: AgentMessage) -> AgentMessage:
        """Generar estrategias bajo demanda"""
        count = message.payload.get("count", self.gen_config.strategies_per_batch)
        strategy_type = message.payload.get("type")
        
        self.logger.info(f"📋 Generación bajo demanda: {count} estrategias")
        
        strategies = []
        
        if strategy_type:
            # Generar tipo específico
            for _ in range(count):
                strategy = await self._generate_single_strategy(StrategyType(strategy_type))
                strategies.append(strategy)
        else:
            # Generar mix
            await self._generate_batch()
            strategies = self.generated_strategies[-count:]
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "generated": len(strategies),
                "strategy_ids": [s.strategy_id for s in strategies]
            }
        )
    
    async def _generate_single_strategy(self, strategy_type: StrategyType) -> GeneratedStrategy:
        """Generar una sola estrategia de tipo específico"""
        template = next(
            (t for t in STRATEGY_TEMPLATES if t.strategy_type == strategy_type),
            random.choice(STRATEGY_TEMPLATES)
        )
        
        return GeneratedStrategy(
            strategy_id=f"strat_{uuid.uuid4().hex[:12]}",
            strategy_name=f"{template.name_prefix}_{random.randint(100,999)}",
            strategy_type=strategy_type.value,
            description=f"Generación bajo demanda - {template.description}",
            parameters=self._mutate_parameters(template.base_parameters.copy()),
            rules={
                "entry": template.entry_rules[0],
                "exit": template.exit_rules[0],
                "risk": template.risk_rules
            },
            metadata={"generation_type": "on_demand"},
            created_at=datetime.now(),
            generation_method="template"
        )
    
    async def _handle_generate_from_template(self, message: AgentMessage) -> AgentMessage:
        """Generar desde template específico"""
        template_name = message.payload.get("template")
        
        template = next(
            (t for t in STRATEGY_TEMPLATES if t.strategy_type.value == template_name),
            random.choice(STRATEGY_TEMPLATES)
        )
        
        strategies = await self._generate_from_templates()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "template_used": template.strategy_type.value,
                "generated": len(strategies),
                "strategy_ids": [s.strategy_id for s in strategies]
            }
        )
    
    async def _handle_evolve_strategy(self, message: AgentMessage) -> AgentMessage:
        """Evolucionar estrategia existente"""
        parent_id = message.payload.get("parent_id")
        mutation_rate = message.payload.get("mutation_rate", self.gen_config.mutation_rate)
        
        # Buscar estrategia padre
        parent = next(
            (s for s in self.generated_strategies if s.strategy_id == parent_id),
            None
        )
        
        if not parent:
            return self.create_result_message(
                to_agent=message.from_agent,
                original_task=message.task_type,
                result={"error": "Strategy not found"}
            )
        
        # Evolver
        self.gen_config.mutation_rate = mutation_rate
        child = self._mutate_strategy(parent)
        self.generated_strategies.append(child)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "parent_id": parent_id,
                "child_id": child.strategy_id,
                "mutation_rate": mutation_rate
            }
        )
    
    def _handle_get_strategies(self, message: AgentMessage) -> AgentMessage:
        """Obtener estrategias generadas"""
        filters = message.payload or {}
        
        strategies = self.generated_strategies
        
        # Filtrar por tipo
        if "type" in filters:
            strategies = [s for s in strategies if s.strategy_type == filters["type"]]
        
        # Filtrar por estado
        if "status" in filters:
            # Consultar DB para estado
            pass
        
        # Limitar
        limit = filters.get("limit", 20)
        strategies = strategies[-limit:]
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "strategies": [
                    {
                        "strategy_id": s.strategy_id,
                        "strategy_name": s.strategy_name,
                        "strategy_type": s.strategy_type,
                        "created_at": s.created_at.isoformat(),
                        "generation_method": s.generation_method
                    }
                    for s in strategies
                ],
                "total_count": len(self.generated_strategies)
            }
        )
    
    def _handle_get_status(self, message: AgentMessage) -> AgentMessage:
        """Obtener estado del generator"""
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "active_strategies": len(self.generated_strategies),
                "total_generated": self.total_generated,
                "total_submitted": self.total_submitted,
                "total_rejected": self.total_rejected,
                "max_capacity": self.gen_config.max_active_strategies,
                "config": {
                    "generation_interval": self.gen_config.generation_interval,
                    "strategies_per_batch": self.gen_config.strategies_per_batch,
                    "mutation_rate": self.gen_config.mutation_rate
                }
            }
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def get_generator_status(self) -> Dict[str, Any]:
        """Obtener estado del generator"""
        return {
            "active_strategies": len(self.generated_strategies),
            "total_generated": self.total_generated,
            "total_submitted": self.total_submitted,
            "total_rejected": self.total_rejected,
            "config": {
                "generation_interval": self.gen_config.generation_interval,
                "strategies_per_batch": self.gen_config.strategies_per_batch,
                "mutation_rate": self.gen_config.mutation_rate,
                "max_active_strategies": self.gen_config.max_active_strategies
            }
        }
    
    def __repr__(self) -> str:
        return f"<StrategyGenerator(active={len(self.generated_strategies)}, total_gen={self.total_generated})>"
