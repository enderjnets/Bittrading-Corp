# ═══════════════════════════════════════════════════════════════════
# WORKERS INTEGRATION - Bittrading Trading Corp
# ═══════════════════════════════════════════════════════════════════

"""
Módulo de integración con el proyecto legacy.

Este módulo mantiene 100% de compatibilidad con:
- coordinator.py (Flask API)
- strategy_miner.py (Genetic Algorithm)
- optimizer.py (Grid/Genetic/Bayesian)
- trading_bot.py (Trading)
- Todos los workers existentes

Y los integra transparentemente con el nuevo sistema de agentes.
"""

from .complete_coordinator_bridge import (
    CoordinatorClient,
    CoordinatorConfig,
    WorkerManagerAgent,
    WorkUnit,
    WorkerResult,
    WorkerStatus
)

from .dashboard_integration import (
    DashboardService,
    DashboardAgent,
    DashboardConfig,
    DashboardMetrics
)

from .strategy_miner_adapter import (
    StrategyMinerAgent,
    MinerConfig,
    Genome,
    PopulationManager
)

__all__ = [
    # Coordinator Bridge
    'CoordinatorClient',
    'CoordinatorConfig', 
    'WorkerManagerAgent',
    'WorkUnit',
    'WorkerResult',
    'WorkerStatus',
    
    # Dashboard
    'DashboardService',
    'DashboardAgent',
    'DashboardConfig',
    'DashboardMetrics',
    
    # Strategy Miner
    'StrategyMinerAgent',
    'MinerConfig',
    'Genome',
    'PopulationManager'
]
