"""
🚀 OPENCLAW TRADING CORP - MAIN ENTRY POINT
============================================
Inicializa y coordina todos los agentes del sistema.

Este es el punto de entrada principal que:
1. Inicializa el Message Bus
2. Crea e inicializa todos los agentes
3. Inicia el ciclo principal de cada agente
4. Maneja shutdown graceful

Author: OpenClaw Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
import sys
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LOGGING
# ═══════════════════════════════════════════════════════════════════

def setup_logging():
    """Configurar logging del sistema"""
    log_path = Path("/Users/enderj/OpenClaw_Trading_Corp/logs")
    log_path.mkdir(parents=True, exist_ok=True)
    
    log_file = log_path / f"system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reducir verbosidad de algunas librerías
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    return logging.getLogger("MAIN")


# ═══════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL DEL SISTEMA
# ═══════════════════════════════════════════════════════════════════

class OpenClawTradingCorp:
    """
    Sistema principal de OpenClaw Trading Corp.
    
    Maneja el ciclo de vida completo de todos los agentes.
    """
    
    def __init__(self):
        self.logger = setup_logging()
        self.logger.info("="*60)
        self.logger.info("🏢 INICIANDO OPENCLAW TRADING CORP")
        self.logger.info("="*60)
        
        # Componentes principales
        self.message_bus = None
        self.agents: Dict[str, Any] = {}
        self.running = False
        
        # Base de datos
        self.db = None
        
        # Tareas asíncronas
        self.main_tasks: List[asyncio.Task] = []
    
    async def initialize(self):
        """Inicializar todos los componentes"""
        try:
            # 1. Inicializar base de datos
            self.logger.info("📦 Inicializando base de datos...")
            from shared.database import get_database, DatabaseConfig
            
            db_config = DatabaseConfig(
                database_url="sqlite:///./trading_corp.db",
                async_url="sqlite+aiosqlite:///./trading_corp.db",
                pool_size=10,
                max_overflow=20,
                echo=False
            )
            
            self.db = get_database(db_config)
            self.db.initialize()
            self.logger.info("✅ Base de datos inicializada")
            
            # 2. Inicializar Message Bus
            self.logger.info("📡 Inicializando Message Bus...")
            from mission_control.message_bus import MessageBus
            
            self.message_bus = MessageBus({
                "max_queue_size": 1000,
                "delivery_timeout": 30,
                "max_retries": 3
            })
            
            # Iniciar delivery workers
            await self.message_bus.start_delivery_workers(num_workers=5)
            self.logger.info("✅ Message Bus inicializado")
            
            # 3. Crear agentes
            self.logger.info("🤖 Creando agentes...")
            await self._create_agents()
            
            # 4. Registrar agentes en Message Bus
            self.logger.info("📝 Registrando agentes...")
            for agent_id, agent in self.agents.items():
                self.message_bus.register_agent(agent)
            
            # 5. Iniciar agentes
            self.logger.info("🚀 Iniciando agentes...")
            await self._start_agents()
            
            self.logger.info("="*60)
            self.logger.info("✅ SISTEMA COMPLETAMENTE INICIALIZADO")
            self.logger.info("="*60)
            self.logger.info(f"Agentes activos: {len(self.agents)}")
            self.logger.info(f"Agentes: {', '.join(self.agents.keys())}")
            self.logger.info("="*60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error durante inicialización: {e}")
            return False
    
    async def _create_agents(self):
        """Crear instancias de todos los agentes"""
        
        # CEO - Chief Executive Orchestrator
        self.logger.info("   🧠 Creando CEO...")
        from agents.ceo import CEOAgent
        self.agents["CEO"] = CEOAgent(self.message_bus)
        
        # Market Scanner - Head of Market Intelligence
        self.logger.info("   📊 Creando Market Scanner...")
        from agents.market_scanner import MarketScannerAgent
        self.agents["MARKET_SCANNER"] = MarketScannerAgent(self.message_bus)
        
        # Strategy Generator - Chief Strategy Officer
        self.logger.info("   🧪 Creando Strategy Generator...")
        from agents.strategy_generator import StrategyGeneratorAgent
        self.agents["STRATEGY_GENERATOR"] = StrategyGeneratorAgent(self.message_bus)
        
        # Backtest Orchestrator - Head of Backtesting
        self.logger.info("   ⚡ Creando Backtest Orchestrator...")
        from agents.backtest_orchestrator import BacktestOrchestratorAgent
        self.agents["BACKTEST_ORCHESTRATOR"] = BacktestOrchestratorAgent(self.message_bus)
        
        # Risk Manager - Chief Risk Officer (CRÍTICO)
        self.logger.info("   💰 Creando Risk Manager (PODER DE VETO)...")
        from agents.risk_manager import RiskManagerAgent
        self.agents["RISK_MANAGER"] = RiskManagerAgent(self.message_bus)
        
        # Trader - Execution Specialist
        self.logger.info("   🤖 Creando Trader...")
        from agents.trader import TraderAgent
        self.agents["TRADER"] = TraderAgent(self.message_bus)
        
        # Agentes adicionales (placeholders para futura implementación)
        self.logger.info("   📈 Creando Analyst...")
        from agents.analyst import AnalystAgent
        self.agents["ANALYST"] = AnalystAgent(self.message_bus)
        
        self.logger.info("   🎯 Creando Strategy Selector...")
        from agents.strategy_selector import StrategySelectorAgent
        self.agents["STRATEGY_SELECTOR"] = StrategySelectorAgent(self.message_bus)
        
        self.logger.info("   🔧 Creando Worker Manager...")
        from agents.worker_manager import WorkerManagerAgent
        self.agents["WORKER_MANAGER"] = WorkerManagerAgent(self.message_bus)
        
        self.logger.info("   📋 Creando Task Manager...")
        from agents.task_manager import TaskManagerAgent
        self.agents["TASK_MANAGER"] = TaskManagerAgent(self.message_bus)
    
    async def _start_agents(self):
        """Iniciar todos los agentes"""
        for agent_id, agent in self.agents.items():
            try:
                task = asyncio.create_task(agent.start(), name=f"agent_{agent_id}")
                self.main_tasks.append(task)
                self.logger.info(f"   ✅ {agent_id} iniciado")
            except Exception as e:
                self.logger.error(f"   ❌ Error iniciando {agent_id}: {e}")
    
    async def run(self):
        """Ejecutar el sistema principal"""
        self.running = True
        
        # Esperar a que todos los agentes estén listos
        await asyncio.sleep(5)
        
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 ESTADO DEL SISTEMA")
        self.logger.info("="*60)
        
        for agent_id, agent in self.agents.items():
            status = agent.get_status()
            self.logger.info(f"  {agent_id}: {status['state']}")
        
        self.logger.info("="*60)
        self.logger.info("💡 SISTEMA OPERATIVO - Presiona Ctrl+C para detener")
        self.logger.info("="*60 + "\n")
        
        # Mantener el sistema ejecutándose
        try:
            while self.running:
                await asyncio.sleep(10)
                
                # Mostrar métricas cada minuto
                if int(datetime.now().strftime("%S")) < 15:
                    await self._show_metrics()
                    
        except asyncio.CancelledError:
            self.logger.info("Loop principal cancelado")
    
    async def _show_metrics(self):
        """Mostrar métricas del sistema"""
        try:
            ceo = self.agents.get("CEO")
            if ceo:
                dashboard = ceo.get_ceo_dashboard()
                self.logger.info(f"📊 CEO Dashboard: {dashboard}")
        except Exception:
            pass
    
    async def shutdown(self):
        """Apagado graceful del sistema"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🛑 CERRANDO OPENCLAW TRADING CORP")
        self.logger.info("="*60)
        
        self.running = False
        
        # 1. Desactivar trading primero
        trader = self.agents.get("TRADER")
        if trader:
            await trader.shutdown()
        
        # 2. Apagar agentes en orden inverso
        shutdown_order = [
            "RISK_MANAGER",
            "TRADER",
            "BACKTEST_ORCHESTRATOR",
            "STRATEGY_GENERATOR",
            "MARKET_SCANNER",
            "ANALYST",
            "STRATEGY_SELECTOR",
            "WORKER_MANAGER",
            "TASK_MANAGER",
            "CEO"
        ]
        
        for agent_id in shutdown_order:
            if agent_id in self.agents:
                try:
                    agent = self.agents[agent_id]
                    await agent.shutdown()
                    self.logger.info(f"   ✅ {agent_id} detenido")
                except Exception as e:
                    self.logger.error(f"   ❌ Error deteniendo {agent_id}: {e}")
        
        # 3. Cerrar Message Bus
        if self.message_bus:
            await self.message_bus.shutdown()
        
        # 4. Cerrar base de datos
        if self.db:
            await self.db.close()
        
        # 5. Cancelar tareas pendientes
        for task in self.main_tasks:
            task.cancel()
        
        await asyncio.gather(*self.main_tasks, return_exceptions=True)
        
        self.logger.info("="*60)
        self.logger.info("✅ SISTEMA CERRADO CORRECTAMENTE")
        self.logger.info("="*60)


