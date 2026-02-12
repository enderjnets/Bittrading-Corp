"""
⚡ BACKTEST ORCHESTRATOR AGENT - Head of Backtesting
=====================================================
Coordina backtesting masivo usando toda la infraestructura de workers.

Responsabilidades:
- Gestión de cola de backtests
- Distribución de WUs a workers
- Monitoreo de progreso
- Agregación de resultados
- Detección de anomalías
- Optimización de uso de recursos

Author: Bittrading Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from agents.base_agent import (
    BaseAgent, AgentConfig, AgentMessage, AgentState, 
    MessageType, TaskPriority
)

# ═══════════════════════════════════════════════════════════════════
# ENUMS Y ESTRUCTURAS
# ═══════════════════════════════════════════════════════════════════

class BacktestStatus(Enum):
    """Estados de un backtest"""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

@dataclass
class BacktestTask:
    """Tarea de backtest"""
    task_id: str
    strategy_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    parameters: Dict[str, Any]
    rules: Dict[str, Any]
    priority: int = 5
    status: BacktestStatus = BacktestStatus.QUEUED
    worker_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    timeout_seconds: int = 300

@dataclass
class WorkerInfo:
    """Información de un worker"""
    worker_id: str
    status: str = "IDLE"
    last_heartbeat: datetime = field(default_factory=datetime.now)
    current_tasks: int = 0
    max_tasks: int = 2
    avg_completion_time: float = 0.0
    success_rate: float = 1.0
    capabilities: List[str] = field(default_factory=list)

# ═══════════════════════════════════════════════════════════════════
# BACKTEST ORCHESTRATOR AGENT
# ═══════════════════════════════════════════════════════════════════

class BacktestOrchestratorAgent(BaseAgent):
    """
    Backtest Orchestrator - Coordina todo el backtesting del sistema.
    
    Maneja:
    - Cola de backtests priorizada
    - Distribución a workers
    - Failover automático
    - Aggregación de resultados
    - Métricas de performance
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        orchestrator_config = AgentConfig(
            agent_id="BACKTEST_ORCHESTRATOR",
            agent_name="Head of Backtesting",
            agent_type="ORCHESTRATOR",
            log_level="INFO",
            cycle_interval=10,
            custom_config=config or {}
        )
        
        super().__init__(orchestrator_config, message_bus)
        
        # Configuración
        self.max_concurrent_tasks = 50
        self.max_retries = 3
        self.default_timeout = 300  # 5 minutos
        self.worker_check_interval = 30
        
        # Cola de backtests
        self.backtest_queue: List[BacktestTask] = []
        self.backtest_index: Dict[str, BacktestTask] = {}  # task_id -> task
        
        # Workers
        self.workers: Dict[str, WorkerInfo] = {}
        
        # Resultados
        self.results_buffer: List[Dict[str, Any]] = []
        self.completed_backtests: List[BacktestTask] = []
        
        # Métricas
        self.total_backtests = 0
        self.successful_backtests = 0
        self.failed_backtests = 0
        self.total_execution_time = 0.0
        
        # Worker connection (coordinator existente)
        self.coordinator_url = "100.77.179.14:5001"
        self.connected = False
        
        # Database
        from shared.database import get_database, BacktestResult as DBBacktestResult
        self.db = get_database()
        self.DBBacktestResult = DBBacktestResult
        
        self.logger.info("⚡ Backtest Orchestrator Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Inicializar orchestrator"""
        self.logger.info("🚀 Iniciando Backtest Orchestrator...")
        
        # Conectar con coordinator
        await self._connect_to_coordinator()
        
        # Suscribirse a mensajes
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                task_types=[
                    "BACKTEST_STRATEGIES",
                    "BACKTEST_SINGLE",
                    "CANCEL_BACKTEST",
                    "GET_BACKTEST_STATUS",
                    "GET_RESULTS"
                ]
            )
        
        # Iniciar monitoreo de workers
        asyncio.create_task(self._worker_monitor_loop())
        
        self.logger.info("✅ Backtest Orchestrator listo")
    
    async def on_shutdown(self):
        """Shutdown"""
        self.logger.info("🛑 Deteniendo Backtest Orchestrator...")
        
        # Cancelar tareas pendientes
        for task in self.backtest_queue:
            task.status = BacktestStatus.CANCELLED
        
        # Desconectar del coordinator
        if self.connected:
            try:
                # await self._disconnect_from_coordinator()
                pass
            except:
                pass
        
        self.logger.info("✅ Backtest Orchestrator detenido")
    
    async def run_cycle(self):
        """Ciclo principal"""
        # Distribuir tareas a workers disponibles
        await self._distribute_tasks()
        
        # Verificar timeouts
        await self._check_timeouts()
        
        # Limpiar tareas completadas
        await self._cleanup_completed()
        
        # Reportar progreso
        await self._report_progress()
    
    # ═══════════════════════════════════════════════════════════════
    # CONEXIÓN CON COORDINATOR
    # ═══════════════════════════════════════════════════════════════
    
    async def _connect_to_coordinator(self):
        """Conectar con el coordinator de workers"""
        self.logger.info(f"🔗 Conectando a coordinator: {self.coordinator_url}")
        
        try:
            # Intentar conexión
            # En una implementación real, usarían el cliente del coordinator
            self.connected = True
            self.logger.info("✅ Conectado al coordinator")
        except Exception as e:
            self.logger.warning(f"No se pudo conectar al coordinator: {e}")
            self.connected = False
    
    async def _register_worker(self, worker_id: str, capabilities: List[str] = None):
        """Registrar un worker"""
        if worker_id not in self.workers:
            self.workers[worker_id] = WorkerInfo(
                worker_id=worker_id,
                capabilities=capabilities or ["backtest"]
            )
            self.logger.info(f"✅ Worker registrado: {worker_id}")
    
    async def _worker_monitor_loop(self):
        """Loop de monitoreo de workers"""
        while self.state == AgentState.RUNNING:
            try:
                await self._check_workers_health()
                await asyncio.sleep(self.worker_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error en worker monitor: {e}")
                await asyncio.sleep(5)
    
    async def _check_workers_health(self):
        """Verificar salud de workers"""
        now = datetime.now()
        timeout = timedelta(minutes=5)
        
        for worker_id, worker in list(self.workers.items()):
            if now - worker.last_heartbeat > timeout:
                self.logger.warning(f"⚠️ Worker desconectado: {worker_id}")
                # Marcar tareas como huérfanas
                await self._handle_orphaned_tasks(worker_id)
                del self.workers[worker_id]
    
    async def _handle_orphaned_tasks(self, worker_id: str):
        """Manejar tareas huérfanas de un worker caído"""
        for task in self.backtest_queue:
            if task.worker_id == worker_id and task.status == BacktestStatus.RUNNING:
                if task.retries < self.max_retries:
                    task.status = BacktestStatus.QUEUED
                    task.worker_id = None
                    task.retries += 1
                    self.logger.info(f"🔄 Reencolando tarea {task.task_id} (retry {task.retries})")
                else:
                    task.status = BacktestStatus.FAILED
                    task.error = "Worker desconectado tras múltiples reintentos"
                    self.failed_backtests += 1
    
    # ═══════════════════════════════════════════════════════════════
    # GESTIÓN DE COLA
    # ═══════════════════════════════════════════════════════════════
    
    async def _add_backtest_task(
        self,
        strategy_id: str,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        parameters: Dict[str, Any],
        rules: Dict[str, Any],
        priority: int = 5,
        timeout: int = 300
    ) -> str:
        """Agregar tarea de backtest a la cola"""
        task_id = f"bt_{uuid.uuid4().hex[:12]}"
        
        task = BacktestTask(
            task_id=task_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            parameters=parameters,
            rules=rules,
            priority=priority,
            timeout_seconds=timeout
        )
        
        self.backtest_queue.append(task)
        self.backtest_index[task_id] = task
        self.total_backtests += 1
        
        self.logger.debug(f"📝 Tarea agregada: {task_id} ({symbol} {timeframe})")
        
        return task_id
    
    async def _distribute_tasks(self):
        """Distribuir tareas a workers disponibles"""
        if not self.connected:
            self.logger.warning("No conectado al coordinator, imposible distribuir")
            return
        
        # Buscar workers disponibles
        available_workers = [
            w for w in self.workers.values()
            if w.status == "IDLE" and w.current_tasks < w.max_tasks
        ]
        
        if not available_workers:
            return
        
        # Obtener tareas pendientes ordenadas por prioridad
        pending_tasks = [
            t for t in self.backtest_queue
            if t.status == BacktestStatus.QUEUED
        ]
        pending_tasks.sort(key=lambda t: (t.priority, t.created_at))
        
        # Distribuir
        for worker in available_workers:
            if not pending_tasks:
                break
            
            task = pending_tasks.pop(0)
            
            # Asignar tarea al worker
            success = await self._assign_task_to_worker(task, worker)
            
            if success:
                task.status = BacktestStatus.RUNNING
                task.worker_id = worker.worker_id
                task.started_at = datetime.now()
                worker.current_tasks += 1
                worker.status = "BUSY"
                
                self.logger.info(f"📤 Tarea {task.task_id} asignada a {worker.worker_id}")
            else:
                # Poner tarea de vuelta en cola
                task.status = BacktestStatus.QUEUED
    
    async def _assign_task_to_worker(self, task: BacktestTask, worker: WorkerInfo) -> bool:
        """Asignar tarea específica a un worker"""
        try:
            # Preparar payload del WU
            wu_payload = {
                "task_id": task.task_id,
                "strategy_id": task.strategy_id,
                "strategy_name": task.strategy_name,
                "symbol": task.symbol,
                "timeframe": task.timeframe,
                "parameters": task.parameters,
                "rules": task.rules,
                "timeout": task.timeout_seconds
            }
            
            # En implementación real, enviar al coordinator
            # await send_to_coordinator(worker.worker_id, wu_payload)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error asignando tarea: {e}")
            return False
    
    async def _check_timeouts(self):
        """Verificar tareas que han excedido timeout"""
        now = datetime.now()
        timeout_delta = timedelta(seconds=30)  # Grace period
        
        for task in self.backtest_queue:
            if task.status == BacktestStatus.RUNNING:
                elapsed = now - task.started_at
                
                if elapsed.total_seconds() > task.timeout_seconds + timeout_delta.total_seconds():
                    self.logger.warning(f"⏰ Timeout en tarea {task.task_id}")
                    
                    if task.retries < self.max_retries:
                        task.status = BacktestStatus.QUEUED
                        task.worker_id = None
                        task.retries += 1
                        
                        # Liberar worker
                        if task.worker_id in self.workers:
                            self.workers[task.worker_id].current_tasks -= 1
                            if self.workers[task.worker_id].current_tasks == 0:
                                self.workers[task.worker_id].status = "IDLE"
                    else:
                        task.status = BacktestStatus.TIMEOUT
                        task.error = "Timeout tras múltiples reintentos"
                        self.failed_backtests += 1
    
    async def _cleanup_completed(self):
        """Limpiar tareas completadas"""
        completed = [
            t for t in self.backtest_queue
            if t.status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED, BacktestStatus.CANCELLED]
        ]
        
        for task in completed:
            if task.status == BacktestStatus.COMPLETED:
                self.completed_backtests.append(task)
                self.successful_backtests += 1
            
            # Remover de cola activa
            if task.task_id in self.backtest_index:
                del self.backtest_index[task.task_id]
            
            self.backtest_queue.remove(task)
    
    # ═══════════════════════════════════════════════════════════════
    # RESULTADOS
    # ═══════════════════════════════════════════════════════════════
    
    async def _handle_backtest_result(self, result: Dict[str, Any]):
        """Procesar resultado de backtest"""
        task_id = result.get("task_id")
        
        if task_id not in self.backtest_index:
            self.logger.warning(f"Resultado para tarea desconocida: {task_id}")
            return
        
        task = self.backtest_index[task_id]
        task.result = result
        task.completed_at = datetime.now()
        task.progress = 100.0
        
        # Calcular tiempo de ejecución
        if task.started_at:
            execution_time = (task.completed_at - task.started_at).total_seconds()
            self.total_execution_time += execution_time
            
            # Actualizar métricas del worker
            if task.worker_id in self.workers:
                worker = self.workers[task.worker_id]
                worker.current_tasks -= 1
                
                # Actualizar tiempo promedio
                if worker.avg_completion_time == 0:
                    worker.avg_completion_time = execution_time
                else:
                    worker.avg_completion_time = (worker.avg_completion_time + execution_time) / 2
                
                if worker.current_tasks == 0:
                    worker.status = "IDLE"
        
        # Determinar estado
        if result.get("status") == "SUCCESS":
            task.status = BacktestStatus.COMPLETED
            
            # Guardar en base de datos
            await self._save_result(task, result)
            
            # Notificar a Strategy Selector
            await self._notify_result(task, result)
        else:
            task.status = BacktestStatus.FAILED
            task.error = result.get("error", "Unknown error")
            self.failed_backtests += 1
    
    async def _save_result(self, task: BacktestTask, result: Dict[str, Any]):
        """Guardar resultado en base de datos"""
        try:
            db_result = self.DBBacktestResult(
                result_id=task.task_id,
                strategy_id=task.strategy_id,
                worker_id=task.worker_id,
                symbol=task.symbol,
                timeframe=task.timeframe,
                start_date=datetime.fromisoformat(result.get("start_date", datetime.now().isoformat())),
                end_date=datetime.fromisoformat(result.get("end_date", datetime.now().isoformat())),
                total_return=result.get("total_return", 0),
                annual_return=result.get("annual_return", 0),
                sharpe_ratio=result.get("sharpe_ratio", 0),
                sortino_ratio=result.get("sortino_ratio", 0),
                max_drawdown=result.get("max_drawdown", 0),
                win_rate=result.get("win_rate", 0),
                profit_factor=result.get("profit_factor", 0),
                total_trades=result.get("total_trades", 0),
                parameters=task.parameters,
                equity_curve=result.get("equity_curve"),
                trades_list=result.get("trades"),
                execution_time=result.get("execution_time", 0)
            )
            await self.db.create(db_result)
        except Exception as e:
            self.logger.warning(f"No se pudo guardar resultado: {e}")
    
    async def _notify_result(self, task: BacktestTask, result: Dict[str, Any]):
        """Notificar resultado a otros agentes"""
        # Notificar al CEO
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="BACKTEST_COMPLETED",
            priority=TaskPriority.NORMAL,
            payload={
                "task_id": task.task_id,
                "strategy_id": task.strategy_id,
                "symbol": task.symbol,
                "sharpe_ratio": result.get("sharpe_ratio", 0),
                "max_drawdown": result.get("max_drawdown", 0),
                "total_return": result.get("total_return", 0)
            }
        ))
        
        # Notificar al Strategy Selector
        await self.send_message(self.create_task_message(
            to_agent="STRATEGY_SELECTOR",
            task_type="BACKTEST_RESULT",
            priority=TaskPriority.NORMAL,
            payload={
                "strategy_id": task.strategy_id,
                "symbol": task.symbol,
                "result": result
            }
        ))
    
    async def _report_progress(self):
        """Reportar progreso al CEO"""
        stats = self.get_orchestrator_status()
        
        await self.send_message(self.create_task_message(
            to_agent="CEO",
            task_type="BACKTEST_PROGRESS",
            priority=TaskPriority.LOW,
            payload={
                "queued": stats["queued"],
                "running": stats["running"],
                "completed": stats["completed"],
                "failed": stats["failed"],
                "workers_active": stats["workers_active"],
                "avg_execution_time": stats["avg_execution_time"]
            }
        ))
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes entrantes"""
        
        if message.task_type == "BACKTEST_STRATEGIES":
            return await self._handle_backtest_strategies(message)
        
        elif message.task_type == "BACKTEST_SINGLE":
            return await self._handle_backtest_single(message)
        
        elif message.task_type == "CANCEL_BACKTEST":
            return await self._handle_cancel_backtest(message)
        
        elif message.task_type == "GET_BACKTEST_STATUS":
            return self._handle_get_status(message)
        
        elif message.task_type == "GET_RESULTS":
            return self._handle_get_results(message)
        
        elif message.task_type == "WORKER_HEARTBEAT":
            return await self._handle_worker_heartbeat(message)
        
        elif message.task_type == "BACKTEST_RESULT":
            return await self._handle_result_report(message)
        
        return None
    
    async def _handle_backtest_strategies(self, message: AgentMessage) -> AgentMessage:
        """Procesar solicitud de backtest para múltiples estrategias"""
        strategies = message.payload.get("strategies", [])
        symbols = message.payload.get("symbols", ["BTC/USD"])
        timeframes = message.payload.get("timeframes", ["1h"])
        priority = message.payload.get("priority", 5)
        
        self.logger.info(f"📋 Recibida solicitud de backtest: {len(strategies)} estrategias")
        
        task_ids = []
        
        for strategy in strategies:
            for symbol in symbols:
                for timeframe in timeframes:
                    task_id = await self._add_backtest_task(
                        strategy_id=strategy["strategy_id"],
                        strategy_name=strategy["strategy_name"],
                        symbol=symbol,
                        timeframe=timeframe,
                        parameters=strategy.get("parameters", {}),
                        rules=strategy.get("rules", {}),
                        priority=priority
                    )
                    task_ids.append(task_id)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "tasks_created": len(task_ids),
                "task_ids": task_ids,
                "status": "QUEUED"
            }
        )
    
    async def _handle_backtest_single(self, message: AgentMessage) -> AgentMessage:
        """Backtest de una sola estrategia"""
        strategy = message.payload.get("strategy", {})
        
        task_id = await self._add_backtest_task(
            strategy_id=strategy["strategy_id"],
            strategy_name=strategy["strategy_name"],
            symbol=strategy.get("symbol", "BTC/USD"),
            timeframe=strategy.get("timeframe", "1h"),
            parameters=strategy.get("parameters", {}),
            rules=strategy.get("rules", {}),
            priority=message.priority.value if hasattr(message.priority, 'value') else 5
        )
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "task_id": task_id,
                "status": "QUEUED"
            }
        )
    
    async def _handle_cancel_backtest(self, message: AgentMessage) -> AgentMessage:
        """Cancelar backtest(s)"""
        task_ids = message.payload.get("task_ids", [])
        
        cancelled = []
        for task_id in task_ids:
            if task_id in self.backtest_index:
                task = self.backtest_index[task_id]
                if task.status == BacktestStatus.QUEUED:
                    task.status = BacktestStatus.CANCELLED
                    cancelled.append(task_id)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "cancelled": cancelled,
                "count": len(cancelled)
            }
        )
    
    def _handle_get_status(self, message: AgentMessage) -> AgentMessage:
        """Obtener estado de backtests"""
        status = self.get_orchestrator_status()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result=status
        )
    
    def _handle_get_results(self, message: AgentMessage) -> AgentMessage:
        """Obtener resultados de backtests"""
        filters = message.payload or {}
        
        results = self.completed_backtests
        
        # Filtrar por estrategia
        if "strategy_id" in filters:
            results = [r for r in results if r.strategy_id == filters["strategy_id"]]
        
        # Filtrar por símbolo
        if "symbol" in filters:
            results = [r for r in results if r.symbol == filters["symbol"]]
        
        # Limitar
        limit = filters.get("limit", 20)
        results = results[-limit:]
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "results": [
                    {
                        "task_id": r.task_id,
                        "strategy_id": r.strategy_id,
                        "symbol": r.symbol,
                        "timeframe": r.timeframe,
                        "result": r.result
                    }
                    for r in results
                ],
                "total_count": len(self.completed_backtests)
            }
        )
    
    async def _handle_worker_heartbeat(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar heartbeat de worker"""
        worker_id = message.payload.get("worker_id")
        status = message.payload.get("status")
        current_tasks = message.payload.get("current_tasks", 0)
        
        if worker_id not in self.workers:
            await self._register_worker(worker_id)
        
        self.workers[worker_id].last_heartbeat = datetime.now()
        self.workers[worker_id].status = status or "IDLE"
        self.workers[worker_id].current_tasks = current_tasks
        
        return None
    
    async def _handle_result_report(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar reporte de resultado de worker"""
        await self._handle_backtest_result(message.payload)
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Obtener estado del orchestrator"""
        queued = len([t for t in self.backtest_queue if t.status == BacktestStatus.QUEUED])
        running = len([t for t in self.backtest_queue if t.status == BacktestStatus.RUNNING])
        completed = len(self.completed_backtests)
        failed = self.failed_backtests
        
        total = completed + failed
        success_rate = (completed / total * 100) if total > 0 else 0
        
        avg_time = (self.total_execution_time / completed) if completed > 0 else 0
        
        workers_active = len([w for w in self.workers.values() if w.status == "BUSY"])
        
        return {
            "queued": queued,
            "running": running,
            "completed": completed,
            "failed": failed,
            "total_backtests": self.total_backtests,
            "success_rate": round(success_rate, 2),
            "workers_registered": len(self.workers),
            "workers_active": workers_active,
            "avg_execution_time": round(avg_time, 2),
            "connected_to_coordinator": self.connected,
            "coordinator_url": self.coordinator_url
        }
    
    def __repr__(self) -> str:
        status = self.get_orchestrator_status()
        return f"<BacktestOrchestrator(queued={status['queued']}, running={status['running']}, success={status['success_rate']}%)>"
