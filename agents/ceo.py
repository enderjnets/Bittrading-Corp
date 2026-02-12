"""
🧠 CEO AGENT - Chief Executive Orchestrator
==============================================
El cerebro supremo de OpenClaw Trading Corp.

Responsabilidades:
- Coordinar todos los agentes subordinados
- Tomar decisiones estratégicas de alto nivel
- Supervisar la salud del sistema
- Gestionar emergencias y decisiones críticas
- Reportar estado general

Author: OpenClaw Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from agents.base_agent import (
    BaseAgent, AgentConfig, AgentMessage, AgentState, 
    MessageType, TaskPriority
)
from shared.database import get_database, AgentState as DBAgentState

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL CEO
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CEOConfig:
    """Configuración específica del CEO"""
    check_interval: int = 30  # Segundos entre checks
    agents_to_monitor: List[str] = field(default_factory=lambda: [
        "MARKET_SCANNER",
        "ANALYST", 
        "STRATEGY_GENERATOR",
        "BACKTEST_ORCHESTRATOR",
        "OPTIMIZER",
        "STRATEGY_SELECTOR",
        "RISK_MANAGER",
        "TRADER",
        "TASK_MANAGER",
        "WORKER_MANAGER"
    ])
    emergency_shutdown_threshold: int = 5  # Errores antes de shutdown
    daily_report_time: str = "18:00"  # Hora del reporte diario
    max_inactive_minutes: int = 10  # Minutos sin actividad antes de alertar

# ═══════════════════════════════════════════════════════════════════
# CEO AGENT
# ═══════════════════════════════════════════════════════════════════

class CEOAgent(BaseAgent):
    """
    Chief Executive Orchestrator - El cerebro de OpenClaw Trading Corp.
    
    Supervisiona todos los agentes, toma decisiones estratégicas y mantiene
    el sistema funcionando como una empresa de trading coordinada.
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        # Configuración del CEO
        ceo_config = AgentConfig(
            agent_id="CEO",
            agent_name="Chief Executive Orchestrator",
            agent_type="COORDINATOR",
            log_level="INFO",
            cycle_interval=30,
            max_retries=0,
            custom_config=config or {}
        )
        
        super().__init__(ceo_config, message_bus)
        
        self.ceo_config = CEOConfig()
        
        # Estado del sistema
        self.system_healthy = True
        self.market_open = False
        self.trading_active = False
        self.daily_pnl = 0.0
        self.daily_target = 0.0
        
        # Métricas
        self.active_strategies = 0
        self.open_positions = 0
        self.last_decision: Optional[Dict[str, Any]] = None
        
        # Database
        self.db = get_database()
        
        # Decisiones recientes
        self.recent_decisions: List[Dict[str, Any]] = []
        
        self.logger.info("🧠 CEO Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Inicialización del CEO"""
        self.logger.info("🚀 CEO comenzando operaciones...")
        
        # Registrar en base de datos
        try:
            agent_state = DBAgentState(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                agent_type="COORDINATOR",
                state="ONLINE"
            )
            await self.db.create(agent_state)
        except Exception as e:
            self.logger.warning(f"No se pudo registrar en DB: {e}")
        
        # Suscribirse a heartbeats de todos los agentes
        self.message_bus.subscribe(
            self.agent_id,
            msg_types=[MessageType.HEARTBEAT, MessageType.ALERT, MessageType.ERROR],
            task_types=["STATUS_REPORT"]
        )
        
        # Inicializar dashboard de status
        self.system_status = {
            "start_time": datetime.now().isoformat(),
            "agents_online": 0,
            "agents_total": len(self.ceo_config.agents_to_monitor),
            "active_tasks": 0,
            "system_health": "HEALTHY"
        }
        
        self.logger.info("✅ CEO listo para operar")
    
    async def on_shutdown(self):
        """Apagado del CEO"""
        self.logger.info("🛑 CEO iniciando shutdown...")
        
        # Notificar a todos los agentes
        shutdown_msg = AgentMessage(
            from_agent=self.agent_id,
            to_agent="BROADCAST",
            msg_type=MessageType.SHUTDOWN,
            task_type="SYSTEM_SHUTDOWN",
            priority=TaskPriority.CRITICAL,
            payload={"reason": "CEO shutdown"}
        )
        await self.message_bus.publish(shutdown_msg)
        
        self.logger.info("✅ CEO shutdown completo")
    
    async def run_cycle(self):
        """Ciclo principal del CEO"""
        await self._check_all_agents()
        await self._evaluate_system_health()
        await self._make_strategic_decisions()
        await self._generate_daily_summary()
    
    # ═══════════════════════════════════════════════════════════════
    # MONITOREO DE AGENTES
    # ═══════════════════════════════════════════════════════════════
    
    async def _check_all_agents(self):
        """Verificar estado de todos los agentes"""
        agents_status = self.message_bus.get_agents_status()
        self.system_status["agents_online"] = len(agents_status)
        self.system_status["agents_detail"] = agents_status
        
        # Verificar agentes críticos
        offline_agents = []
        for agent_id in self.ceo_config.agents_to_monitor:
            if agent_id not in agents_status:
                offline_agents.append(agent_id)
            else:
                status = agents_status[agent_id]
                if status.get("state") == "ERROR":
                    offline_agents.append(f"{agent_id} (ERROR)")
        
        if offline_agents:
            self.logger.warning(f"⚠️ Agentes offline: {offline_agents}")
            # No es necesariamente crítico, algunos agentes pueden no estar activos aún
    
    async def _evaluate_system_health(self):
        """Evaluar salud general del sistema"""
        agents = self.message_bus.get_agents_status()
        
        total_errors = sum(
            a.get("errors_count", 0) for a in agents.values()
        )
        
        agents_in_error = [
            a for a in agents.values() 
            if a.get("state") == "ERROR"
        ]
        
        if len(agents_in_error) >= 3:
            self.system_healthy = False
            self.system_status["system_health"] = "CRITICAL"
            self.logger.error("🚨 Sistema en estado CRÍTICO")
        elif total_errors > 10:
            self.system_healthy = False
            self.system_status["system_health"] = "DEGRADED"
        else:
            self.system_healthy = True
            self.system_status["system_health"] = "HEALTHY"
        
        # Actualizar en DB
        try:
            await self.db.update_agent_state(
                self.agent_id,
                state=self.system_status["system_health"],
                last_heartbeat=datetime.now()
            )
        except Exception as e:
            self.logger.warning(f"No se pudo actualizar DB: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # DECISIONES ESTRATÉGICAS
    # ═══════════════════════════════════════════════════════════════
    
    async def _make_strategic_decisions(self):
        """Tomar decisiones estratégicas para el sistema"""
        now = datetime.now()
        
        # Decisión 1: ¿Abrir mercado?
        if not self.trading_active:
            decision = await self._evaluate_market_open()
            if decision.get("action") == "START_TRADING":
                await self._initiate_trading_day()
        
        # Decisión 2: ¿Detectar cambio de régimen?
        regime = await self._detect_regime_change()
        if regime.get("change_detected"):
            await self._announce_regime_change(regime)
        
        # Decisión 3: ¿Algo fuera de lo común?
        anomalies = await self._detect_anomalies()
        if anomalies:
            await self._handle_anomalies(anomalies)
    
    async def _evaluate_market_open(self) -> Dict[str, Any]:
        """Evaluar si el mercado está abierto para trading"""
        # Verificar horario (UTC)
        utc_hour = datetime.utcnow().hour
        
        # Crypto markets: 24/7
        market_hours = {
            "COINBASE": True,  # Siempre abierto
            "BINANCE": True,
        }
        
        is_open = market_hours.get("COINBASE", False)
        
        return {
            "action": "START_TRADING" if is_open and not self.trading_active else "WAIT",
            "market_open": is_open,
            "utc_hour": utc_hour
        }
    
    async def _initiate_trading_day(self):
        """Iniciar el día de trading"""
        self.trading_active = True
        self.logger.info("🌅 Iniciando día de trading")
        
        # Notificar a Market Scanner
        await self.send_message(self.create_task_message(
            to_agent="MARKET_SCANNER",
            task_type="START_MARKET_WATCH",
            priority=TaskPriority.HIGH,
            payload={"trading_session": "DAILY"}
        ))
        
        # Notificar a Trader
        await self.send_message(self.create_task_message(
            to_agent="TRADER",
            task_type="ACTIVATE_TRADING",
            priority=TaskPriority.HIGH,
            payload={"session": "DAILY"}
        ))
        
        # Registrar decisión
        self._record_decision({
            "type": "TRADING_SESSION_START",
            "timestamp": datetime.now().isoformat(),
            "details": "Iniciando día de trading"
        })
    
    async def _detect_regime_change(self) -> Dict[str, Any]:
        """Detectar cambios en el régimen de mercado"""
        # Esta funcionalidad se expandiría con análisis más profundo
        return {"change_detected": False}
    
    async def _announce_regime_change(self, regime: Dict[str, Any]):
        """Anunciar cambio de régimen a todos los agentes"""
        self.logger.info(f"📢 Cambio de régimen: {regime}")
        
        # Notificar a Strategy Selector
        await self.send_message(self.create_task_message(
            to_agent="STRATEGY_SELECTOR",
            task_type="REGIME_CHANGE",
            priority=TaskPriority.HIGH,
            payload=regime
        ))
        
        # Notificar a Risk Manager
        await self.send_message(self.create_task_message(
            to_agent="RISK_MANAGER",
            task_type="REGIME_CHANGE",
            priority=TaskPriority.HIGH,
            payload=regime
        ))
    
    async def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detectar anomalías en el sistema"""
        anomalies = []
        
        agents = self.message_bus.get_agents_status()
        
        # Error spike
        for agent_id, status in agents.items():
            if status.get("errors_count", 0) > 5:
                anomalies.append({
                    "type": "ERROR_SPIKE",
                    "agent": agent_id,
                    "count": status.get("errors_count")
                })
        
        # Queue overflow
        queue_status = self.message_bus.get_queue_status()
        for agent_id, size in queue_status.get("queues", {}).items():
            if size > 100:
                anomalies.append({
                    "type": "QUEUE_OVERFLOW",
                    "agent": agent_id,
                    "size": size
                })
        
        return anomalies
    
    async def _handle_anomalies(self, anomalies: List[Dict[str, Any]]):
        """Manejar anomalías detectadas"""
        for anomaly in anomalies:
            self.logger.warning(f"⚠️ Anomalía detectada: {anomaly}")
            
            # Según el tipo, tomar acción
            if anomaly["type"] == "ERROR_SPIKE":
                # Reiniciar agente si hay muchos errores
                if anomaly["count"] > 10:
                    await self.send_message(self.create_task_message(
                        to_agent=anomaly["agent"],
                        task_type="RESTART",
                        priority=TaskPriority.HIGH,
                        payload={"reason": "Error spike"}
                    ))
            
            elif anomaly["type"] == "QUEUE_OVERFLOW":
                # Limpiar cola
                await self.send_message(self.create_task_message(
                    to_agent="TASK_MANAGER",
                    task_type="CLEAR_QUEUE",
                    priority=TaskPriority.HIGH,
                    payload={"agent": anomaly["agent"]}
                ))
    
    # ═══════════════════════════════════════════════════════════════
    # REPORTING
    # ═══════════════════════════════════════════════════════════════
    
    async def _generate_daily_summary(self):
        """Generar resumen diario del sistema"""
        now = datetime.now()
        
        # Generar a las 18:00 o cuando se solicite
        if now.hour == 18 and now.minute == 0:
            summary = await self._create_daily_report()
            await self._send_daily_report(summary)
    
    async def _create_daily_report(self) -> Dict[str, Any]:
        """Crear reporte diario"""
        agents = self.message_bus.get_agents_status()
        
        report = {
            "date": datetime.now().date().isoformat(),
            "system_health": self.system_status["system_health"],
            "agents_status": {
                a["agent_id"]: {
                    "state": a["state"],
                    "uptime": a["uptime_seconds"],
                    "messages_processed": a["messages_processed"]
                }
                for a in agents.values()
            },
            "trading_active": self.trading_active,
            "queue_stats": self.message_bus.get_queue_status(),
            "message_bus_stats": self.message_bus.get_stats()
        }
        
        return report
    
    async def _send_daily_report(self, report: Dict[str, Any]):
        """Enviar reporte diario"""
        # Por ahora, solo loggear
        self.logger.info(f"\n{'='*60}")
        self.logger.info("📊 REPORTE DIARIO - OpenClaw Trading Corp")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Salud del sistema: {report['system_health']}")
        self.logger.info(f"Trading activo: {report['trading_active']}")
        self.logger.info(f"Mensajes procesados hoy: {report['message_bus_stats']['messages_sent']}")
        self.logger.info(f"{'='*60}\n")
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes entrantes"""
        
        if message.msg_type == MessageType.HEARTBEAT:
            return await self._handle_heartbeat(message)
        
        elif message.msg_type == MessageType.ALERT:
            return await self._handle_alert(message)
        
        elif message.msg_type == MessageType.ERROR:
            return await self._handle_error(message)
        
        elif message.task_type == "STATUS_REQUEST":
            return self._handle_status_request(message)
        
        elif message.task_type == "EMERGENCY_STOP":
            return await self._handle_emergency_stop(message)
        
        elif message.task_type == "DECISION_REQUEST":
            return await self._handle_decision_request(message)
        
        return None
    
    async def _handle_heartbeat(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar heartbeat de un agente"""
        payload = message.payload
        
        # Actualizar estado en DB
        try:
            await self.db.update_agent_state(
                message.from_agent,
                last_heartbeat=datetime.now(),
                state=payload.get("state", "UNKNOWN"),
                messages_processed=payload.get("processed", 0),
                errors_count=payload.get("errors", 0)
            )
        except Exception as e:
            pass  # No bloquear por errores de DB
        
        return None
    
    async def _handle_alert(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar alerta de un agente"""
        severity = message.payload.get("severity", "WARNING")
        self.logger.warning(f"🚨 ALERTA de {message.from_agent}: {message.payload}")
        
        # Si es crítica, tomar acción inmediata
        if severity == "CRITICAL":
            await self._handle_critical_alert(message)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"received": True, "action_taken": severity}
        )
    
    async def _handle_critical_alert(self, message: AgentMessage):
        """Manejar alerta crítica"""
        self.logger.error(f"🚨 ALERTA CRÍTICA de {message.from_agent}: {message.payload}")
        
        # Notificar a Risk Manager
        await self.send_message(self.create_task_message(
            to_agent="RISK_MANAGER",
            task_type="CRITICAL_ALERT",
            priority=TaskPriority.CRITICAL,
            payload={
                "source": message.from_agent,
                "alert": message.payload,
                "timestamp": datetime.now().isoformat()
            }
        ))
    
    async def _handle_error(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar error de un agente"""
        self.logger.error(f"❌ ERROR de {message.from_agent}: {message.payload}")
        return None
    
    def _handle_status_request(self, message: AgentMessage) -> AgentMessage:
        """Manejar solicitud de estado"""
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "status": self.system_status.copy(),
                "healthy": self.system_healthy,
                "trading_active": self.trading_active,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def _handle_emergency_stop(self, message: AgentMessage) -> AgentMessage:
        """Manejar parada de emergencia"""
        self.logger.critical(f"🛑 EMERGENCY STOP solicitado por {message.from_agent}")
        
        # Notificar a Risk Manager (tiene poder de veto)
        await self.send_message(self.create_task_message(
            to_agent="RISK_MANAGER",
            task_type="EMERGENCY_STOP",
            priority=TaskPriority.CRITICAL,
            payload={
                "requested_by": message.from_agent,
                "reason": message.payload.get("reason", "Unknown"),
                "timestamp": datetime.now().isoformat()
            }
        ))
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"emergency_stop_initiated": True}
        )
    
    async def _handle_decision_request(self, message: AgentMessage) -> AgentMessage:
        """Manejar solicitud de decisión"""
        decision_type = message.payload.get("type")
        
        if decision_type == "STRATEGY_ACTIVATION":
            return await self._decide_strategy_activation(message)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"decision": "DECLINED", "reason": "Unknown decision type"}
        )
    
    async def _decide_strategy_activation(self, message: AgentMessage) -> AgentMessage:
        """Decidir sobre activación de estrategia"""
        strategy_id = message.payload.get("strategy_id")
        risk_score = message.payload.get("risk_score", 0.5)
        
        # Consultar con Risk Manager
        await self.send_message(self.create_task_message(
            to_agent="RISK_MANAGER",
            task_type="EVALUATE_STRATEGY",
            priority=TaskPriority.HIGH,
            payload={
                "strategy_id": strategy_id,
                "risk_score": risk_score
            }
        ))
        
        # La decisión real vendrá del Risk Manager
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"decision": "PENDING_RISK_REVIEW"}
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def _record_decision(self, decision: Dict[str, Any]):
        """Registrar una decisión tomada"""
        decision["decision_id"] = len(self.recent_decisions)
        self.recent_decisions.append(decision)
        
        # Mantener solo las últimas 100
        if len(self.recent_decisions) > 100:
            self.recent_decisions = self.recent_decisions[-100:]
        
        self.last_decision = decision
    
    def get_ceo_dashboard(self) -> Dict[str, Any]:
        """Obtener dashboard del CEO"""
        return {
            "system_status": self.system_status,
            "healthy": self.system_healthy,
            "trading_active": self.trading_active,
            "daily_pnl": self.daily_pnl,
            "last_decision": self.last_decision,
            "recent_decisions_count": len(self.recent_decisions),
            "uptime": (datetime.now() - self.start_time).total_seconds()
        }
    
    def __repr__(self) -> str:
        return f"<CEOAgent(state={self.state.value}, healthy={self.system_healthy})>"
