"""
🗄️ SHARED - Base de Datos Centralizada
========================================
Modelos de datos y conexión a base de datos para Bittrading Trading Corp.

Usa SQLAlchemy con soporte para SQLite (desarrollo) y PostgreSQL (producción).

Author: Bittrading Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from pathlib import Path
import json

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, Text, JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    database_url: str = "sqlite:///./trading_corp.db"
    async_url: str = "sqlite+aiosqlite:///./trading_corp.db"
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        return cls(
            database_url=data.get("database_url", cls.database_url),
            async_url=data.get("async_url", cls.async_url),
            pool_size=data.get("pool_size", cls.pool_size),
            max_overflow=data.get("max_overflow", cls.max_overflow),
            echo=data.get("echo", False)
        )

# ═══════════════════════════════════════════════════════════════════
# MODELOS SQLALCHEMY
# ═══════════════════════════════════════════════════════════════════

Base = declarative_base()

class AgentState(Base):
    """Estado de los agentes"""
    __tablename__ = "agent_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(100), unique=True, nullable=False)
    agent_name = Column(String(200), nullable=False)
    agent_type = Column(String(100), nullable=False)
    state = Column(String(50), default="OFFLINE")
    state_reason = Column(Text, nullable=True)
    last_heartbeat = Column(DateTime, default=datetime.now)
    last_activity = Column(DateTime, default=datetime.now)
    messages_processed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class TaskQueue(Base):
    """Cola de tareas del sistema"""
    __tablename__ = "task_queue"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), unique=True, nullable=False)
    task_type = Column(String(100), nullable=False)
    from_agent = Column(String(100), nullable=False)
    to_agent = Column(String(100), nullable=False)
    priority = Column(Integer, default=5)
    status = Column(String(50), default="PENDING")
    payload = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    correlation_id = Column(String(100), nullable=True)
    deadline = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Strategy(Base):
    """Definición de estrategias"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(100), unique=True, nullable=False)
    strategy_name = Column(String(200), nullable=False)
    strategy_type = Column(String(100), nullable=False)  # momentum, mean_reversion, breakout, etc.
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True)  # Parámetros base
    rules = Column(JSON, nullable=True)  # Reglas de entrada/salida
    timeframes = Column(JSON, nullable=True)  #timeframes 적용
    markets = Column(JSON, nullable=True)  # Mercados objetivo
    status = Column(String(50), default="DRAFT")  # DRAFT, TESTING, ACTIVE, ARCHIVED
    created_by = Column(String(100), nullable=True)  # Agente creador
    generation_method = Column(String(100), nullable=True)  # manual, generated, evolved
    version = Column(Integer, default=1)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class BacktestResult(Base):
    """Resultados de backtests"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(100), unique=True, nullable=False)
    strategy_id = Column(String(100), ForeignKey("strategies.strategy_id"), nullable=False)
    worker_id = Column(String(100), nullable=True)
    symbol = Column(String(50), nullable=False)
    timeframe = Column(String(20), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Métricas de performance
    total_return = Column(Float, default=0.0)
    annual_return = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    expectancy = Column(Float, default=0.0)
    
    # Datos adicionales
    parameters = Column(JSON, nullable=True)
    equity_curve = Column(JSON, nullable=True)
    trades_list = Column(JSON, nullable=True)
    execution_time = Column(Float, default=0.0)
    status = Column(String(50), default="COMPLETED")
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Índices
    __table_args__ = (
        Index("idx_backtest_strategy", "strategy_id"),
        Index("idx_backtest_symbol", "symbol"),
        Index("idx_backtest_period", "start_date", "end_date"),
    )

class OptimizedParams(Base):
    """Parámetros optimizados"""
    __tablename__ = "optimized_params"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    param_id = Column(String(100), unique=True, nullable=False)
    strategy_id = Column(String(100), ForeignKey("strategies.strategy_id"), nullable=False)
    symbol = Column(String(50), nullable=False)
    timeframe = Column(String(20), nullable=False)
    
    # Parámetros optimizados
    parameters = Column(JSON, nullable=False)
    optimization_method = Column(String(100), nullable=True)  # grid, bayesian, genetic
    walk_forward_window = Column(Integer, nullable=True)
    validation_window = Column(Integer, nullable=True)
    
    # Métricas del optimizador
    in_sample_sharpe = Column(Float, default=0.0)
    out_sample_sharpe = Column(Float, default=0.0)
    robustness_score = Column(Float, default=0.0)
    
    status = Column(String(50), default="OPTIMIZED")  # OPTIMIZING, VALIDATING, READY, REJECTED
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.now)
    validated_at = Column(DateTime, nullable=True)

class ActivePortfolio(Base):
    """Portfolio activo de estrategias"""
    __tablename__ = "active_portfolio"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(String(100), unique=True, nullable=False)
    strategy_id = Column(String(100), ForeignKey("strategies.strategy_id"), nullable=False)
    param_id = Column(String(100), ForeignKey("optimized_params.param_id"), nullable=True)
    symbol = Column(String(50), nullable=False)
    allocation_percent = Column(Float, default=0.0)
    priority = Column(Integer, default=5)
    
    # Estado actual
    status = Column(String(50), default="ACTIVE")  # ACTIVE, PAUSED, STOPPED
    current_pnl = Column(Float, default=0.0)
    current_drawdown = Column(Float, default=0.0)
    trades_today = Column(Integer, default=0)
    last_trade_at = Column(DateTime, nullable=True)
    
    # Configuración de trading
    max_position_size = Column(Float, default=0.05)
    stop_loss = Column(Float, default=0.02)
    take_profit = Column(Float, default=0.06)
    trailing_stop = Column(Float, default=0.0)
    
    risk_score = Column(Float, default=0.5)
    activated_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Trade(Base):
    """Historial de trades ejecutados"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(100), unique=True, nullable=False)
    portfolio_id = Column(String(100), ForeignKey("active_portfolio.portfolio_id"), nullable=True)
    strategy_id = Column(String(100), nullable=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(50), nullable=False)
    
    # Orden
    order_id = Column(String(100), nullable=True)
    side = Column(String(10), nullable=False)  # BUY, SELL
    order_type = Column(String(20), nullable=False)  # MARKET, LIMIT, STOP, etc.
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    filled_price = Column(Float, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False)  # PENDING, FILLED, CANCELLED, FAILED
    
    # Resultado
    pnl = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    slippaje = Column(Float, default=0.0)
    
    # Contexto
    reason = Column(Text, nullable=True)
    signal_type = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index("idx_trade_symbol", "symbol"),
        Index("idx_trade_status", "status"),
        Index("idx_trade_created", "created_at"),
    )

