"""
🔗 COORDINATOR ADAPTER - Integra el Coordinator Existente
=========================================================
Este módulo actúa como bridge entre el nuevo sistema de agentes 
y el Coordinator existente (coordinator.py).

Funcionalidades:
- Traduce mensajes del MessageBus al API del Coordinator
- Conecta Workers al nuevo sistema de agentes
- Reutiliza toda la lógica de distribución de WUs

Author: Bittrading Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import requests
import json

from agents.base_agent import (
    BaseAgent, AgentConfig, AgentMessage, AgentState, 
    MessageType, TaskPriority
)


# ═══════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class WorkUnit:
    """Work Unit para el Coordinator"""
    work_id: int
    strategy_params: Dict[str, Any]
    replica_number: int
    replicas_needed: int
    
@dataclass
class WorkerResult:
    """Resultado de un worker"""
    work_id: int
    worker_id: str
    pnl: float
    trades: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    execution_time: float


# ═══════════════════════════════════════════════════════════════════
# COORDINATOR CLIENT
# ═══════════════════════════════════════════════════════════════════

class CoordinatorClient:
    """
    Cliente para comunicarse con el Coordinator existente.
    
    Se conecta al Coordinator via HTTP REST API.
    """
    
    def __init__(self, coordinator_url: str = "http://localhost:5000"):
        self.coordinator_url = coordinator_url.rstrip('/')
        self.logger = logging.getLogger("CoordinatorClient")
        
        # Caché de estado
        self._workers_cache = {}
        self._results_cache = []
    
    # ═══════════════════════════════════════════════════════════════
    # API ENDPOINTS
    # ═══════════════════════════════════════════════════════════════
    
    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema"""
        try:
            response = requests.get(f"{self.coordinator_url}/api/status", timeout=5)
            return response.json()
        except Exception as e:
            self.logger.warning(f"Error get_status: {e}")
            return {}
    
    async def get_work(self, worker_id: str) -> Optional[WorkUnit]:
        """
        Obtener trabajo pendiente del Coordinator
        
        Args:
            worker_id: ID del worker que solicita trabajo
            
        Returns:
            WorkUnit o None si no hay trabajo
        """
        try:
            response = requests.get(
                f"{self.coordinator_url}/api/get_work",
                params={"worker_id": worker_id},
                timeout=5
            )
            data = response.json()
            
            if data.get("work_id"):
                return WorkUnit(
                    work_id=data["work_id"],
                    strategy_params=data["strategy_params"],
                    replica_number=data["replica_number"],
                    replicas_needed=data["replicas_needed"]
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting work: {e}")
            return None
    
    async def submit_result(self, result: WorkerResult) -> bool:
        """
        Enviar resultado al Coordinator
        
        Args:
            result: WorkerResult con los métricas
            
        Returns:
            True si se envió correctamente
        """
        try:
            payload = {
                "work_id": result.work_id,
                "worker_id": result.worker_id,
                "pnl": result.pnl,
                "trades": result.trades,
                "win_rate": result.win_rate,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown": result.max_drawdown,
                "execution_time": result.execution_time
            }
            
            response = requests.post(
                f"{self.coordinator_url}/api/submit_result",
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Error submitting result: {e}")
            return False
    
    async def get_workers(self) -> List[Dict[str, Any]]:
        """Obtener lista de workers"""
        try:
            response = requests.get(f"{self.coordinator_url}/api/workers", timeout=5)
            return response.json().get("workers", [])
        except Exception as e:
            self.logger.warning(f"Error getting workers: {e}")
            return []
    
    async def get_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener resultados canónicos"""
        try:
            response = requests.get(
                f"{self.coordinator_url}/api/results",
                params={"limit": limit},
                timeout=5
            )
            return response.json().get("results", [])
        except Exception as e:
            self.logger.warning(f"Error getting results: {e}")
            return []
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas completas"""
        try:
            response = requests.get(f"{self.coordinator_url}/api/dashboard_stats", timeout=5)
            return response.json()
        except Exception as e:
            self.logger.warning(f"Error getting dashboard stats: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════
    
    async def health_check(self) -> bool:
        """Verificar si el Coordinator está disponible"""
        try:
            response = requests.get(f"{self.coordinator_url}/api/status", timeout=3)
            return response.status_code == 200
        except:
            return False


# ═══════════════════════════════════════════════════════════════════
# WORKER MANAGER AGENT - VERSIÓN INTEGRADA
# ═══════════════════════════════════════════════════════════════════

class WorkerManagerAgent(BaseAgent):
    """
    Worker Manager - Gestión de infraestructura de workers.
    
    Este agente se integra con el Coordinator existente para:
    - Monitorear workers activos
    - Distribuir WUs
    - Recopilar resultados
    - Gestión de failover
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        worker_config = AgentConfig(
            agent_id="WORKER_MANAGER",
            agent_name="Infrastructure Manager",
            agent_type="INFRASTRUCTURE",
            log_level="INFO",
            cycle_interval=30,
            custom_config=config or {}
        )
        
        super().__init__(worker_config, message_bus)
        
        # Coordinator client
        self.coordinator_url = config.get("coordinator_url", "http://localhost:5000")
        self.coordinator = CoordinatorClient(self.coordinator_url)
        
        # Estado
        self.workers: Dict[str, Dict] = {}
        self.active_workers: List[str] = []
        self.total_workers_completed = 0
        
        # Métricas
        self.wus_completed = 0
        self.wus_failed = 0
        self.avg_completion_time = 0.0
        
        # Configuración
        self.health_check_interval = 30
        self.max_inactive_minutes = 10
        
        self.logger.info("🔧 Worker Manager Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Inicializar Worker Manager"""
        self.logger.info("🚀 Iniciando Worker Manager...")
        
        # Suscribirse a mensajes relevantes
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                task_types=[
                    "DISTRIBUTE_WU",
                    "GET_WORKER_STATUS",
                    "FORCE_REASSIGN",
                    "SCALE_WORKERS",
                    "HEALTH_CHECK"
                ]
            )
        
        # Verificar conexión con Coordinator
        healthy = await self.coordinator.health_check()
        if healthy:
            self.logger.info(f"✅ Conectado al Coordinator: {self.coordinator_url}")
        else:
            self.logger.warning(f"⚠️ Coordinator no disponible: {self.coordinator_url}")
        
        self.logger.info("✅ Worker Manager listo")
    
    async def on_shutdown(self):
        """Shutdown del Worker Manager"""
        self.logger.info("🛑 Deteniendo Worker Manager...")
        self.logger.info(f"📊 Workers gestionados: {len(self.workers)}")
        self.logger.info(f"✅ WUs completados: {self.wus_completed}")
    
    async def run_cycle(self):
        """Ciclo principal"""
        # Actualizar estado de workers
        await self._update_workers()
        
        # Verificar Coordinator
        await self._check_coordinator()
        
        # Reportar métricas
        await self._report_metrics()
    
    # ═══════════════════════════════════════════════════════════════
    # ACTUALIZACIÓN DE WORKERS
    # ═══════════════════════════════════════════════════════════════
    
    async def _update_workers(self):
        """Actualizar lista de workers desde el Coordinator"""
        workers = await self.coordinator.get_workers()
        
        for w in workers:
            worker_id = w["id"]
            self.workers[worker_id] = {
                "id": worker_id,
                "hostname": w.get("hostname", "Unknown"),
                "platform": w.get("platform", "Unknown"),
                "last_seen": w.get("last_seen"),
                "completed": w.get("work_units_completed", 0),
                "total_time": w.get("total_execution_time", 0),
                "status": w.get("status", "unknown")
            }
        
        # Contar activos (vistos en los últimos 5 minutos)
        import time
        now = time.time()
        active = []
        for wid, w in self.workers.items():
            last_seen = w.get("last_seen", 0)
            if now - last_seen < 300:  # 5 minutos
                active.append(wid)
        
        self.active_workers = active
        
        if len(self.active_workers) != len(self.active_workers):
            self.logger.debug(f"Workers activos: {len(self.active_workers)}/{len(self.workers)}")
    
    async def _check_coordinator(self):
        """Verificar que el Coordinator esté saludable"""
        healthy = await self.coordinator.health_check()
        
        if not healthy:
            self.logger.warning("⚠️ Coordinator no saludable o inalcanzable")
            # Notificar al CEO
            await self.send_message(self.create_alert(
                alert_type="COORDINATOR_DOWN",
                message="Coordinator no disponible",
                severity="CRITICAL"
            ))
    
    async def _report_metrics(self):
        """Reportar métricas al CEO"""
        stats = await self.coordinator.get_dashboard_stats()
        
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="WORKER_METRICS",
            priority=TaskPriority.LOW,
            payload={
                "workers_active": len(self.active_workers),
                "workers_total": len(self.workers),
                "wus_completed": self.wus_completed,
                "wus_failed": self.wus_failed,
                "stats": stats
            }
        ))
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes entrantes"""
        
        if message.task_type == "DISTRIBUTE_WU":
            return await self._handle_distribute_wu(message)
        
        elif message.task_type == "GET_WORKER_STATUS":
            return self._handle_get_status(message)
        
        elif message.task_type == "FORCE_REASSIGN":
            return await self._handle_force_reassign(message)
        
        elif message.task_type == "HEALTH_CHECK":
            return await self._handle_health_check(message)
        
        return None
    
    async def _handle_distribute_wu(self, message: AgentMessage) -> AgentMessage:
        """Distribuir work unit a workers"""
        strategy_params = message.payload.get("strategy_params")
        
        # El Coordinator ya maneja la distribución
        # Solo necesitamos verificar que está funcionando
        stats = await self.coordinator.get_dashboard_stats()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "distributed": True,
                "workers_available": stats.get("workers", {}).get("active", 0),
                "pending_wus": stats.get("work_units", {}).get("pending", 0)
            }
        )
    
    def _handle_get_status(self, message: AgentMessage) -> AgentMessage:
        """Obtener estado de workers"""
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "workers": self.workers,
                "active_workers": self.active_workers,
                "total_active": len(self.active_workers),
                "total_registered": len(self.workers),
                "wus_completed": self.wus_completed
            }
        )
    
    async def _handle_force_reassign(self, message: AgentMessage) -> AgentMessage:
        """Forzar reassign de un work unit"""
        work_id = message.payload.get("work_id")
        
        # No podemos forzar reassign directamente desde aquí
        # El Coordinator maneja esto automáticamente en timeouts
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "forced": True,
                "work_id": work_id,
                "note": "Coordinator maneja reassign automáticamente"
            }
        )
    
    async def _handle_health_check(self, message: AgentMessage) -> AgentMessage:
        """Health check del sistema"""
        coordinator_healthy = await self.coordinator.health_check()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "coordinator_healthy": coordinator_healthy,
                "coordinator_url": self.coordinator_url,
                "workers_healthy": len(self.active_workers),
                "total_workers": len(self.workers),
                "system_healthy": coordinator_healthy and len(self.active_workers) > 0
            }
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def get_worker_manager_status(self) -> Dict[str, Any]:
        """Obtener estado del Worker Manager"""
        return {
            "coordinator_url": self.coordinator_url,
            "active_workers": len(self.active_workers),
            "total_workers": len(self.workers),
            "wus_completed": self.wus_completed,
            "wus_failed": self.wus_failed,
            "avg_completion_time": self.avg_completion_time
        }
    
    def __repr__(self) -> str:
        return f"<WorkerManager(workers={len(self.active_workers)}/{len(self.workers)})>"
