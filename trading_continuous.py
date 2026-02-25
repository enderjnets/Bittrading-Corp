"""
🚀 BITTRADING CORP - CONTINUOUS TRADING SYSTEM
==============================================
Sistema de trading continuo basado en evolved_version

Author: Bittrading Trading Corp
Version: 4.0.0 - Production Ready
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Importar del evolved_version
import sys
sys.path.insert(0, str(Path(__file__).parent))

from evolved_version import (
    BittradingConfig, AgentRegistry, TradingCoordinator
)

# ═══════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════

def setup_logging():
    """Configurar logging"""
    log_path = Path("/home/enderj/.openclaw/workspace/Bittrading-Corp/logs")
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "trading.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("BITTRADING_TRADING")

# ═══════════════════════════════════════════════════════════════════
# PAPER TRADING ENGINE
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PaperPosition:
    """Posición de paper trading"""
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    size: float
    entry_price: float
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class PaperTradingEngine:
    """Motor de paper trading"""
    
    def __init__(self, initial_balance: float = 500.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions: Dict[str, PaperPosition] = {}
        self.trades_history: List[Dict] = []
        self.logger = logging.getLogger("PaperTrading")
        
    async def update_prices(self):
        """Actualizar precios (simulado)"""
        # TODO: Conectar a API real
        for symbol, pos in self.positions.items():
            # Simular movimiento de precio pequeño
            import random
            change_pct = random.uniform(-0.02, 0.02)
            pos.current_price = pos.entry_price * (1 + change_pct)
            
            # Calcular P&L
            if pos.side == "LONG":
                pos.pnl = (pos.current_price - pos.entry_price) * pos.size
            else:
                pos.pnl = (pos.entry_price - pos.current_price) * pos.size
            
            pos.pnl_pct = (pos.pnl / (pos.size * pos.entry_price)) * 100
    
    async def open_position(self, symbol: str, side: str, size: float, price: float) -> bool:
        """Abrir posición"""
        if size > self.balance:
            self.logger.warning(f"❌ Insufficient balance: {size} > {self.balance}")
            return False
        
        self.balance -= size
        position = PaperPosition(
            symbol=symbol,
            side=side,
            size=size,
            entry_price=price,
            current_price=price
        )
        self.positions[symbol] = position
        
        self.logger.info(f"✅ Position opened: {symbol} {side} ${size:.2f} @ {price:.4f}")
        return True
    
    async def close_position(self, symbol: str) -> Optional[float]:
        """Cerrar posición"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        self.balance += pos.size + pos.pnl
        
        trade = {
            "symbol": symbol,
            "side": pos.side,
            "size": pos.size,
            "entry_price": pos.entry_price,
            "exit_price": pos.current_price,
            "pnl": pos.pnl,
            "pnl_pct": pos.pnl_pct,
            "timestamp": datetime.now().isoformat()
        }
        self.trades_history.append(trade)
        
        del self.positions[symbol]
        
        self.logger.info(f"✅ Position closed: {symbol} P&L: ${pos.pnl:+.2f} ({pos.pnl_pct:+.1f}%)")
        return pos.pnl
    
    def get_portfolio_value(self) -> float:
        """Obtener valor total del portfolio"""
        positions_value = sum(p.size + p.pnl for p in self.positions.values())
        return self.balance + positions_value
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas"""
        total_pnl = self.get_portfolio_value() - self.initial_balance
        winning = sum(1 for t in self.trades_history if t["pnl"] > 0)
        losing = sum(1 for t in self.trades_history if t["pnl"] <= 0)
        
        return {
            "balance": self.balance,
            "portfolio_value": self.get_portfolio_value(),
            "total_pnl": total_pnl,
            "pnl_pct": (total_pnl / self.initial_balance) * 100,
            "positions": len(self.positions),
            "trades": len(self.trades_history),
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": (winning / len(self.trades_history) * 100) if self.trades_history else 0
        }

# ═══════════════════════════════════════════════════════════════════
# TRADING SYSTEM CONTINUOUS
# ═══════════════════════════════════════════════════════════════════

class BittradingTradingSystem:
    """Sistema de trading continuo"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.config = BittradingConfig()
        self.registry = AgentRegistry(self.config)
        self.coordinator = TradingCoordinator(self.config, self.registry)
        self.paper_engine = PaperTradingEngine(initial_balance=500.0)
        self.running = False
        self.cycle_count = 0
        
    async def initialize(self):
        """Inicializar sistema"""
        self.logger.info("="*70)
        self.logger.info("🚀 BITTRADING CORP - TRADING SYSTEM")
        self.logger.info("="*70)
        self.logger.info(f"💰 Paper Trading: ${self.paper_engine.initial_balance:.2f}")
        self.logger.info(f"🤖 Agents: {len(self.registry.agents)}")
        self.logger.info("="*70)
        
    async def run_trading_cycle(self):
        """Ejecutar ciclo de trading"""
        self.cycle_count += 1
        
        self.logger.info(f"─"*70)
        self.logger.info(f"📊 Trading Cycle #{self.cycle_count}")
        self.logger.info(f"─"*70)
        
        # 1. Update prices
        await self.paper_engine.update_prices()
        
        # 2. Get portfolio status
        stats = self.paper_engine.get_stats()
        self.logger.info(f"💰 Portfolio: ${stats['portfolio_value']:.2f}")
        self.logger.info(f"   Balance: ${stats['balance']:.2f}")
        self.logger.info(f"   Positions: {stats['positions']}")
        self.logger.info(f"   P&L: ${stats['total_pnl']:+.2f} ({stats['pnl_pct']:+.1f}%)")
        
        # 3. Show positions if any
        if self.paper_engine.positions:
            self.logger.info("📌 Positions:")
            for symbol, pos in self.paper_engine.positions.items():
                emoji = "🟢" if pos.pnl >= 0 else "🔴"
                self.logger.info(f"   {emoji} {symbol}: ${pos.size:.2f} @ {pos.entry_price:.4f}")
                self.logger.info(f"      P&L: ${pos.pnl:+.2f} ({pos.pnl_pct:+.1f}%)")
        
        # 4. Example: Open a position every 10 cycles (demo)
        if self.cycle_count % 10 == 0 and stats['positions'] < 3:
            await self._demo_open_position()
        
        # 5. Example: Close a position every 15 cycles (demo)
        if self.cycle_count % 15 == 0 and self.paper_engine.positions:
            await self._demo_close_position()
        
    async def _demo_open_position(self):
        """Demo: Abrir posición aleatoria"""
        import random
        
        symbols = ["BTC/USD", "ETH/USD", "SOL/USD"]
        symbol = random.choice(symbols)
        
        # Precios aproximados
        prices = {
            "BTC/USD": 95000,
            "ETH/USD": 2800,
            "SOL/USD": 180
        }
        
        price = prices.get(symbol, 100)
        size = min(50, self.paper_engine.balance * 0.1)  # 10% del balance
        side = random.choice(["LONG", "SHORT"])
        
        await self.paper_engine.open_position(symbol, side, size, price)
    
    async def _demo_close_position(self):
        """Demo: Cerrar posición aleatoria"""
        if self.paper_engine.positions:
            symbol = list(self.paper_engine.positions.keys())[0]
            await self.paper_engine.close_position(symbol)
    
    async def run(self):
        """Ejecutar sistema continuo"""
        self.running = True
        
        try:
            while self.running:
                await self.run_trading_cycle()
                await asyncio.sleep(60)  # Ciclo cada 60 segundos
                
        except Exception as e:
            self.logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def shutdown(self):
        """Detener sistema"""
        self.logger.info("="*70)
        self.logger.info("🛑 DETENIENDO SISTEMA")
        self.logger.info("="*70)
        
        self.running = False
        
        # Cerrar todas las posiciones
        for symbol in list(self.paper_engine.positions.keys()):
            await self.paper_engine.close_position(symbol)
        
        # Estadísticas finales
        stats = self.paper_engine.get_stats()
        self.logger.info("📊 Estadísticas Finales:")
        self.logger.info(f"   Portfolio: ${stats['portfolio_value']:.2f}")
        self.logger.info(f"   P&L Total: ${stats['total_pnl']:+.2f} ({stats['pnl_pct']:+.1f}%)")
        self.logger.info(f"   Trades: {stats['trades']} (Win: {stats['winning_trades']}, Loss: {stats['losing_trades']})")
        self.logger.info(f"   Win Rate: {stats['win_rate']:.1f}%")
        self.logger.info("="*70)

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

import signal

async def main():
    """Punto de entrada principal"""
    system = BittradingTradingSystem()
    
    # Signal handler
    def signal_handler(sig, frame):
        print("\n⚠️  Shutdown requested...")
        system.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await system.initialize()
        await system.run()
    except Exception as e:
        system.logger.error(f"❌ Fatal error: {e}")
    finally:
        await system.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
