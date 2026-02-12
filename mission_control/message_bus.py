"""
📡 MISSION CONTROL - Message Bus
=================================
Sistema de mensajería asíncrono para comunicación entre agentes.

Características:
- Colas de mensajes por agente
- Pub/Sub para broadcasts
- Prioridad de mensajes
- Confirmed delivery
- Timeouts y retries
- Dead letter queue

Author: OpenClaw Trading Corp
Version: 1.0.0
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
from collections import defaultdict
from pathlib import Path
import uuid

# Importar del proyecto
from agents.base_agent import AgentMessage, MessageType, TaskPriority

# ═══════════════════════════════════════════════════════════════════
# ENUMS Y ESTRUCTURAS
# ═══════════════════════════════════════════════════════════════════

class QueueType(Enum):
    """Tipos de cola"""
    FIFO = "fifo"
    PRIORITY = "priority"
    DEAD_LETTER = "dead_letter"

@dataclass
class Subscription:
    """Suscripción a un tipo de mensaje"""
    agent_id: str
    msg_types: Set[MessageType] = field(default_factory=set)
    task_types: Set[str] = field(default_factory=set)
    priority_threshold: int = 10
    
class MessageStats:
    """Estadísticas del message bus"""
    def __init__(self):
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_failed = 0
        self.messages_retried = 0
        self.dead_letter_count = 0
        self.avg_processing_time = 0.0
        self.by_agent: Dict[str, int] = defaultdict(int)
        self.by_type: Dict[str, int] = defaultdict(int)
        self.last_activity: datetime = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "messages_failed": self.messages_failed,
            "messages_retried": self.messages_retried,
            "dead_letter_count": self.dead_letter_count,
            "avg_processing_time": self.avg_processing_time,
            "by_agent": dict(self.by_agent),
            "by_type": dict(self.by_type),
            "last_activity": self.last_activity.isoformat()
        }

# ═══════════════════════════════════════════════════════════════════
# MESSAGE BUS PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

class MessageBus:
    """
    Sistema central de mensajería para OpenClaw Trading Corp.
    
    Maneja la comunicación entre todos los agentes del sistema.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("MessageBus")
        self.stats = MessageStats()
        
        # Registro de agentes
        self.agents: Dict[str, Any] = {}  # agent_id -> agent reference
        
        # Colas de mensajes por agente
        self.queues: Dict[str, List[AgentMessage]] = defaultdict(list)
        
        # Cola de prioridad (mensajes críticos)
        self.priority_queue: List[AgentMessage] = []
        
        # Dead letter queue
        self.dead_letter_queue: List[AgentMessage] = []
        
        # Suscripciones pub/sub
        self.subscriptions: Dict[str, Subscription] = {}
        
        # Suscripciones por tipo de mensaje
        self.subscribers_by_type: Dict[MessageType, Set[str]] = defaultdict(set)
        self.subscribers_by_task: Dict[str, Set[str]] = defaultdict(set)
        
        # Mensajes en flight (no entregados)
        self.in_flight: Dict[str, AgentMessage] = {}
        
        # Workers de entrega
        self.delivery_workers: List[asyncio.Task] = []
        self.running = False
        
        # Locks
        self.queue_lock = asyncio.Lock()
        self.sub_lock = asyncio.Lock()
        
        # Configuración
        self.max_queue_size = self.config.get("max_queue_size", 1000)
        self.delivery_timeout = self.config.get("delivery_timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        
        # Logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configurar logging"""
        log_path = Path("/Users/enderj/OpenClaw_Trading_Corp/logs/mission_control")
        log_path.mkdir(parents=True, exist_ok=True)
        
        log_file = log_path / "message_bus.log"
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | MessageBus | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    # ═══════════════════════════════════════════════════════════════
    # REGISTRO DE AGENTES
    # ═══════════════════════════════════════════════════════════════
    
    def register_agent(self, agent: Any) -> bool:
        """
        Registrar un agente en el message bus.
        
        Args:
            agent: Instancia del agente
            
        Returns:
            True si se registró exitosamente
        """
        agent_id = getattr(agent, 'agent_id', None)
        if not agent_id:
            self.logger.error("Agente sin agent_id no puede registrarse")
            return False
        
        if agent_id in self.agents:
            self.logger.warning(f"Agente {agent_id} ya registrado, actualizando")
        
        self.agents[agent_id] = agent
        self.queues[agent_id] = []
        
        self.logger.info(f"✅ Agente registrado: {agent_id}")
        self.logger.info(f"   Agentes activos: {len(self.agents)}")
        
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Desregistrar un agente"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            if agent_id in self.queues:
                del self.queues[agent_id]
            
            # Limpiar suscripciones
            for sub_key in list(self.subscriptions.keys()):
                if self.subscriptions[sub_key].agent_id == agent_id:
                    del self.subscriptions[sub_key]
            
            self.logger.info(f"❌ Agente desregistrado: {agent_id}")
            return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # PUBLICACIÓN DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def publish(self, message: AgentMessage) -> bool:
        """
        Publicar un mensaje en el sistema.
        
        Args:
            message: Mensaje a publicar
            
        Returns:
            True si se publicó exitosamente
        """
        self.stats.messages_sent += 1
        self.stats.by_agent[message.from_agent] += 1
        self.stats.by_type[message.task_type] += 1
        self.stats.last_activity = datetime.now()
        
        try:
            # Determinar destino
            if message.to_agent == "BROADCAST":
                return await self._broadcast(message)
            
            # Cola de prioridad
            if message.priority.value <= 2:
                return await self._publish_priority(message)
            
            # Mensaje directo o cola normal
            return await self._publish_normal(message)
            
        except Exception as e:
            self.logger.error(f"Error publicando mensaje: {e}")
            self.stats.messages_failed += 1
            await self._send_to_dead_letter(message, str(e))
            return False
    
    async def _publish_priority(self, message: AgentMessage) -> bool:
        """Publicar mensaje de alta prioridad"""
        async with self.queue_lock:
            self.priority_queue.append(message)
            self.priority_queue.sort(key=lambda m: (m.priority.value, m.timestamp))
        
        self.logger.debug(f"📨 Mensaje PRIORIDAD [{message.priority.name}] a {message.to_agent}")
        return True
    
    async def _publish_normal(self, message: AgentMessage) -> bool:
        """Publicar mensaje normal"""
        # Si el agente destino existe, encolar directamente
        if message.to_agent in self.agents:
            async with self.queue_lock:
                self.queues[message.to_agent].append(message)
            
            self.logger.debug(f"📨 Mensaje encolado para {message.to_agent}: {message.task_type}")
            
            # Intentar entrega inmediata si el agente está idle
            await self._try_deliver(message)
            
            return True
        
        # Si no existe, intentar pub/sub
        return await self._try_pubsub(message)
    
    async def _broadcast(self, message: AgentMessage) -> bool:
        """Broadcast a todos los agentes"""
        tasks = []
        for agent_id in self.agents:
            broadcast_msg = AgentMessage(
                from_agent=message.from_agent,
                to_agent=agent_id,
                msg_type=message.msg_type,
                task_type=message.task_type,
                priority=message.priority,
                payload=message.payload.copy(),
                metadata={**message.metadata, "is_broadcast": True}
            )
            tasks.append(self.publish(broadcast_msg))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info(f"📢 Broadcast enviado a {len(tasks)} agentes")
        return True
    
    async def _try_pubsub(self, message: AgentMessage) -> bool:
        """Intentar entrega por pub/sub"""
        delivered = False
        
        # Por tipo de mensaje
        for subscriber in self.subscribers_by_type.get(message.msg_type, set()):
            if subscriber in self.agents:
                await self._enqueue_for_agent(subscriber, message)
                delivered = True
        
        # Por tipo de tarea
        for subscriber in self.subscribers_by_task.get(message.task_type, set()):
            if subscriber in self.agents:
                await self._enqueue_for_agent(subscriber, message)
                delivered = True
        
        if not delivered and message.to_agent != "BROADCAST":
            self.logger.warning(f"⚠️ Mensaje sin destinatario: {message.to_agent}")
            await self._send_to_dead_letter(message, "No subscriber found")
            return False
        
        return delivered
    
    async def _enqueue_for_agent(self, agent_id: str, message: AgentMessage):
        """Encolar mensaje para un agente específico"""
        async with self.queue_lock:
            if len(self.queues[agent_id]) < self.max_queue_size:
                self.queues[agent_id].append(message)
            else:
                self.logger.warning(f"Cola llena para {agent_id}, mensaje descartado")
                await self._send_to_dead_letter(message, "Queue overflow")
    
    # ═══════════════════════════════════════════════════════════════
    # ENTREGA DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def _try_deliver(self, message: AgentMessage) -> bool:
        """Intentar entrega inmediata al agente"""
        agent = self.agents.get(message.to_agent)
        if not agent:
            return False
        
        # Solo entregar si el agente está idle o procesando
        if hasattr(agent, 'state') and str(agent.state) in ['IDLE', 'PROCESSING']:
            try:
                await agent.receive_message(message)
                self.stats.messages_received += 1
                return True
            except Exception as e:
                self.logger.error(f"Error en entrega inmediata: {e}")
                return False
        
        return False
    
    async def start_delivery_workers(self, num_workers: int = 3):
        """Iniciar workers de entrega de mensajes"""
        self.running = True
        
        for i in range(num_workers):
            task = asyncio.create_task(self._delivery_worker(i))
            self.delivery_workers.append(task)
        
        self.logger.info(f"🚀 {num_workers} delivery workers iniciados")
    
    async def _delivery_worker(self, worker_id: int):
        """Worker para entrega de mensajes"""
        self.logger.info(f"Delivery worker {worker_id} iniciado")
        
        while self.running:
            try:
                # Chequear mensajes de prioridad primero
                message = await self._get_next_message()
                
                if message:
                    await self._deliver_message(message)
                
                await asyncio.sleep(0.1)  # No saturar el CPU
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error en delivery worker {worker_id}: {e}")
                await asyncio.sleep(1)
        
        self.logger.info(f"Delivery worker {worker_id} detenido")
    
    async def _get_next_message(self) -> Optional[AgentMessage]:
        """Obtener siguiente mensaje a entregar"""
        async with self.queue_lock:
            # Prioridad primero
            if self.priority_queue:
                return self.priority_queue.pop(0)
            
            # Luego colas normales (round-robin)
            for agent_id in self.queues:
                if self.queues[agent_id]:
                    return self.queues[agent_id].pop(0)
            
            return None
    
    async def _deliver_message(self, message: AgentMessage) -> bool:
        """Entregar mensaje al agente destino"""
        agent = self.agents.get(message.to_agent)
        if not agent:
            self.logger.warning(f"Agente no encontrado: {message.to_agent}")
            await self._send_to_dead_letter(message, "Agent not found")
            return False
        
        try:
            # Marcar como in-flight
            self.in_flight[message.msg_id] = message
            
            # Entregar
            await agent.receive_message(message)
            
            # Remover de in-flight
            if message.msg_id in self.in_flight:
                del self.in_flight[message.msg_id]
            
            self.stats.messages_received += 1
            self.logger.debug(f"✅ Mensaje entregado a {message.to_agent}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error entregando mensaje: {e}")
            
            # Retry logic
            if message.metadata.get("retry_count", 0) < self.max_retries:
                await self._retry_message(message)
            else:
                await self._send_to_dead_letter(message, str(e))
            
            return False
    
    async def _retry_message(self, message: AgentMessage):
        """Reintentar mensaje fallido"""
        retry_count = message.metadata.get("retry_count", 0) + 1
        message.metadata["retry_count"] = retry_count
        self.stats.messages_retried += 1
        
        # Backoff exponencial
        delay = min(2 ** retry_count, 60)
        self.logger.warning(f"Reintentando mensaje en {delay}s (intento {retry_count})")
        
        await asyncio.sleep(delay)
        await self.publish(message)
    
    async def _send_to_dead_letter(self, message: AgentMessage, reason: str):
        """Enviar mensaje a dead letter queue"""
        message.metadata["dead_letter_reason"] = reason
        message.metadata["dead_letter_time"] = datetime.now().isoformat()
        
        self.dead_letter_queue.append(message)
        self.stats.dead_letter_count += 1
        
        self.logger.warning(f"📭 Mensaje a Dead Letter: {message.msg_id} | Razón: {reason}")
        
        # Limitar tamaño
        if len(self.dead_letter_queue) > 100:
            self.dead_letter_queue = self.dead_letter_queue[-100:]
    
    # ═══════════════════════════════════════════════════════════════
    # SUSCRIPCIONES PUB/SUB
    # ═══════════════════════════════════════════════════════════════
    
    def subscribe(
        self,
        agent_id: str,
        msg_types: Optional[List[MessageType]] = None,
        task_types: Optional[List[str]] = None,
        priority_threshold: int = 10
    ) -> Subscription:
        """
        Suscribir un agente a tipos de mensajes.
        
        Args:
            agent_id: ID del agente
            msg_types: Tipos de mensajes a suscribirse
            task_types: Tipos de tareas a suscribirse
            priority_threshold: Prioridad mínima para recibir
        """
        subscription = Subscription(
            agent_id=agent_id,
            msg_types=set(msg_types or []),
            task_types=set(task_types or []),
            priority_threshold=priority_threshold
        )
        
        self.subscriptions[agent_id] = subscription
        
        # Indexar por tipo
        for msg_type in subscription.msg_types:
            self.subscribers_by_type[msg_type].add(agent_id)
        
        for task_type in subscription.task_types:
            self.subscribers_by_task[task_type].add(agent_id)
        
        self.logger.info(f"📬 Agente {agent_id} suscrito: {len(subscription.msg_types)} tipos, {len(subscription.task_types)} tareas")
        
        return subscription
    
    def unsubscribe(self, agent_id: str) -> bool:
        """Desuscribir un agente"""
        if agent_id in self.subscriptions:
            sub = self.subscriptions[agent_id]
            
            # Limpiar índices
            for msg_type in sub.msg_types:
                self.subscribers_by_type[msg_type].discard(agent_id)
            
            for task_type in sub.task_types:
                self.subscribers_by_task[task_type].discard(agent_id)
            
            del self.subscriptions[agent_id]
            self.logger.info(f"📭 Agente {agent_id} desuscrito")
            return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # CONSULTAS DE ESTADO
    # ═══════════════════════════════════════════════════════════════
    
    def get_queue_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtener estado de colas"""
        if agent_id:
            return {
                "agent_id": agent_id,
                "queue_size": len(self.queues.get(agent_id, [])),
                "messages": [m.task_type for m in self.queues.get(agent_id, [])]
            }
        
        return {
            "total_agents": len(self.agents),
            "total_queued": sum(len(q) for q in self.queues.values()),
            "priority_queue_size": len(self.priority_queue),
            "dead_letter_size": len(self.dead_letter_queue),
            "in_flight": len(self.in_flight),
            "queues": {
                aid: len(q) for aid, q in self.queues.items()
            }
        }
    
    def get_agents_status(self) -> Dict[str, Any]:
        """Obtener estado de todos los agentes"""
        return {
            agent_id: agent.get_status() if hasattr(agent, 'get_status') else {"status": "unknown"}
            for agent_id, agent in self.agents.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del message bus"""
        return self.stats.to_dict()
    
    # ═══════════════════════════════════════════════════════════════
    # APAGADO
    # ═══════════════════════════════════════════════════════════════
    
    async def shutdown(self):
        """Apagar el message bus"""
        self.logger.info("🛑 Apagando Message Bus...")
        self.running = False
        
        # Cancelar workers
        for task in self.delivery_workers:
            task.cancel()
        
        await asyncio.gather(*self.delivery_workers, return_exceptions=True)
        
        # Limpiar colas
        self.queues.clear()
        self.priority_queue.clear()
        
        self.logger.info("✅ Message Bus detenido")
    
    # ═══════════════════════════════════════════════════════════════
    # REPRESENTACIÓN
    # ═══════════════════════════════════════════════════════════════
    
    def __repr__(self) -> str:
        return f"<MessageBus(agents={len(self.agents)}, queues={sum(len(q) for q in self.queues.values())})>"
