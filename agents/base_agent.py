"""
🤖 BASE AGENT - Clase Base para Todos los Agentes de Bittrading Trading Corp
===========================================================================
Framework base que heredarán todos los agentes especializados.

Author: Bittrading Trading Corp
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import json
import logging
import asyncio
import uuid
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# ENUMS Y ESTRUCTURAS
# ═══════════════════════════════════════════════════════════════════

class AgentState(Enum):
    """Estados posibles de un agente"""
    INITIALIZING = "INITIALIZING"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PROCESSING = "PROCESSING"
    WAITING = "WAITING"
    ERROR = "ERROR"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    OFFLINE = "OFFLINE"

class TaskPriority(Enum):
    """Prioridades de tareas"""
    CRITICAL = 1    # Emergency stops, veto
    HIGH = 2        # Decisiones de trading
    NORMAL = 5      # Operaciones regulares
    LOW = 10        # Background tasks
    IDLE = 20       # Cuando no hay nada que hacer

class MessageType(Enum):
    """Tipos de mensajes entre agentes"""
    TASK = "TASK"
    RESULT = "RESULT"
    STATUS = "STATUS"
    ALERT = "ALERT"
    COMMAND = "COMMAND"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"

# ═══════════════════════════════════════════════════════════════════
# ESTRUCTURAS DE DATOS
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AgentMessage:
    """Mensaje estándar entre agentes"""
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    msg_type: MessageType = MessageType.TASK
    priority: TaskPriority = TaskPriority.NORMAL
    task_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    requires_acknowledgment: bool = False
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        return {
            "msg_id": self.msg_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "msg_type": self.msg_type.value,
            "priority": self.priority.value,
            "task_type": self.task_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "requires_acknowledgment": self.requires_acknowledgment,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Crear desde diccionario"""
        data["msg_type"] = MessageType(data["msg_type"])
        data["priority"] = TaskPriority(data["priority"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data["deadline"]:
            data["deadline"] = datetime.fromisoformat(data["deadline"])
        return cls(**data)

@dataclass
class AgentConfig:
    """Configuración de un agente"""
    agent_id: str
    agent_name: str
    agent_type: str
    log_level: str = "INFO"
    cycle_interval: int = 60  # segundos
    max_retries: int = 3
    timeout: int = 300  # segundos
    enabled: bool = True
    custom_config: Dict[str, Any] = field(default_factory=dict)

# ═══════════════════════════════════════════════════════════════════
# CLASE BASE DEL AGENTE
# ═══════════════════════════════════════════════════════════════════

class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes de Bittrading Trading Corp.
    
    Proporciona:
    - Ciclo de vida del agente
    - Sistema de mensajería
    - Logging centralizado
    - Estado y health checks
    - Configuración individual
    """
    
    def __init__(self, config: AgentConfig, message_bus=None):
        self.config = config
        self.agent_id = config.agent_id
        self.agent_name = config.agent_name
        self.state = AgentState.INITIALIZING
        self.state_reason = ""
        self.message_bus = message_bus
        self.logger = None
        self.message_queue: List[AgentMessage] = []
        self.processed_messages: int = 0
        self.errors_count: int = 0
        self.last_activity: datetime = datetime.now()
        self.start_time: datetime = datetime.now()
        self.last_heartbeat: datetime = datetime.now()
        self.tasks_in_progress: Dict[str, AgentMessage] = {}
        
        # Callbacks opcionales
        self.on_state_change: Optional[Callable[[AgentState, AgentState], None]] = None
        self.on_message: Optional[Callable[[AgentMessage], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # Inicializar logging
        self._setup_logging()
        
        # Registrar en message bus si existe
        if self.message_bus:
            self.message_bus.register_agent(self)
    
    def _setup_logging(self):
        """Configurar logging específico del agente"""
        log_path = Path("/Users/enderj/Bittrading_Trading_Corp/logs/agents")
        log_path.mkdir(parents=True, exist_ok=True)
        
        log_file = log_path / f"{self.agent_id}.log"
        
        # Configurar logger
        self.logger = logging.getLogger(self.agent_id)
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Evitar duplicados
        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_format = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_format = logging.Formatter(
                f'[{self.agent_id}] %(levelname)s: %(message)s'
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
        
        self.logger.info(f"🤖 Agente {self.agent_name} ({self.agent_id}) inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # ESTADO Y CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    def set_state(self, new_state: AgentState, reason: str = ""):
        """Cambiar estado del agente"""
        old_state = self.state
        self.state = new_state
        self.state_reason = reason
        self.last_activity = datetime.now()
        
        self.logger.info(f"Estado cambiado: {old_state.value} → {new_state.value} | Razón: {reason}")
        
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error en callback de estado: {e}")
    
    async def start(self):
        """Iniciar el agente"""
        self.logger.info(f"🚀 Iniciando agente {self.agent_name}")
        self.set_state(AgentState.IDLE, "Agente listo para operar")
        
        try:
            await self.on_start()
            self.set_state(AgentState.RUNNING, "Ciclo principal iniciado")
            await self._run_main_loop()
        except Exception as e:
            self.logger.error(f"❌ Error crítico: {e}")
            self.set_state(AgentState.ERROR, str(e))
            if self.on_error:
                self.on_error(e)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Apagado graceful del agente"""
        self.logger.info(f"🛑 Apagando agente {self.agent_name}")
        self.set_state(AgentState.SHUTTING_DOWN, " shutdown iniciado")
        
        try:
            await self.on_shutdown()
            
            # Cancelar tareas pendientes
            for task_id, task in self.tasks_in_progress.items():
                self.logger.warning(f"Tarea pendiente cancelada: {task_id}")
            
            self.set_state(AgentState.OFFLINE, "Agente detenido")
            self.logger.info(f"✅ Agente {self.agent_name} detenido correctamente")
            
        except Exception as e:
            self.logger.error(f"Error durante shutdown: {e}")
            self.set_state(AgentState.ERROR, f"Shutdown error: {e}")
    
    async def _run_main_loop(self):
        """Loop principal del agente"""
        while self.state == AgentState.RUNNING:
            try:
                # Procesar mensajes
                await self._process_messages()
                
                # Ejecutar ciclo principal
                await self.run_cycle()
                
                # Heartbeat
                self._send_heartbeat()
                
                # Sleep configurable
                await asyncio.sleep(self.config.cycle_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Loop principal cancelado")
                break
            except Exception as e:
                self.logger.error(f"Error en loop principal: {e}")
                self.errors_count += 1
                await asyncio.sleep(5)  # Backoff
    
    def _send_heartbeat(self):
        """Enviar heartbeat al message bus"""
        self.last_heartbeat = datetime.now()
        if self.message_bus:
            heartbeat_msg = AgentMessage(
                from_agent=self.agent_id,
                to_agent="CEO",
                msg_type=MessageType.HEARTBEAT,
                task_type="HEARTBEAT",
                payload={
                    "state": self.state.value,
                    "errors": self.errors_count,
                    "processed": self.processed_messages,
                    "tasks_active": len(self.tasks_in_progress)
                }
            )
            # No bloquear, enviar asíncrono
            asyncio.create_task(self.message_bus.publish(heartbeat_msg))
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS ABSTRACTOS (Override en cada agente)
    # ═══════════════════════════════════════════════════════════════
    
    @abstractmethod
    async def on_start(self):
        """Called when agent starts. Initialize resources."""
        pass
    
    @abstractmethod
    async def on_shutdown(self):
        """Called when agent shuts down. Cleanup resources."""
        pass
    
    @abstractmethod
    async def run_cycle(self):
        """Main agent cycle. Called every cycle_interval seconds."""
        pass
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Process incoming message from another agent.
        Return response message if needed.
        """
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # SISTEMA DE MENSAJERÍA
    # ═══════════════════════════════════════════════════════════════
    
    async def receive_message(self, message: AgentMessage):
        """Recibir mensaje del message bus"""
        self.logger.debug(f"📨 Mensaje recibido de {message.from_agent}: {message.task_type}")
        
        self.message_queue.append(message)
        
        if self.on_message:
            self.on_message(message)
        
        try:
            response = await self.process_message(message)
            self.processed_messages += 1
            self.last_activity = datetime.now()
            
            if response:
                await self.send_message(response)
                
        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
            self.errors_count += 1
            error_response = AgentMessage(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                msg_type=MessageType.ERROR,
                task_type=f"ERROR_{message.task_type}",
                payload={"error": str(e), "original_task": message.task_type}
            )
            await self.send_message(error_response)
    
    async def send_message(self, message: AgentMessage):
        """Enviar mensaje a través del message bus"""
        if not self.message_bus:
            self.logger.warning("Message bus no disponible, mensaje perdido")
            return
        
        message.from_agent = self.agent_id
        await self.message_bus.publish(message)
        self.logger.debug(f"📤 Mensaje enviado a {message.to_agent}: {message.task_type}")
    
    def create_task_message(
        self,
        to_agent: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        deadline: Optional[datetime] = None
    ) -> AgentMessage:
        """Helper para crear mensajes de tarea"""
        return AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            msg_type=MessageType.TASK,
            task_type=task_type,
            priority=priority,
            payload=payload,
            deadline=deadline
        )
    
    def create_result_message(
        self,
        to_agent: str,
        original_task: str,
        result: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> AgentMessage:
        """Helper para crear mensajes de resultado"""
        return AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            msg_type=MessageType.RESULT,
            task_type=f"RESULT_{original_task}",
            payload=result,
            correlation_id=correlation_id
        )
    
    def create_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "WARNING",
        payload: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Crear alerta para otros agentes"""
        return AgentMessage(
            from_agent=self.agent_id,
            to_agent="CEO",
            msg_type=MessageType.ALERT,
            task_type=alert_type,
            priority=TaskPriority.CRITICAL if severity == "CRITICAL" else TaskPriority.HIGH,
            payload={"alert_message": message, "severity": severity, **(payload or {})}
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES Y HELPERS
    # ═══════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado completo del agente para reporting"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "state": self.state.value,
            "state_reason": self.state_reason,
            "uptime_seconds": uptime,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "messages_processed": self.processed_messages,
            "errors_count": self.errors_count,
            "tasks_active": len(self.tasks_in_progress),
            "queue_size": len(self.message_queue)
        }
    
    async def wait_for_completion(self, task_id: str, timeout: float = 300) -> bool:
        """Esperar a que una tarea específica se complete"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if task_id not in self.tasks_in_progress:
                return True
            await asyncio.sleep(1)
        
        self.logger.warning(f"Timeout esperando tarea {task_id}")
        return False
    
    def add_task(self, task_id: str, message: AgentMessage):
        """Agregar tarea en progreso"""
        self.tasks_in_progress[task_id] = message
        self.set_state(AgentState.PROCESSING, f"Procesando: {task_id}")
    
    def complete_task(self, task_id: str):
        """Marcar tarea como completada"""
        if task_id in self.tasks_in_progress:
            del self.tasks_in_progress[task_id]
        
        if not self.tasks_in_progress:
            self.set_state(AgentState.IDLE, "Sin tareas pendientes")
    
    # ═══════════════════════════════════════════════════════════════
    # VALIDACIÓN Y ERROR HANDLING
    # ═══════════════════════════════════════════════════════════════
    
    async def safe_execute(self, coro, fallback_value=None):
        """Ejecutar coroutine con manejo de errores"""
        try:
            return await coro
        except Exception as e:
            self.logger.error(f"Error en ejecución segura: {e}")
            self.errors_count += 1
            return fallback_value
    
    def validate_payload(self, message: AgentMessage, required_fields: List[str]) -> bool:
        """Validar que el payload tenga los campos requeridos"""
        missing = [f for f in required_fields if f not in message.payload]
        if missing:
            self.logger.warning(f"Payload incompleto. Faltan: {missing}")
            return False
        return True
    
    # ═══════════════════════════════════════════════════════════════
    # REPRESENTACIÓN
    # ═══════════════════════════════════════════════════════════════
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.agent_id}, state={self.state.value})>"
    
    def __str__(self) -> str:
        return f"""
╔═══════════════════════════════════════════════════╗
║ 🤖 {self.agent_name:<45} ║
╠═══════════════════════════════════════════════════╣
║ ID:        {self.agent_id:<45} ║
║ Estado:    {self.state.value:<45} ║
║ Uptime:    {self.get_status()['uptime_seconds']:.0f}s{'':<39} ║
║ Mensajes:  {self.processed_messages:<45} ║
║ Errores:   {self.errors_count:<45} ║
╚═══════════════════════════════════════════════════╝
"""