# ═══════════════════════════════════════════════════════════════════
# AGENTES PLACEHOLDER (Para completar la implementación)
# ═══════════════════════════════════════════════════════════════════

class AnalystAgent:
    """Placeholder para Analyst Agent"""
    def __init__(self, message_bus=None):
        self.agent_id = "ANALYST"
        self.agent_name = "Senior Market Analyst"
        self.state = "INITIALIZING"
        self.message_bus = message_bus
        
    async def start(self):
        from agents.base_agent import AgentState
        self.state = AgentState.RUNNING.value
        while True:
            await asyncio.sleep(60)
    
    def shutdown(self):
        pass
    
    def get_status(self):
        return {"agent_id": self.agent_id, "state": self.state}


class StrategySelectorAgent:
    """Placeholder para Strategy Selector Agent"""
    def __init__(self, message_bus=None):
        self.agent_id = "STRATEGY_SELECTOR"
        self.agent_name = "Chief Investment Officer"
        self.state = "INITIALIZING"
        self.message_bus = message_bus
        
    async def start(self):
        from agents.base_agent import AgentState
        self.state = AgentState.RUNNING.value
        while True:
            await asyncio.sleep(60)
    
    def shutdown(self):
        pass
    
    def get_status(self):
        return {"agent_id": self.agent_id, "state": self.state}


