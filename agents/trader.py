"""
🤖 TRADER AGENT - Execution Specialist
======================================
Ejecuta trades en exchanges con gestión de órdenes.

Responsabilidades:
- Ejecución de órdenes (market/limit)
- Gestión de fill rates
- Slippaje optimization
- Rebalancing automático
- Order types especializados
- Multi-exchange coordination

Author: Bittrading Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from agents.base_agent import (
    BaseAgent, AgentConfig, AgentMessage, AgentState, 
    MessageType, TaskPriority
)

# Trading libraries
import ccxt

# ═══════════════════════════════════════════════════════════════════
# ENUMS Y ESTRUCTURAS
# ═══════════════════════════════════════════════════════════════════

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING = "TRAILING"

class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"

@dataclass
class Order:
    """Orden de trading"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    fees: float = 0.0
    slippaje: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    cancel_at: Optional[datetime] = None
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Position:
    """Posición abierta"""
    symbol: str
    side: str  # LONG, SHORT
    size: float
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None

# ═══════════════════════════════════════════════════════════════════
# TRADER AGENT
# ═══════════════════════════════════════════════════════════════════

class TraderAgent(BaseAgent):
    """
    Trader Agent - Execution Specialist.
    
    Maneja toda la ejecución de trades en Coinbase y otros exchanges.
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        trader_config = AgentConfig(
            agent_id="TRADER",
            agent_name="Execution Specialist",
            agent_type="TRADER",
            log_level="INFO",
            cycle_interval=5,  # Checks frecuentes para fills
            custom_config=config or {}
        )
        
        super().__init__(trader_config, message_bus)
        
        # Conexiones a exchanges
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.exchange_ids: List[str] = ["coinbase"]
        
        # Órdenes y posiciones
        self.active_orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.order_history: List[Order] = []
        
        # Estado
        self.trading_active = False
        self.balance: Dict[str, float] = {}
        
        # Métricas
        self.orders_submitted = 0
        self.orders_filled = 0
        self.orders_failed = 0
        self.total_fees = 0.0
        self.avg_slippage = 0.0
        
        # Database
        from shared.database import get_database, Trade as DBTrade
        self.db = get_database()
        self.DBTrade = DBTrade
        
        self.logger.info("🤖 Trader Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Inicializar trader"""
        self.logger.info("🚀 Iniciando Trader Agent...")
        
        # Conectar a exchanges
        await self._connect_exchanges()
        
        # Suscribirse a mensajes
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                task_types=[
                    "EXECUTE_TRADE",
                    "PLACE_ORDER",
                    "CANCEL_ORDER",
                    "CLOSE_POSITION",
                    "CLOSE_POSITION_PARTIAL",
                    "GET_POSITIONS",
                    "GET_ORDERS",
                    "ACTIVATE_TRADING",
                    "DEACTIVATE_TRADING",
                    "UPDATE_POSITIONS",
                    "REBALANCE"
                ]
            )
        
        # Iniciar loop de monitoreo de órdenes
        asyncio.create_task(self._order_monitor_loop())
        
        self.logger.info("✅ Trader Agent listo")
    
    async def on_shutdown(self):
        """Shutdown del trader"""
        self.logger.info("🛑 Deteniendo Trader Agent...")
        
        # Cancelar órdenes pendientes
        for order_id in list(self.active_orders.keys()):
            await self.cancel_order(order_id)
        
        # Cerrar conexiones
        for name, exchange in self.exchanges.items():
            try:
                exchange.close()
            except:
                pass
        
        self.logger.info("✅ Trader Agent detenido")
    
    async def run_cycle(self):
        """Ciclo principal"""
        # Actualizar posiciones
        await self._update_positions()
        
        # Verificar stops/targets
        await self._check_exits()
        
        # Rebalancing si necesario
        # await self._check_rebalancing()
    
    # ═══════════════════════════════════════════════════════════════
    # CONEXIONES A EXCHANGES
    # ═══════════════════════════════════════════════════════════════
    
    async def _connect_exchanges(self):
        """Conectar a todos los exchanges configurados"""
        for exchange_id in self.exchange_ids:
            try:
                if exchange_id == "coinbase":
                    exchange = self._create_coinbase_connection()
                else:
                    exchange = self._create_exchange_connection(exchange_id)
                
                self.exchanges[exchange_id] = exchange
                
                # Verificar conexión
                await self._verify_connection(exchange, exchange_id)
                
                # Obtener balance inicial
                await self._update_balance(exchange_id)
                
            except Exception as e:
                self.logger.error(f"❌ Error conectando a {exchange_id}: {e}")
    
    def _create_coinbase_connection(self) -> ccxt.Exchange:
        """Crear conexión a Coinbase"""
        from dotenv import load_dotenv
        import os
        
        # Cargar API keys de environment o config
        api_key = os.getenv("COINBASE_API_KEY", "")
        api_secret = os.getenv("COINBASE_API_SECRET", "")
        passphrase = os.getenv("COINBASE_PASSPHRASE", "")
        
        return ccxt.coinbase({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'createMarketBuyOrderRequiresPrice': False,
                'defaultNetwork': 'ethereum',
            }
        })
    
    def _create_exchange_connection(self, exchange_id: str) -> ccxt.Exchange:
        """Crear conexión a otro exchange"""
        config = getattr(self, f"{exchange_id}_config", {})
        
        exchange_class = getattr(ccxt, exchange_id)
        return exchange_class({
            'apiKey': config.get('apiKey', ''),
            'secret': config.get('secret', ''),
            'enableRateLimit': True,
            'timeout': 30000
        })
    
    async def _verify_connection(self, exchange: ccxt.Exchange, exchange_id: str):
        """Verificar que la conexión funciona"""
        try:
            # Intentar fetch de ticker
            ticker = await self._safe_api_call(
                exchange.fetch_ticker, "BTC/USD"
            )
            if ticker:
                self.logger.info(f"✅ {exchange_id}: Conectado | BTC=${ticker['last']:,.2f}")
            else:
                self.logger.warning(f"⚠️ {exchange_id}: Sin datos de ticker")
        except Exception as e:
            self.logger.error(f"❌ {exchange_id}: Error de verificación: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # EJECUCIÓN DE TRADES
    # ═══════════════════════════════════════════════════════════════
    
    async def execute_trade(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        ⭐ EJECUTAR TRADE - Función principal
        
        Recibe solicitud de trade, valida con Risk Manager si es necesario,
        y ejecuta la orden.
        """
        symbol = trade_request.get("symbol", "BTC/USD")
        side = OrderSide.BUY if trade_request.get("side", "BUY") == "BUY" else OrderSide.SELL
        quantity = trade_request.get("quantity", 0)
        order_type = OrderType(trade_request.get("order_type", "MARKET"))
        price = trade_request.get("price")
        stop_loss = trade_request.get("stop_loss")
        take_profit = trade_request.get("take_profit")
        
        self.logger.info(f"📝 Ejecutando trade: {side.value} {quantity} {symbol}")
        
        # Verificar si trading está activo
        if not self.trading_active:
            return {"status": "REJECTED", "reason": "Trading no activo"}
        
        # Verificar balance
        if side == OrderSide.BUY:
            required_value = quantity * (price or 1)
            available = self.balance.get("USD", 0)
            if required_value > available:
                return {"status": "REJECTED", "reason": "Saldo insuficiente"}
        
        # Place order
        order = await self.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            validate_with_risk=False  # Ya validado por Risk Manager
        )
        
        return {
            "status": "SUBMITTED",
            "order_id": order.order_id,
            "symbol": symbol,
            "side": side.value,
            "quantity": quantity,
            "order_type": order_type.value
        }
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        validate_with_risk: bool = True
    ) -> Order:
        """
        ⭐ COLOCAR ORDEN - Crear y enviar orden al exchange
        """
        exchange_id = "coinbase"
        exchange = self.exchanges.get(exchange_id)
        
        if not exchange:
            raise Exception(f"No hay conexión con {exchange_id}")
        
        # Crear orden
        order_id = str(uuid.uuid4())
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_loss,
            client_order_id=f"oc_{order_id[:12]}",
            metadata={
                "exchange": exchange_id,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
        )
        
        # Preparar parámetros
        params = {}
        if stop_loss and take_profit:
            # Coinbase advanced trade orders
            params = {
                'stop': 'loss',
                'stop_price': str(stop_loss),
                'stop_direction': 'STOP_DOWN' if side == OrderSide.BUY else 'STOP_UP',
            }
        
        try:
            # Ejecutar según tipo de orden
            if order_type == OrderType.MARKET:
                if side == OrderSide.BUY:
                    response = await self._safe_api_call(
                        exchange.create_market_buy_order, symbol, quantity
                    )
                else:
                    response = await self._safe_api_call(
                        exchange.create_market_sell_order, symbol, quantity
                    )
            
            elif order_type == OrderType.LIMIT:
                response = await self._safe_api_call(
                    exchange.create_limit_buy_order if side == OrderSide.BUY else exchange.create_limit_sell_order,
                    symbol, quantity, price
                )
            
            elif order_type == OrderType.STOP:
                response = await self._safe_api_call(
                    exchange.create_order, symbol, 'market', 'buy' if side == OrderSide.BUY else 'sell', 
                    quantity, price, params
                )
            
            else:
                raise Exception(f"Tipo de orden no soportado: {order_type}")
            
            # Procesar respuesta
            order.client_order_id = response.get('id', order_id)
            order.status = OrderStatus.SUBMITTED
            
            self.active_orders[order.order_id] = order
            self.orders_submitted += 1
            
            self.logger.info(f"✅ Orden colocada: {order.client_order_id} | {side.value} {quantity} {symbol}")
            
            # Si es market, esperar fill
            if order_type == OrderType.MARKET:
                await self._wait_for_fill(order)
            
            return order
            
        except Exception as e:
            order.status = OrderStatus.FAILED
            order.metadata["error"] = str(e)
            self.orders_failed += 1
            
            self.logger.error(f"❌ Error colocando orden: {e}")
            
            return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar una orden"""
        if order_id not in self.active_orders:
            return False
        
        order = self.active_orders[order_id]
        exchange = self.exchanges.get(order.metadata.get("exchange", "coinbase"))
        
        if not exchange:
            return False
        
        try:
            await self._safe_api_call(
                exchange.cancel_order, order.client_order_id
            )
            
            order.status = OrderStatus.CANCELLED
            self.logger.info(f"❌ Orden cancelada: {order.client_order_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelando orden: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════
    # GESTIÓN DE POSICIONES
    # ═══════════════════════════════════════════════════════════════
    
    async def _update_positions(self):
        """Actualizar estado de posiciones"""
        for symbol, position in self.positions.items():
            try:
                # Obtener precio actual
                exchange = self.exchanges.get("coinbase")
                ticker = await self._safe_api_call(
                    exchange.fetch_ticker, symbol
                )
                
                if ticker:
                    current_price = ticker['last']
                    position.current_price = current_price
                    
                    # Calcular P&L
                    if position.side == "LONG":
                        position.unrealized_pnl = (current_price - position.entry_price) * position.size
                        position.unrealized_pnl_percent = (
                            (current_price - position.entry_price) / position.entry_price * 100
                        )
                    else:
                        position.unrealized_pnl = (position.entry_price - current_price) * position.size
                        position.unrealized_pnl_percent = (
                            (position.entry_price - current_price) / position.entry_price * 100
                        )
                    
                    # Notificar P&L
                    await self._notify_pnl_update(position)
                    
            except Exception as e:
                self.logger.warning(f"Error actualizando posición {symbol}: {e}")
    
    async def _check_exits(self):
        """Verificar stops y take profits"""
        for symbol, position in list(self.positions.items()):
            current_price = position.current_price
            
            # Check stop loss
            if position.stop_loss:
                if position.side == "LONG" and current_price <= position.stop_loss:
                    await self._close_position(symbol, "STOP_LOSS_HIT")
                elif position.side == "SHORT" and current_price >= position.stop_loss:
                    await self._close_position(symbol, "STOP_LOSS_HIT")
            
            # Check take profit
            if position.take_profit:
                if position.side == "LONG" and current_price >= position.take_profit:
                    await self._close_position(symbol, "TAKE_PROFIT_HIT")
                elif position.side == "SHORT" and current_price <= position.take_profit:
                    await self._close_position(symbol, "TAKE_PROFIT_HIT")
    
    async def _close_position(self, symbol: str, reason: str) -> bool:
        """Cerrar posición"""
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        
        # Cerrar posición
        side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
        
        try:
            order = await self.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=position.size
            )
            
            if order.status == OrderStatus.FILLED:
                # Registrar trade
                await self._log_trade(order, position, reason)
                
                # Remover posición
                del self.positions[symbol]
                
                # Notificar
                await self.send_message(self.create_task_message(
                    to_agent="CEO",
                    task_type="POSITION_CLOSED",
                    priority=TaskPriority.NORMAL,
                    payload={
                        "symbol": symbol,
                        "reason": reason,
                        "pnl": position.unrealized_pnl,
                        "pnl_percent": position.unrealized_pnl_percent
                    }
                ))
                
                return True
            
        except Exception as e:
            self.logger.error(f"Error cerrando posición {symbol}: {e}")
            return False
        
        return False
    
    async def _log_trade(self, order: Order, position: Position, reason: str):
        """Loggear trade en base de datos"""
        try:
            trade = self.DBTrade(
                trade_id=order.order_id,
                portfolio_id="default",
                strategy_id=position.metadata.get("strategy_id", "unknown"),
                symbol=order.symbol,
                exchange="coinbase",
                order_id=order.client_order_id,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
                price=position.entry_price,
                filled_price=order.average_price,
                filled_at=order.filled_at,
                status=order.status.value,
                pnl=position.unrealized_pnl,
                pnl_percent=position.unrealized_pnl_percent,
                fees=order.fees,
                slippaje=order.slippaje,
                reason=reason
            )
            await self.db.create(trade)
        except Exception as e:
            self.logger.warning(f"No se pudo loggear trade: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # MONITOREO DE ÓRDENES
    # ═══════════════════════════════════════════════════════════════
    
    async def _order_monitor_loop(self):
        """Loop de monitoreo de órdenes"""
        while self.state == AgentState.RUNNING:
            try:
                for order_id, order in list(self.active_orders.items()):
                    if order.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
                        await self._check_order_fill(order)
                
                await asyncio.sleep(2)  # Check cada 2 segundos
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error en order monitor: {e}")
                await asyncio.sleep(5)
    
    async def _check_order_fill(self, order: Order):
        """Verificar si una orden fue ejecutada"""
        exchange = self.exchanges.get(order.metadata.get("exchange", "coinbase"))
        
        if not exchange:
            return
        
        try:
            response = await self._safe_api_call(
                exchange.fetch_order, order.client_order_id, order.symbol
            )
            
            if response:
                status = response.get('status', '')
                
                if status == 'closed' or status == 'filled':
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = response.get('filled', order.quantity)
                    order.average_price = response.get('average', response.get('price'))
                    order.filled_at = datetime.now()
                    
                    # Calcular fees y slippage
                    order.fees = response.get('fee', {}).get('cost', 0)
                    
                    # Remover de activas
                    del self.active_orders[order.order_id]
                    self.order_history.append(order)
                    self.orders_filled += 1
                    
                    self.logger.info(f"✅ Orden llenada: {order.client_order_id} | @ ${order.average_price}")
                    
                    # Crear posición si es nueva entrada
                    if order.side == OrderSide.BUY:
                        await self._open_position(order)
                
                elif status == 'canceled':
                    order.status = OrderStatus.CANCELLED
                    del self.active_orders[order.order_id]
                    self.order_history.append(order)
                
        except Exception as e:
            self.logger.debug(f"Error checkeando orden {order.client_order_id}: {e}")
    
    async def _wait_for_fill(self, order: Order, timeout: float = 60.0):
        """Esperar a que una orden market sea llenada"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if order.status == OrderStatus.FILLED:
                return
            
            await asyncio.sleep(1)
        
        self.logger.warning(f"Timeout esperando fill para {order.order_id}")
    
    async def _open_position(self, order: Order):
        """Abrir nueva posición"""
        position = Position(
            symbol=order.symbol,
            side="LONG",
            size=order.filled_quantity,
            entry_price=order.average_price or order.price,
            current_price=order.average_price or order.price,
            entry_time=order.filled_at or datetime.now()
        )
        
        # Agregar stops del metadata
        if order.metadata.get("stop_loss"):
            position.stop_loss = order.metadata["stop_loss"]
        if order.metadata.get("take_profit"):
            position.take_profit = order.metadata["take_profit"]
        
        self.positions[order.symbol] = position
        
        self.logger.info(f"📊 Posición abierta: {order.symbol} | {position.side} {position.size} @ ${position.entry_price}")
    
    async def _notify_pnl_update(self, position: Position):
        """Notificar actualización de P&L"""
        await self.send_message(self.create_task_message(
            to_agent="RISK_MANAGER",
            task_type="UPDATE_POSITION",
            priority=TaskPriority.NORMAL,
            payload={
                "symbol": position.symbol,
                "pnl": position.unrealized_pnl,
                "pnl_percent": position.unrealized_pnl_percent
            }
        ))
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes entrantes"""
        
        if message.task_type == "EXECUTE_TRADE":
            return await self._handle_execute_trade(message)
        
        elif message.task_type == "PLACE_ORDER":
            return await self._handle_place_order(message)
        
        elif message.task_type == "CANCEL_ORDER":
            return await self._handle_cancel_order(message)
        
        elif message.task_type == "CLOSE_POSITION":
            return await self._handle_close_position(message)
        
        elif message.task_type == "CLOSE_POSITION_PARTIAL":
            return await self._handle_close_partial(message)
        
        elif message.task_type == "GET_POSITIONS":
            return self._handle_get_positions(message)
        
        elif message.task_type == "GET_ORDERS":
            return self._handle_get_orders(message)
        
        elif message.task_type == "ACTIVATE_TRADING":
            return await self._handle_activate_trading(message)
        
        elif message.task_type == "DEACTIVATE_TRADING":
            return await self._handle_deactivate_trading(message)
        
        elif message.task_type == "UPDATE_POSITIONS":
            return await self._handle_update_positions(message)
        
        return None
    
    async def _handle_execute_trade(self, message: AgentMessage) -> AgentMessage:
        """Ejecutar trade"""
        result = await self.execute_trade(message.payload)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result=result
        )
    
    async def _handle_place_order(self, message: AgentMessage) -> AgentMessage:
        """Colocar orden"""
        payload = message.payload
        
        order = await self.place_order(
            symbol=payload["symbol"],
            side=OrderSide(payload["side"]),
            order_type=OrderType(payload.get("order_type", "MARKET")),
            quantity=payload["quantity"],
            price=payload.get("price"),
            stop_loss=payload.get("stop_loss"),
            take_profit=payload.get("take_profit")
        )
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "order_id": order.order_id,
                "status": order.status.value,
                "client_order_id": order.client_order_id
            }
        )
    
    async def _handle_cancel_order(self, message: AgentMessage) -> AgentMessage:
        """Cancelar orden"""
        order_ids = message.payload.get("order_ids", [])
        cancelled = []
        
        for order_id in order_ids:
            success = await self.cancel_order(order_id)
            if success:
                cancelled.append(order_id)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"cancelled": cancelled}
        )
    
    async def _handle_close_position(self, message: AgentMessage) -> AgentMessage:
        """Cerrar posición"""
        symbol = message.payload.get("symbol")
        reason = message.payload.get("reason", "MANUAL")
        
        success = await self._close_position(symbol, reason)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "symbol": symbol,
                "closed": success,
                "reason": reason
            }
        )
    
    async def _handle_close_partial(self, message: AgentMessage) -> AgentMessage:
        """Cerrar parcialmente"""
        symbol = message.payload.get("symbol")
        percentage = message.payload.get("percentage", 50)
        
        if symbol in self.positions:
            position = self.positions[symbol]
            close_qty = position.size * (percentage / 100)
            
            side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
            
            await self.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=close_qty
            )
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"symbol": symbol, "percentage_closed": percentage}
        )
    
    def _handle_get_positions(self, message: AgentMessage) -> AgentMessage:
        """Obtener posiciones actuales"""
        positions = {
            symbol: {
                "symbol": pos.symbol,
                "side": pos.side,
                "size": pos.size,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_percent": pos.unrealized_pnl_percent,
                "stop_loss": pos.stop_loss,
                "take_profit": pos.take_profit
            }
            for symbol, pos in self.positions.items()
        }
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "positions": positions,
                "count": len(positions),
                "total_unrealized_pnl": sum(p.unrealized_pnl for p in self.positions.values())
            }
        )
    
    def _handle_get_orders(self, message: AgentMessage) -> AgentMessage:
        """Obtener órdenes activas"""
        orders = {
            oid: {
                "order_id": oid,
                "symbol": o.symbol,
                "side": o.side.value,
                "status": o.status.value,
                "quantity": o.quantity,
                "filled": o.filled_quantity
            }
            for oid, o in self.active_orders.items()
        }
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"orders": orders, "count": len(orders)}
        )
    
    async def _handle_activate_trading(self, message: AgentMessage) -> AgentMessage:
        """Activar trading"""
        self.trading_active = True
        self.logger.info("✅ Trading activado")
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"trading_active": True}
        )
    
    async def _handle_deactivate_trading(self, message: AgentMessage) -> AgentMessage:
        """Desactivar trading"""
        self.trading_active = False
        self.logger.info("🛑 Trading desactivado")
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"trading_active": False}
        )
    
    async def _handle_update_positions(self, message: AgentMessage) -> AgentMessage:
        """Actualizar posiciones manualmente"""
        await self._update_positions()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"updated": True}
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    async def _safe_api_call(self, func, *args, **kwargs):
        """Llamada segura a API"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        except Exception as e:
            self.logger.warning(f"API call failed: {e}")
            return None
    
    async def _update_balance(self, exchange_id: str):
        """Obtener balance del exchange"""
        exchange = self.exchanges.get(exchange_id)
        if not exchange:
            return
        
        try:
            balance = await self._safe_api_call(exchange.fetch_balance)
            if balance:
                self.balance = {
                    asset: info['total'] 
                    for asset, info in balance.get('total', {}).items() 
                    if info > 0
                }
        except Exception as e:
            self.logger.warning(f"Error actualizando balance: {e}")
    
    def get_trader_status(self) -> Dict[str, Any]:
        """Obtener estado del trader"""
        total_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        
        return {
            "trading_active": self.trading_active,
            "positions_count": len(self.positions),
            "active_orders_count": len(self.active_orders),
            "total_unrealized_pnl": round(total_pnl, 2),
            "orders_submitted": self.orders_submitted,
            "orders_filled": self.orders_filled,
            "orders_failed": self.orders_failed,
            "fill_rate": round(
                self.orders_filled / max(1, self.orders_submitted) * 100, 2
            ),
            "total_fees": round(self.total_fees, 4),
            "balance": self.balance,
            "connected_exchanges": list(self.exchanges.keys())
        }
    
    def __repr__(self) -> str:
        status = self.get_trader_status()
        return f"<Trader(active={status['trading_active']}, positions={status['positions_count']}, fill_rate={status['fill_rate']}%)>"
