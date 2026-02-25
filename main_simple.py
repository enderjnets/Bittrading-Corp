"""
🚀 BITTRADING CORP - SIMPLIFIED CONTINUOUS TRADING
==================================================
Sistema de trading continuo simplificado y funcional

Author: Bittrading Trading Corp
Version: 5.0.0 - Simplified & Working
"""

import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, field

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
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("BITTRADING")

# ═══════════════════════════════════════════════════════════════════
# PAPER TRADING
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Position:
    """Posición de trading"""
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float = 0.0
    pnl: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class PaperTradingEngine:
    """Motor de paper trading"""
    
    def __init__(self, initial_balance: float = 500.0):
        self.balance = initial_balance
        self.initial = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trades: List[Dict] = []
        self.logger = logging.getLogger("PaperEngine")
        
    async def update_prices(self):
        """Actualizar precios"""
        for symbol, pos in self.positions.items():
            # Simular movimiento
            change = random.uniform(-0.05, 0.05)
            pos.current_price = pos.entry_price * (1 + change)
            pos.pnl = (pos.current_price - pos.entry_price) * pos.size * (1 if pos.side == "LONG" else -1)
    
    async def open_position(self, symbol: str, side: str, size: float, price: float) -> bool:
        """Abrir posición"""
        if size > self.balance:
            return False
        
        self.balance -= size
        self.positions[symbol] = Position(symbol, side, size, price, price)
        self.logger.info(f"✅ Opened: {symbol} {side} ${size:.2f} @ {price:.2f}")
        return True
    
    async def close_position(self, symbol: str) -> float:
        """Cerrar posición"""
        if symbol not in self.positions:
            return 0
        
        pos = self.positions[symbol]
        self.balance += pos.size + pos.pnl
        
        self.trades.append({
            "symbol": symbol, "pnl": pos.pnl,
            "timestamp": datetime.now().isoformat()
        })
        
        del self.positions[symbol]
        self.logger.info(f"✅ Closed: {symbol} P&L ${pos.pnl:+.2f}")
        return pos.pnl
    
    def get_value(self) -> float:
        """Valor total del portfolio"""
        return self.balance + sum(p.size + p.pnl for p in self.positions.values())
    
    def get_stats(self) -> Dict:
        """Estadísticas"""
        value = self.get_value()
        pnl = value - self.initial
        wins = sum(1 for t in self.trades if t["pnl"] > 0)
        
        return {
            "balance": self.balance,
            "value": value,
            "pnl": pnl,
            "pnl_pct": (pnl / self.initial) * 100,
            "positions": len(self.positions),
            "trades": len(self.trades),
            "wins": wins,
            "win_rate": (wins / len(self.trades) * 100) if self.trades else 0
        }

# ═══════════════════════════════════════════════════════════════════
# TRADING SYSTEM
# ═══════════════════════════════════════════════════════════════════

class TradingSystem:
    """Sistema de trading"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.engine = PaperTradingEngine(500.0)
        self.running = False
        self.cycles = 0
        self.symbols = {
            "BTC/USD": 95000,
            "ETH/USD": 2800,
            "SOL/USD": 180
        }
        
    async def initialize(self):
        """Inicializar"""
        self.logger.info("="*70)
        self.logger.info("🚀 BITTRADING CORP - TRADING SYSTEM v5.0")
        self.logger.info("="*70)
        self.logger.info(f"💰 Balance inicial: ${self.engine.initial:.2f}")
        self.logger.info(f"📊 Modo: Paper Trading")
        self.logger.info(f"🎯 Mercados: {list(self.symbols.keys())}")
        self.logger.info("="*70)
        
    async def run_cycle(self):
        """Ejecutar ciclo"""
        self.cycles += 1
        
        self.logger.info(f"─"*70)
        self.logger.info(f"📊 Ciclo #{self.cycles} | {datetime.now().strftime('%H:%M:%S')}")
        self.logger.info(f"─"*70)
        
        # Update prices
        await self.engine.update_prices()
        
        # Stats
        stats = self.engine.get_stats()
        emoji = "🟢" if stats['pnl'] >= 0 else "🔴"
        
        self.logger.info(f"💰 Portfolio: ${stats['value']:.2f}")
        self.logger.info(f"   {emoji} P&L: ${stats['pnl']:+.2f} ({stats['pnl_pct']:+.1f}%)")
        self.logger.info(f"   Posiciones: {stats['positions']} | Trades: {stats['trades']}")
        
        # Show positions
        if self.engine.positions:
            self.logger.info("📌 Posiciones:")
            for sym, pos in self.engine.positions.items():
                e = "🟢" if pos.pnl >= 0 else "🔴"
                self.logger.info(f"   {e} {sym}: ${pos.pnl:+.2f}")
        
        # Demo: Open position every 10 cycles
        if self.cycles % 10 == 0 and stats['positions'] < 3:
            symbol = random.choice(list(self.symbols.keys()))
            price = self.symbols[symbol]
            size = min(50, self.engine.balance * 0.1)
            side = random.choice(["LONG", "SHORT"])
            await self.engine.open_position(symbol, side, size, price)
        
        # Demo: Close position every 15 cycles
        if self.cycles % 15 == 0 and self.engine.positions:
            symbol = list(self.engine.positions.keys())[0]
            await self.engine.close_position(symbol)
    
    async def run(self):
        """Ejecutar sistema"""
        self.running = True
        
        try:
            while self.running:
                await self.run_cycle()
                await asyncio.sleep(60)
        except Exception as e:
            self.logger.error(f"❌ Error: {e}")
    
    async def shutdown(self):
        """Detener"""
        self.logger.info("="*70)
        self.logger.info("🛑 DETENIENDO SISTEMA")
        self.logger.info("="*70)
        
        self.running = False
        
        # Close all positions
        for symbol in list(self.engine.positions.keys()):
            await self.engine.close_position(symbol)
        
        # Final stats
        stats = self.engine.get_stats()
        self.logger.info("📊 Final:")
        self.logger.info(f"   Portfolio: ${stats['value']:.2f}")
        self.logger.info(f"   P&L: ${stats['pnl']:+.2f} ({stats['pnl_pct']:+.1f}%)")
        self.logger.info(f"   Trades: {stats['trades']} | Win Rate: {stats['win_rate']:.1f}%")
        self.logger.info("="*70)

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

import signal

async def main():
    system = TradingSystem()
    
    def handler(sig, frame):
        system.running = False
    
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    
    try:
        await system.initialize()
        await system.run()
    finally:
        await system.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