class MarketData(Base):
    """Datos de mercado cacheados"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(50), nullable=False)
    timeframe = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # OHLCV
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    
    # Datos adicionales
    indicators = Column(JSON, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "timeframe", "timestamp"),
        Index("idx_market_symbol_time", "symbol", "timeframe", "timestamp"),
    )

class RiskLimits(Base):
    """Límites de riesgo configurados"""
    __tablename__ = "risk_limits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    limit_id = Column(String(100), unique=True, nullable=False)
    limit_name = Column(String(200), nullable=False)
    limit_type = Column(String(50), nullable=False)  # position, daily, weekly, global
    asset = Column(String(50), nullable=True)  # ALL para global
    value = Column(Float, nullable=False)
    unit = Column(String(20), default="PERCENT")  # PERCENT, USD, ABSOLUTE
    severity = Column(String(20), default="WARNING")  # WARNING, CRITICAL, HARD_STOP
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class AuditLog(Base):
    """Log de auditoría"""
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(100), unique=True, nullable=False)
    agent_id = Column(String(100), nullable=True)
    action = Column(String(200), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index("idx_audit_agent", "agent_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_time", "created_at"),
    )

# ═══════════════════════════════════════════════════════════════════
# CLASE DE CONEXIÓN A BASE DE DATOS
# ═══════════════════════════════════════════════════════════════════

class Database:
    """
    Manejador de conexión a base de datos.
    
    Soporta:
    - SQLite para desarrollo
    - PostgreSQL para producción (futuro)
    - Modo asíncrono para operaciones concurrentes
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None
        self.logger = logging.getLogger("Database")
        
        self._initialized = False
    
    def initialize(self):
        """Inicializar conexiones a base de datos"""
        if self._initialized:
            return
        
        try:
            # Motor síncrono
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                echo=self.config.echo,
                pool_pre_ping=True
            )
            
            # Motor asíncrono
            async_url = self.config.async_url
            self.async_engine = create_async_engine(
                async_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                echo=self.config.echo
            )
            
            # Session factories
            self.session_factory = sessionmaker(bind=self.engine)
            self.async_session_factory = async_sessionmaker(
                self.async_engine, 
                class_=AsyncSession, 
                expire_on_commit=False
            )
            
            # Crear tablas
            Base.metadata.create_all(self.engine)
            
            self._initialized = True
            self.logger.info("✅ Base de datos inicializada")
            
        except Exception as e:
            self.logger.error(f"Error inicializando base de datos: {e}")
            raise
    
    @asynccontextmanager
    async def async_session(self):
        """Context manager para sesiones asíncronas"""
        if not self.async_session_factory:
            raise RuntimeError("Base de datos no inicializada")
        
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    def session(self):
        """Obtener sesión síncrona"""
        if not self.session_factory:
            raise RuntimeError("Base de datos no inicializada")
        return self.session_factory()
    
    # ═══════════════════════════════════════════════════════════════
    # OPERACIONES GENÉRICAS
    # ═══════════════════════════════════════════════════════════════
    
    async def create(self, obj: Base) -> bool:
        """Crear un objeto en la base de datos"""
        async with self.async_session() as session:
            session.add(obj)
            return True
    
    async def get_by_id(self, model: Type[Base], id_value: Any) -> Optional[Base]:
        """Obtener por ID"""
        async with self.async_session() as session:
            return await session.get(model, id_value)
    
    async def get_by_field(self, model: Type[Base], field_name: str, value: Any) -> Optional[Base]:
        """Obtener por campo específico"""
        async with self.async_session() as session:
            query = f"SELECT * FROM {model.__tablename__} WHERE {field_name} = :value"
            result = await session.execute(query, {"value": value})
            return result.fetchone()
    
    async def update(self, model: Type[Base], id_value: Any, **kwargs) -> bool:
        """Actualizar un objeto"""
        async with self.async_session() as session:
            obj = await session.get(model, id_value)
            if obj:
                for key, value in kwargs.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                return True
            return False
    
    async def delete(self, model: Type[Base], id_value: Any) -> bool:
        """Eliminar un objeto"""
        async with self.async_session() as session:
            obj = await session.get(model, id_value)
            if obj:
                await session.delete(obj)
                return True
            return False
    
    async def query(self, model: Type[Base], **filters) -> List[Base]:
        """Consultar con filtros"""
        async with self.async_session() as session:
            query = session.query(model)
            for field, value in filters.items():
                query = query.filter(getattr(model, field) == value)
            return query.all()
    
    # ═══════════════════════════════════════════════════════════════
    # OPERACIONES ESPECÍFICAS
    # ═══════════════════════════════════════════════════════════════
    
    async def update_agent_state(self, agent_id: str, **kwargs):
        """Actualizar estado de un agente"""
        return await self.update(AgentState, agent_id, **kwargs)
    
    async def create_task(self, task: TaskQueue) -> bool:
        """Crear una tarea"""
        return await self.create(task)
    
    async def get_pending_tasks(self, agent_id: Optional[str] = None) -> List[TaskQueue]:
        """Obtener tareas pendientes"""
        async with self.async_session() as session:
            query = session.query(TaskQueue).filter(TaskQueue.status == "PENDING")
            if agent_id:
                query = query.filter(TaskQueue.to_agent == agent_id)
            query = query.order_by(TaskQueue.priority, TaskQueue.created_at)
            return query.all()
    
    async def create_strategy(self, strategy: Strategy) -> bool:
        """Crear una estrategia"""
        return await self.create(strategy)
    
    async def get_strategies(self, status: Optional[str] = None) -> List[Strategy]:
        """Obtener estrategias"""
        return await self.query(Strategy, **( {"status": status} if status else {} ))
    
    async def create_backtest_result(self, result: BacktestResult) -> bool:
        """Crear resultado de backtest"""
        return await self.create(result)
    
    async def get_best_backtests(
        self, 
        strategy_id: str, 
        symbol: str, 
        limit: int = 10
    ) -> List[BacktestResult]:
        """Obtener mejores backtests por estrategia y símbolo"""
        async with self.async_session() as session:
            query = session.query(BacktestResult).filter(
                BacktestResult.strategy_id == strategy_id,
                BacktestResult.symbol == symbol,
                BacktestResult.status == "COMPLETED"
            )
            query = query.order_by(BacktestResult.sharpe_ratio.desc())
            return query.limit(limit).all()
    
    async def log_trade(self, trade: Trade) -> bool:
        """Registrar un trade"""
        return await self.create(trade)
    
    async def log_audit(self, agent_id: str, action: str, **kwargs) -> bool:
        """Registrar en audit log"""
        import uuid
        audit = AuditLog(
            log_id=str(uuid.uuid4()),
            agent_id=agent_id,
            action=action,
            **kwargs
        )
        return await self.create(audit)
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def get_engine(self):
        """Obtener motor síncrono"""
        return self.engine
    
    async def close(self):
        """Cerrar conexiones"""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
        self.logger.info("✅ Conexiones cerradas")
    
    def __repr__(self) -> str:
        return f"<Database(url={self.config.database_url})>"


# ═══════════════════════════════════════════════════════════════════
# INSTANCIA GLOBAL
# ═══════════════════════════════════════════════════════════════════

# Instancia global de base de datos
_db_instance: Optional[Database] = None

def get_database(config: Optional[DatabaseConfig] = None) -> Database:
    """Obtener instancia global de base de datos"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(config)
    return _db_instance
