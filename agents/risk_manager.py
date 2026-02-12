"""
💰 RISK MANAGER AGENT - Chief Risk Officer
============================================
Controla TODO el riesgo del sistema - TIENE PODER DE VETO.

Responsabilidades:
- Límites de exposición por activo
- Límites de exposición global
- Límites de drawdown diario/semanal
- Position sizing adaptativo
- Correlation risk management
- Black swan protection
- Emergency stop triggers

⚠️ TIENE PODER DE VETO ABSOLUTO - puede detener cualquier operación

Author: Bittrading Trading Corp
Version: 1.0.0
"""

import
import uuid
 asyncio
import logging, timedelta
fromfrom datetime import datetime typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from agents.base_agent import (
    Base, AgentMessage,Agent, AgentConfig AgentState, 
    MessageType, TaskPriority
)

# ═══════════════════════════════════════════════════════════════════
# ENUMS Y ESTRUCTURAS
# ═══════════════════════════════════════════════════════════════════

class RiskLevel(Enum):
    """Niveles de riesgo"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"  
    HIGH = "HIGH"
    EXTREME = "EXTREME"

class LimitType(Enum):
    """Tipos de límites"""
    POSITION_SIZE = "position_size"
    EXPOSURE = "exposure"
    DAILY_LOSS = "daily_loss"
    WEEKLY_LOSS = "weekly_loss"
    MONTHLY_LOSS = "monthly_loss"
    DRAWDOWN = "drawdown"
    CORRELATION = "correlation"
    LEVERAGE = "leverage"

@dataclass
class RiskLimit:
    """Límite de riesgo configurado"""
    limit_id: str
    limit_type: LimitType
    asset: str  # "ALL" para global
    value: float
    unit: str = "PERCENT"  # PERCENT, USD, ABSOLUTE
    severity: str = "WARNING"  # WARNING, CRITICAL, HARD_STOP
    is_active: bool = True
    description: str = ""
    
    def check(self, current_value: float) -> Dict[str, Any]:
        """Verificar si el límite fue alcanzado"""
        if not self.is_active:
            return {"breached": False, "message": "Límite inactivo"}
        
        if self.unit == "PERCENT":
            breached = current_value >= self.value
        else:
            breached = current_value >= self.value
        
        return {
            "breached": breached,
            "limit_id": self.limit_id,
            "current_value": current_value,
            "limit_value": self.value,
            "severity": self.severity
        }

@dataclass
class Position:
    """Posición actual"""
    symbol: str
    side: str  # LONG, SHORT
    size: float
    entry_price: float
    current_price: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    unrealized_pnl: float = 0.0
    open_time: datetime = field(default_factory=datetime.now)

@dataclass
class RiskAssessment:
    """Evaluación de riesgo para una operación"""
    approved: bool
    risk_score: float  # 0-1
    level: RiskLevel
    position_size_recommended: float
    stop_loss_suggested: float
    take_profit_suggested: float
    warnings: List[str]
    reasons: List[str]
    risk_manager_override: bool = False

# ═══════════════════════════════════════════════════════════════════
# RISK MANAGER AGENT
# ═══════════════════════════════════════════════════════════════════

class RiskManagerAgent(BaseAgent):
    """
    Risk Manager - Control total del riesgo del sistema.
    
    ⚠️ Este agente tiene PODER DE VETO absoluto.
    Puede detener cualquier operación, cerrar posiciones 
    y paralizar el sistema en caso de riesgo extremo.
    
    Límites configurados:
    - Exposición por activo: 5%
    - Exposición total: 25%
    - Drawdown diario: 5%
    - Drawdown semanal: 10%
    - Correlación entre activos: 0.7
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        risk_config = AgentConfig(
            agent_id="RISK_MANAGER",
            agent_name="Chief Risk Officer",
            agent_type="RISK",
            log_level="INFO",
            cycle_interval=10,  # Checks frecuentes
            custom_config=config or {}
        )
        
        super().__init__(risk_config, message_bus)
        
        # Estado del riesgo
        self.current_risk_level = RiskLevel.LOW
        self.emergency_stop_active = False
        self.market_halt_active = False
        
        # Límites configurados
        self.limits: List[RiskLimit] = []
        self._setup_default_limits()
        
        # Estado actual
        self.total_portfolio_value: float = 100000.0  # valor inicial
        self.current_exposure: Dict[str, float] = {}
        self.current_exposure_total: float = 0.0
        self.daily_pnl: float = 0.0
        self.weekly_pnl: float = 0.0
        self.peak_value: float = 100000.0
        self.current_drawdown: float = 0.0
        
        # Posiciones actuales
        self.positions: Dict[str, Position] = {}
        
        # Métricas
        self.trades_rejected = 0
        self.trades_approved = 0
        self.emergency_stops_triggered = 0
        
        # Database
        from shared.database import get_database, RiskLimits as DBRiskLimits
        self.db = get_database()
        self.DBRiskLimits = DBRiskLimits
        
        self.logger.info("💰 Risk Manager Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CONFIGURACIÓN DE LÍMITES
    # ═══════════════════════════════════════════════════════════════
    
    def _setup_default_limits(self):
        """Configurar límites de riesgo por defecto"""
        self.limits = [
            # Exposición por activo
            RiskLimit(
                limit_id="max_position_size",
                limit_type=LimitType.POSITION_SIZE,
                asset="ALL",
                value=5.0,  # 5% del portfolio por posición
                unit="PERCENT",
                severity="CRITICAL",
                description="Máximo 5% del portfolio en una posición"
            ),
            
            # Exposición total
            RiskLimit(
                limit_id="max_total_exposure",
                limit_type=LimitType.EXPOSURE,
                asset="ALL",
                value=25.0,  # 25% del portfolio total
                unit="PERCENT",
                severity="CRITICAL",
                description="Máximo 25% del portfolio expuesto"
            ),
            
            # Drawdown diario
            RiskLimit(
                limit_id="max_daily_drawdown",
                limit_type=LimitType.DAILY_LOSS,
                asset="ALL",
                value=5.0,  # 5% drawdown máximo diario
                unit="PERCENT",
                severity="HARD_STOP",
                description="Halt total si se pierde 5% en un día"
            ),
            
            # Drawdown semanal
            RiskLimit(
                limit_id="max_weekly_drawdown",
                limit_type=LimitType.WEEKLY_LOSS,
                asset="ALL",
                value=10.0,  # 10% drawdown semanal
                unit="PERCENT",
                severity="HARD_STOP",
                description="Halt total si se pierde 10% en una semana"
            ),
            
            # Max drawdown desde peak
            RiskLimit(
                limit_id="max_drawdown_from_peak",
                limit_type=LimitType.DRAWDOWN,
                asset="ALL",
                value=15.0,  # 15% desde peak
                unit="PERCENT",
                severity="HARD_STOP",
                description="Halt total si drawdown excede 15% desde peak"
            ),
            
            # Correlación
            RiskLimit(
                limit_id="max_correlation",
                limit_type=LimitType.CORRELATION,
                asset="ALL",
                value=0.7,  # 0.7 correlación máxima
                unit="ABSOLUTE",
                severity="WARNING",
                description="Alertar si correlación excede 0.7"
            ),
            
            # Por activo específico
            RiskLimit(
                limit_id="btc_exposure",
                limit_type=LimitType.EXPOSURE,
                asset="BTC/USD",
                value=15.0,  # BTC max 15%
                unit="PERCENT",
                severity="WARNING",
                description="Máximo 15% en BTC"
            ),
            RiskLimit(
                limit_id="eth_exposure",
                limit_type=LimitType.EXPOSURE,
                asset="ETH/USD",
                value=15.0,  # ETH max 15%
                unit="PERCENT",
                severity="WARNING",
                description="Máximo 15% en ETH"
            )
        ]
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Inicializar Risk Manager"""
        self.logger.info("🚀 Iniciando Risk Manager...")
        
        # Cargar límites de la base de datos
        await self._load_limits()
        
        # Suscribirse a todos los mensajes de trading
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                msg_types=[MessageType.TASK, MessageType.ALERT],
                task_types=[
                    "EVALUATE_TRADE",
                    "EVALUATE_STRATEGY",
                    "UPDATE_POSITION",
                    "EMERGENCY_STOP",
                    "GET_RISK_STATUS",
                    "CONFIGURE_LIMITS",
                    "CRITICAL_ALERT",
                    "REGIME_CHANGE"
                ]
            )
        
        self.logger.info("✅ Risk Manager listo con PODER DE VETO")
        self.logger.warning("⚠️ LÍMITES ACTIVOS:")
        for limit in self.limits:
            if limit.is_active:
                self.logger.warning(f"   - {limit.limit_id}: {limit.value}{limit.unit}")
    
    async def on_shutdown(self):
        """Shutdown del Risk Manager"""
        self.logger.info("🛑 Deteniendo Risk Manager...")
        
        # Si hay posiciones abiertas, alertar
        if self.positions:
            self.logger.warning(f"⚠️ Cerrando {len(self.positions)} posiciones por shutdown")
            await self._emergency_close_all()
    
    async def run_cycle(self):
        """Ciclo principal de evaluación de riesgo"""
        # Actualizar métricas de riesgo
        await self._update_risk_metrics()
        
        # Verificar límites
        await self._check_all_limits()
        
        # Evaluar nivel de riesgo
        await self._evaluate_risk_level()
        
        # Acciones automáticas si es necesario
        if self.current_risk_level == RiskLevel.EXTREME:
            await self._trigger_emergency_protocol()
    
    # ═══════════════════════════════════════════════════════════════
    # ACTUALIZACIÓN DE MÉTRICAS
    # ═══════════════════════════════════════════════════════════════
    
    async def _update_risk_metrics(self):
        """Actualizar métricas de riesgo actuales"""
        # Calcular drawdown actual
        if self.total_portfolio_value > self.peak_value:
            self.peak_value = self.total_portfolio_value
        
        self.current_drawdown = (
            (self.peak_value - self.total_portfolio_value) / self.peak_value * 100
        )
        
        # Calcular exposición total
        self.current_exposure_total = sum(self.current_exposure.values())
        
        # Calcular P&L diario
        # (En producción, esto vendría de la base de datos)
    
    async def _check_all_limits(self):
        """Verificar todos los límites de riesgo"""
        violations = []
        
        for limit in self.limits:
            if not limit.is_active:
                continue
            
            if limit.limit_type == LimitType.POSITION_SIZE:
                current = self._get_max_position_size()
            elif limit.limit_type == LimitType.EXPOSURE:
                if limit.asset == "ALL":
                    current = self.current_exposure_total
                else:
                    current = self.current_exposure.get(limit.asset, 0)
            elif limit.limit_type == LimitType.DAILY_LOSS:
                current = -self.daily_pnl if self.daily_pnl < 0 else 0
            elif limit.limit_type == LimitType.WEEKLY_LOSS:
                current = -self.weekly_pnl if self.weekly_pnl < 0 else 0
            elif limit.limit_type == LimitType.DRAWDOWN:
                current = self.current_drawdown
            else:
                continue
            
            check_result = limit.check(current)
            
            if check_result["breached"]:
                violations.append(check_result)
                
                if limit.severity == "HARD_STOP":
                    self.logger.critical(f"🚨 HARD STOP: {limit.description}")
                    await self._trigger_hard_stop(limit, current)
                elif limit.severity == "CRITICAL":
                    self.logger.error(f"⚠️ LÍMITE CRÍTICO: {limit.description}")
                    await self._trigger_critical_alert(limit, current)
                elif limit.severity == "WARNING":
                    self.logger.warning(f"⚠️ ALERTA: {limit.description}")
        
        return violations
    
    async def _evaluate_risk_level(self):
        """Evaluar nivel general de riesgo"""
        # Contar violaciones
        violations = await self._check_all_limits()
        
        critical_violations = [v for v in violations if v["severity"] in ["HARD_STOP", "CRITICAL"]]
        warning_violations = [v for v in violations if v["severity"] == "WARNING"]
        
        # Determinar nivel
        if self.emergency_stop_active:
            self.current_risk_level = RiskLevel.EXTREME
        elif critical_violations:
            self.current_risk_level = RiskLevel.HIGH
        elif warning_violations:
            self.current_risk_level = RiskLevel.MEDIUM
        else:
            self.current_risk_level = RiskLevel.LOW
    
    # ═══════════════════════════════════════════════════════════════
    # EVALUACIÓN DE OPERACIONES
    # ═══════════════════════════════════════════════════════════════
    
    async def evaluate_trade(self, trade_request: Dict[str, Any]) -> RiskAssessment:
        """
        ⭐ EVALUACIÓN PRINCIPAL - Esta es la función que se llama para cada trade.
        
        Returns RiskAssessment con:
        - approved: Si el trade puede proceder
        - risk_score: 0-1
        - position_size_recommended: Tamaño ajustado
        - warnings: Lista de advertencias
        - reasons: Lista de razones para aprobación/rechazo
        """
        symbol = trade_request.get("symbol", "UNKNOWN")
        proposed_size = trade_request.get("size", 0)
        side = trade_request.get("side", "BUY")
        
        warnings = []
        reasons = []
        approved = True
        
        self.logger.info(f"📊 Evaluando trade: {side} {symbol} {proposed_size}")
        
        # 1. Verificar emergency stop
        if self.emergency_stop_active:
            return RiskAssessment(
                approved=False,
                risk_score=1.0,
                level=RiskLevel.EXTREME,
                position_size_recommended=0,
                stop_loss_suggested=0,
                take_profit_suggested=0,
                warnings=["EMERGENCY STOP ACTIVE"],
                reasons=["Trading halted due to emergency stop"],
                risk_manager_override=True
            )
        
        # 2. Verificar límites de posición por activo
        current_exposure = self.current_exposure.get(symbol, 0)
        total_exposure_after = current_exposure + proposed_size
        
        position_limit = self._get_limit_for_type(LimitType.POSITION_SIZE)
        if position_limit:
            if total_exposure_after > position_limit.value:
                approved = False
                warnings.append(f"Límite de posición excedido: {total_exposure_after:.2f}% > {position_limit.value}%")
                reasons.append(f"Tamaño máximo de posición es {position_limit.value}%")
        
        # 3. Verificar exposición total
        total_exposure = self.current_exposure_total
        exposure_limit = self._get_limit_for_type(LimitType.EXPOSURE)
        if exposure_limit:
            if (total_exposure + proposed_size) > exposure_limit.value:
                approved = False
                adjusted_size = max(0, exposure_limit.value - total_exposure)
                proposed_size = adjusted_size
                warnings.append(f"Exposición total excedida. Ajustando a {adjusted_size:.2f}%")
                reasons.append(f"Exposición máxima total es {exposure_limit.value}%")
        
        # 4. Verificar drawdown actual
        dd_limit = self._get_limit_for_type(LimitType.DRAWDOWN)
        if dd_limit and self.current_drawdown > dd_limit.value * 0.8:
            warnings.append(f"Drawdown actual alto: {self.current_drawdown:.2f}%")
            # Reducir tamaño en drawdown
            reduction_factor = 1 - (self.current_drawdown / dd_limit.value)
            proposed_size *= reduction_factor
            reasons.append(f"Reducción de tamaño por drawdown ({reduction_factor:.2f}x)")
        
        # 5. Verificar límite diario
        daily_limit = self._get_limit_for_type(LimitType.DAILY_LOSS)
        if daily_limit and abs(self.daily_pnl) > daily_limit.value * 0.9:
            approved = False
            reasons.append(f"Límite diario alcanzado: {abs(self.daily_pnl):.2f}%")
        
        # 6. Calcular risk score
        risk_score = self._calculate_risk_score(trade_request, proposed_size, warnings)
        
        # 7. Determinar nivel
        if risk_score > 0.8:
            level = RiskLevel.EXTREME
        elif risk_score > 0.6:
            level = RiskLevel.HIGH
        elif risk_score > 0.4:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        # 8. Sugerir stop loss y take profit
        stop_loss = self._suggest_stop_loss(trade_request)
        take_profit = self._suggest_take_profit(trade_request, stop_loss)
        
        # 9. Decisión final
        if approved and level not in [RiskLevel.EXTREME]:
            self.trades_approved += 1
            self.logger.info(f"✅ Trade APROBADO: {symbol} | Risk: {risk_score:.2f} | Level: {level.value}")
        else:
            self.trades_rejected += 1
            self.logger.warning(f"❌ Trade RECHAZADO: {symbol} | Razones: {reasons}")
        
        # 10. Loggear decisión
        await self._log_trade_decision(trade_request, approved, risk_score, level)
        
        return RiskAssessment(
            approved=approved,
            risk_score=risk_score,
            level=level,
            position_size_recommended=proposed_size,
            stop_loss_suggested=stop_loss,
            take_profit_suggested=take_profit,
            warnings=warnings,
            reasons=reasons
        )
    
    def _calculate_risk_score(self, trade: Dict[str, Any], size: float, warnings: List[str]) -> float:
        """Calcular score de riesgo (0-1)"""
        base_risk = 0.3
        
        # Factor por tamaño
        size_factor = min(1.0, size / 5.0) * 0.2
        
        # Factor por nivel de mercado
        regime_risk = self._get_regime_risk_factor()
        
        # Factor por advertencias
        warning_factor = len(warnings) * 0.1
        
        # Factor por drawdown
        dd_factor = min(0.3, self.current_drawdown / 50)
        
        risk_score = base_risk + size_factor + regime_risk + warning_factor + dd_factor
        
        return min(1.0, risk_score)
    
    def _get_regime_risk_factor(self) -> float:
        """Obtener factor de riesgo según régimen de mercado"""
        # Alta volatilidad = más riesgo
        if self.current_risk_level == RiskLevel.HIGH:
            return 0.15
        elif self.current_risk_level == RiskLevel.EXTREME:
            return 0.3
        return 0.0
    
    def _suggest_stop_loss(self, trade: Dict[str, Any]) -> float:
        """Sugerir stop loss para el trade"""
        # Stop loss por volatilidad (ATR)
        atr = trade.get("atr", 0.02)  # 2% por defecto
        
        # Ajuste por drawdown actual
        dd_adjustment = 1 + (self.current_drawdown / 100)
        
        return round(atr * 1.5 * dd_adjustment, 4)
    
    def _suggest_take_profit(self, trade: Dict[str, Any], stop_loss: float) -> float:
        """Sugerir take profit basado en risk/reward"""
        reward_risk_ratio = trade.get("reward_risk_ratio", 2.0)
        return round(stop_loss * reward_risk_ratio, 4)
    
    # ═══════════════════════════════════════════════════════════════
    # PROTOCOLOS DE EMERGENCIA
    # ═══════════════════════════════════════════════════════════════
    
    async def _trigger_hard_stop(self, limit: RiskLimit, current_value: float):
        """Trigger hard stop - detener todo"""
        self.emergency_stop_active = True
        self.emergency_stops_triggered += 1
        
        self.logger.critical(f"🚨 HARD STOP ACTIVADO: {limit.description}")
        
        # Cerrar todas las posiciones
        await self._emergency_close_all()
        
        # Notificar al CEO
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="HARD_STOP_TRIGGERED",
            priority=TaskPriority.CRITICAL,
            payload={
                "limit_id": limit.limit_id,
                "description": limit.description,
                "current_value": current_value,
                "limit_value": limit.value,
                "positions_closed": len(self.positions)
            }
        ))
    
    async def _trigger_critical_alert(self, limit: RiskLimit, current_value: float):
        """Trigger alerta crítica"""
        self.logger.error(f"⚠️ ALERTA CRÍTICA: {limit.description}")
        
        # Reducir exposición automáticamente
        await self._reduce_exposure()
        
        # Notificar al CEO
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="CRITICAL_RISK_ALERT",
            priority=TaskPriority.CRITICAL,
            payload={
                "limit_id": limit.limit_id,
                "current_value": current_value,
                "limit_value": limit.value
            }
        ))
    
    async def _trigger_emergency_protocol(self):
        """Protocolo de emergencia completo"""
        self.logger.critical("🚨 PROTOCOLO DE EMERGENCIA ACTIVADO")
        
        # 1. Notificar a todos los agentes
        await self.send_message(self.create_task_message(
            to_agent="BROADCAST",
            task_type="EMERGENCY_STOP",
            priority=TaskPriority.CRITICAL,
            payload={
                "reason": "Riesgo extremo detectado",
                "risk_level": self.current_risk_level.value,
                "current_drawdown": self.current_drawdown
            }
        ))
        
        # 2. Cerrar todas las posiciones
        await self._emergency_close_all()
        
        # 3. Desactivar nuevos trades
        self.market_halt_active = True
    
    async def _emergency_close_all(self):
        """Cerrar todas las posiciones"""
        self.logger.warning(f"⚠️ Cerrando {len(self.positions)} posiciones...")
        
        for symbol in list(self.positions.keys()):
            await self.send_message(self.create_task_message(
                to_agent="TRADER",
                task_type="CLOSE_POSITION",
                priority=TaskPriority.CRITICAL,
                payload={
                    "symbol": symbol,
                    "reason": "EMERGENCY_CLOSE",
                    "force": True
                }
            ))
        
        self.positions.clear()
    
    async def _reduce_exposure(self):
        """Reducir exposición total"""
        target_exposure = self.current_exposure_total * 0.5
        
        self.logger.info(f"📉 Reduciendo exposición de {self.current_exposure_total:.2f}% a {target_exposure:.2f}%")
        
        # Cerrar parcialmente las posiciones más grandes
        sorted_positions = sorted(
            self.current_exposure.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for symbol, exposure in sorted_positions:
            if self.current_exposure_total <= target_exposure:
                break
            
            reduction = min(exposure * 0.3, self.current_exposure_total - target_exposure)
            
            await self.send_message(self.create_task_message(
                to_agent="TRADER",
                task_type="CLOSE_POSITION_PARTIAL",
                priority=TaskPriority.HIGH,
                payload={
                    "symbol": symbol,
                    "percentage": reduction,
                    "reason": "RISK_REDUCTION"
                }
            ))
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes entrantes"""
        
        if message.task_type == "EVALUATE_TRADE":
            return await self._handle_evaluate_trade(message)
        
        elif message.task_type == "EVALUATE_STRATEGY":
            return await self._handle_evaluate_strategy(message)
        
        elif message.task_type == "UPDATE_POSITION":
            return await self._handle_update_position(message)
        
        elif message.task_type == "EMERGENCY_STOP":
            return await self._handle_emergency_stop(message)
        
        elif message.task_type == "GET_RISK_STATUS":
            return self._handle_get_status(message)
        
        elif message.task_type == "CONFIGURE_LIMITS":
            return await self._handle_configure_limits(message)
        
        elif message.task_type == "CRITICAL_ALERT":
            return await self._handle_critical_alert(message)
        
        elif message.task_type == "REGIME_CHANGE":
            return await self._handle_regime_change(message)
        
        return None
    
    async def _handle_evaluate_trade(self, message: AgentMessage) -> AgentMessage:
        """Evaluar un trade"""
        assessment = await self.evaluate_trade(message.payload)
        
        # Crear respuesta
        response = self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "approved": assessment.approved,
                "risk_score": assessment.risk_score,
                "risk_level": assessment.level.value,
                "position_size_recommended": assessment.position_size_recommended,
                "stop_loss": assessment.stop_loss_suggested,
                "take_profit": assessment.take_profit_suggested,
                "warnings": assessment.warnings,
                "reasons": assessment.reasons,
                "emergency_stop_active": self.emergency_stop_active,
                "veto_exercised": not assessment.approved and assessment.risk_manager_override
            }
        )
        
        # Si fue vetado, notificar al CEO
        if not assessment.approved and assessment.risk_manager_override:
            await self.send_message(self.create_alert(
                alert_type="TRADE_VETOED",
                message=f"Trade vetado para {message.payload.get('symbol')}",
                severity="CRITICAL",
                payload={
                    "trade": message.payload,
                    "reasons": assessment.reasons,
                    "risk_score": assessment.risk_score
                }
            ))
        
        return response
    
    async def _handle_evaluate_strategy(self, message: AgentMessage) -> AgentMessage:
        """Evaluar una estrategia para activación"""
        strategy_id = message.payload.get("strategy_id")
        risk_score = message.payload.get("risk_score", 0.5)
        
        # Verificar si podemos activar más estrategias
        if len(self.positions) >= 10:
            return self.create_result_message(
                to_agent=message.from_agent,
                original_task=message.task_type,
                result={
                    "approved": False,
                    "reason": "Máximo número de posiciones alcanzado",
                    "current_positions": len(self.positions)
                }
            )
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "approved": True,
                "strategy_id": strategy_id,
                "risk_score": risk_score,
                "can_proceed": True
            }
        )
    
    async def _handle_update_position(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Actualizar estado de posición"""
        symbol = message.payload.get("symbol")
        pnl = message.payload.get("pnl", 0)
        
        if symbol in self.positions:
            self.positions[symbol].pnl = pnl
            self.positions[symbol].pnl_percent = pnl / self.positions[symbol].size * 100
        
        # Actualizar P&L diario
        self.daily_pnl += pnl
        
        return None
    
    async def _handle_emergency_stop(self, message: AgentMessage) -> AgentMessage:
        """Manejar solicitud de emergency stop"""
        reason = message.payload.get("reason", "Manual request")
        requested_by = message.payload.get("requested_by", "Unknown")
        
        self.logger.critical(f"🚨 EMERGENCY STOP solicitado por {requested_by}: {reason}")
        
        await self._trigger_emergency_protocol()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "emergency_stop_active": self.emergency_stop_active,
                "positions_closed": len(self.positions),
                "reason": reason
            }
        )
    
    def _handle_get_status(self, message: AgentMessage) -> AgentMessage:
        """Obtener estado de riesgo"""
        status = self.get_risk_status()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result=status
        )
    
    async def _handle_configure_limits(self, message: AgentMessage) -> AgentMessage:
        """Configurar nuevos límites"""
        new_limits = message.payload.get("limits", [])
        
        for limit_data in new_limits:
            limit = RiskLimit(
                limit_id=limit_data.get("limit_id", f"custom_{uuid.uuid4().hex[:8]}"),
                limit_type=LimitType(limit_data.get("limit_type", "position_size")),
                asset=limit_data.get("asset", "ALL"),
                value=limit_data.get("value", 5.0),
                unit=limit_data.get("unit", "PERCENT"),
                severity=limit_data.get("severity", "WARNING"),
                description=limit_data.get("description", "")
            )
            self.limits.append(limit)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "limits_configured": len(new_limits),
                "total_limits": len(self.limits)
            }
        )
    
    async def _handle_critical_alert(self, message: AgentMessage) -> AgentMessage:
        """Manejar alerta crítica de otro agente"""
        source = message.payload.get("source", "Unknown")
        alert = message.payload.get("alert", {})
        
        self.logger.warning(f"⚠️ Alerta crítica de {source}: {alert}")
        
        # Evaluar si necesitamos tomar acción
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "alert_received": True,
                "action_taken": "Evaluating",
                "current_risk_level": self.current_risk_level.value
            }
        )
    
    async def _handle_regime_change(self, message: AgentMessage) -> AgentMessage:
        """Manejar cambio de régimen de mercado"""
        regime = message.payload.get("regime", "NEUTRAL")
        
        # Ajustar límites según régimen
        if regime in ["HIGH_VOLATILITY", "CRASH"]:
            self.logger.warning(f"⚠️ Régimen de riesgo elevado: {regime}")
            # Reducir tamaño de posiciones
            # (Se aplicaría en futuras evaluaciones)
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def _get_limit_for_type(self, limit_type: LimitType) -> Optional[RiskLimit]:
        """Obtener límite por tipo"""
        for limit in self.limits:
            if limit.limit_type == limit_type and limit.is_active and limit.asset == "ALL":
                return limit
        return None
    
    def _get_max_position_size(self) -> float:
        """Obtener tamaño máximo de posición actual"""
        # Reducir si hay drawdown
        base_max = 5.0
        dd_reduction = min(0.5, self.current_drawdown / 100)
        return max(1.0, base_max - dd_reduction)
    
    async def _log_trade_decision(
        self, 
        trade: Dict[str, Any], 
        approved: bool, 
        risk_score: float,
        level: RiskLevel
    ):
        """Loggear decisión de trade"""
        from shared.database import get_database, AuditLog
        db = get_database()
        
        try:
            audit = AuditLog(
                log_id=str(uuid.uuid4()),
                agent_id=self.agent_id,
                action="TRADE_EVALUATION",
                entity_type="TRADE",
                entity_id=trade.get("symbol"),
                details={
                    "approved": approved,
                    "risk_score": risk_score,
                    "risk_level": level.value,
                    "symbol": trade.get("symbol"),
                    "size": trade.get("size"),
                    "side": trade.get("side")
                }
            )
            await db.create(audit)
        except:
            pass
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Obtener estado completo del riesgo"""
        return {
            "risk_level": self.current_risk_level.value,
            "emergency_stop_active": self.emergency_stop_active,
            "market_halt_active": self.market_halt_active,
            "current_drawdown": round(self.current_drawdown, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "weekly_pnl": round(self.weekly_pnl, 2),
            "total_exposure": round(self.current_exposure_total, 2),
            "positions_count": len(self.positions),
            "trades_approved": self.trades_approved,
            "trades_rejected": self.trades_rejected,
            "approval_rate": round(
                self.trades_approved / max(1, self.trades_approved + self.trades_rejected) * 100, 2
            ),
            "active_limits": len([l for l in self.limits if l.is_active]),
            "limits_summary": {
                l.limit_id: {"value": l.value, "unit": l.unit, "active": l.is_active}
                for l in self.limits
            }
        }
    
    def __repr__(self) -> str:
        status = self.get_risk_status()
        return f"<RiskManager(level={status['risk_level']}, drawdown={status['current_drawdown']}%, approved={status['approval_rate']}%)>"