class WorkerManagerAgent:
    """Placeholder para Worker Manager Agent"""
    def __init__(self, message_bus=None):
        self.agent_id = "WORKER_MANAGER"
        self.agent_name = "Infrastructure Manager"
        self.state = "INITIALIZING"
        self.message_bus = message_bus
        
    async def start(self):
        from agents.base_agent import AgentState
        self.state = AgentState.RUNNING.value
        while True:
            await asyncio.sleep(60)
    
    def shutdown(self):
        pass
    
    def get_status(self):
        return {"agent_id": self.agent_id, "state": self.state}


class TaskManagerAgent:
    """Placeholder para Task Manager Agent"""
    def __init__(self, message_bus=None):
        self.agent_id = "TASK_MANAGER"
        self.agent_name = "Project Manager"
        self.state = "INITIALIZING"
        self.message_bus = message_bus
        
    async def start(self):
        from agents.base_agent import AgentState
        self.state = AgentState.RUNNING.value
        while True:
            await asyncio.sleep(60)
    
    def shutdown(self):
        pass
    
    def get_status(self):
        return {"agent_id": self.agent_id, "state": self.state}


# ═══════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

async def main():
    """Función principal"""
    system = OpenClawTradingCorp()
    
    # Configurar handlers de señales
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        print("\n🛑 Señal de interrupción recibida...")
        asyncio.create_task(system.shutdown())
    
    # Registrar handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Inicializar y ejecutar
    success = await system.initialize()
    
    if success:
        await system.run()
    else:
        print("❌ Error inicializando el sistema. Saliendo...")
        await system.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Hasta luego!")
    except Exception as e:
        print(f"\n💥 Error fatal: {e}")
        sys.exit(1)
