"""
🧪 STRATEGY MINER ADAPTER - Integra Strategy Miner Existente
=============================================================
Este módulo adapta el strategy_miner.py existente para funcionar
dentro del nuevo sistema de agentes.

 reutilizar:
- Genetic Algorithm del strategy_miner.py
- Todos los tipos de estrategias (RSI, SMA, EMA, etc.)
- Evaluación de poblaciones
- Evolución de genomas

Author: Bittrading Trading Corp
Version: 1.0.0
"""

import asyncio
import logging
import random
import copy
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from agents.base_agent import (
    BaseAgent, AgentConfig, AgentMessage, AgentState, 
    MessageType, TaskPriority
)


# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MinerConfig:
    """Configuración del Strategy Miner"""
    population_size: int = 100
    generations: int = 20
    mutation_rate: float = 0.2
    crossover_rate: float = 0.3
    elitism_count: int = 5
    force_local: bool = False
    use_ray: bool = True
    ray_address: str = "auto"


# ═══════════════════════════════════════════════════════════════════
# GENOME CLASS (Reutilizado de strategy_miner.py)
# ═══════════════════════════════════════════════════════════════════

class Genome:
    """
    Represents a trading strategy as a genome.
    Contains entry rules and parameters.
    """
    
    def __init__(self, data: Optional[Dict] = None):
        if data:
            self.data = data
        else:
            self.data = {
                "entry_rules": [],
                "params": {
                    "sl_pct": random.uniform(0.01, 0.05),
                    "tp_pct": random.uniform(0.02, 0.10)
                }
            }
    
    @property
    def entry_rules(self) -> List[Dict]:
        return self.data.get("entry_rules", [])
    
    @property
    def params(self) -> Dict:
        return self.data.get("params", {})
    
    def mutate(self, mutation_rate: float = 0.2) -> 'Genome':
        """Create mutated copy of genome"""
        mutated = copy.deepcopy(self.data)
        
        if random.random() < mutation_rate:
            # Mutate params
            key = random.choice(["sl_pct", "tp_pct"])
            change = random.uniform(0.8, 1.2)
            mutated["params"][key] *= change
        
        if random.random() < mutation_rate:
            # Mutate rules
            if mutated["entry_rules"]:
                idx = random.randint(0, len(mutated["entry_rules"]) - 1)
                mutated["entry_rules"][idx] = self._random_rule()
        
        return Genome(mutated)
    
    def crossover(self, other: 'Genome') -> 'Genome':
        """Crossover with another genome"""
        child_data = {
            "entry_rules": [],
            "params": {}
        }
        
        # Mix params
        child_data["params"]["sl_pct"] = (
            self.data["params"]["sl_pct"] + 
            other.data["params"]["sl_pct"]
        ) / 2
        child_data["params"]["tp_pct"] = (
            self.data["params"]["tp_pct"] + 
            other.data["params"]["tp_pct"]
        ) / 2
        
        # Mix rules
        rules1 = self.data["entry_rules"]
        rules2 = other.data["entry_rules"]
        
        split1 = len(rules1) // 2
        split2 = len(rules2) // 2
        
        child_data["entry_rules"] = rules1[:split1] + rules2[split2:]
        
        if not child_data["entry_rules"]:
            child_data["entry_rules"] = rules1 if rules1 else [self._random_rule()]
        
        return Genome(child_data)
    
    def _random_rule(self) -> Dict:
        """Generate random rule"""
        indicators = ["RSI", "SMA", "EMA", "VOLSMA"]
        operators = [">", "<"]
        periods = [10, 14, 20, 50, 100, 200]
        constants_rsi = [20, 25, 30, 35, 40, 60, 65, 70, 75, 80]
        
        ind = random.choice(indicators)
        period = random.choice(periods)
        op = random.choice(operators)
        
        left = {"indicator": ind, "period": period}
        
        if ind == "RSI":
            right = {"value": random.choice(constants_rsi)}
        elif ind in ["SMA", "EMA"]:
            left = {"field": "close"}
            right = {"indicator": ind, "period": period}
            if random.random() < 0.3:
                period2 = random.choice([p for p in periods if p != period])
                left = {"indicator": ind, "period": min(period, period2)}
                right = {"indicator": ind, "period": max(period, period2)}
        elif ind == "VOLSMA":
            left = {"field": "volume"}
            right = {"indicator": "VOLSMA", "period": period}
        
        return {"left": left, "op": op, "right": right}
    
    def to_dict(self) -> Dict:
        return self.data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Genome':
        return cls(data)


# ═══════════════════════════════════════════════════════════════════
# POPULATION MANAGER
# ═══════════════════════════════════════════════════════════════════

class PopulationManager:
    """Manages population of genomes"""
    
    def __init__(self, config: MinerConfig):
        self.config = config
        self.population: List[Genome] = []
        self.generation = 0
    
    def initialize_random(self, size: Optional[int] = None) -> List[Genome]:
        """Initialize random population"""
        size = size or self.config.population_size
        self.population = [Genome() for _ in range(size)]
        return self.population
    
    def evaluate(self, fitness_func: Callable[[Genome], Dict], 
                 progress_callback: Optional[Callable] = None) -> List[tuple]:
        """
        Evaluate all genomes
        
        Args:
            fitness_func: Function that takes a genome and returns metrics dict
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of (genome, fitness_score, metrics) tuples
        """
        results = []
        
        for i, genome in enumerate(self.population):
            try:
                metrics = fitness_func(genome)
                fitness = self._calculate_fitness(metrics)
                results.append((genome, fitness, metrics))
                
                if progress_callback:
                    progress_callback((i + 1) / len(self.population))
                    
            except Exception as e:
                logging.warning(f"Error evaluating genome: {e}")
                results.append((genome, -9999, {"error": str(e)}))
        
        # Sort by fitness
        results.sort(key=lambda x: x[1], reverse=True)
        self.population = [r[0] for r in results]
        
        return results
    
    def _calculate_fitness(self, metrics: Dict) -> float:
        """Calculate fitness score from metrics"""
        pnl = metrics.get("Total PnL", 0)
        num_trades = metrics.get("Total Trades", 0)
        win_rate = metrics.get("Win Rate %", 0)
        
        # Bonus for having trades
        trade_bonus = min(num_trades * 10, 100) if num_trades >= 5 else 0
        
        # Bonus for high win rate
        winrate_bonus = (win_rate - 50) * 2 if win_rate > 50 else 0
        
        return pnl + trade_bonus + winrate_bonus
    
    def evolve(self, evaluated_pop: List[tuple]) -> List[Genome]:
        """
        Create next generation through selection, crossover, mutation
        
        Args:
            evaluated_pop: List of (genome, fitness, metrics) tuples (already sorted)
            
        Returns:
            New population for next generation
        """
        # Elitism - keep best genomes
        elite_count = self.config.elitism_count
        survivors = [r[0] for r in evaluated_pop[:int(self.config.population_size * 0.2)]]
        
        next_pop = survivors[:elite_count]
        
        # Fill rest with crossover + mutation
        while len(next_pop) < self.config.population_size:
            p1 = random.choice(survivors)
            p2 = random.choice(survivors)
            
            # Crossover
            if random.random() < self.config.crossover_rate:
                child = p1.crossover(p2)
            else:
                child = p1
            
            # Mutation
            if random.random() < self.config.mutation_rate:
                child = child.mutate(self.config.mutation_rate)
            
            next_pop.append(child)
        
        self.generation += 1
        self.population = next_pop
        
        return next_pop


# ═══════════════════════════════════════════════════════════════════
# STRATEGY MINER AGENT - VERSIÓN INTEGRADA
# ═══════════════════════════════════════════════════════════════════

class StrategyMinerAgent(BaseAgent):
    """
    Strategy Miner Agent - Genetic Algorithm for Strategy Discovery.
    
    This agent integrates the existing strategy_miner.py logic:
    - Generates random trading strategies (genomes)
    - Evaluates fitness via backtesting
    - Evolves population through generations
    - Finds profitable strategies
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        miner_config = AgentConfig(
            agent_id="STRATEGY_MINER",
            agent_name="Genetic Strategy Miner",
            agent_type="MINER",
            log_level="INFO",
            cycle_interval=60,
            custom_config=config or {}
        )
        
        super().__init__(miner_config, message_bus)
        
        # Config
        self.miner_config = MinerConfig(
            population_size=config.get("population_size", 100) if config else 100,
            generations=config.get("generations", 20) if config else 20,
            mutation_rate=config.get("mutation_rate", 0.2) if config else 0.2
        )
        
        # Population manager
        self.pop_manager = PopulationManager(self.miner_config)
        
        # State
        self.best_genome: Optional[Genome] = None
        self.best_pnl = -float('inf')
        self.current_generation = 0
        self.generation_history: List[Dict] = []
        
        # Backtester (external reference)
        self.backtester = None
        self.data = None
        
        self.logger.info("🧬 Strategy Miner Agent inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════
    
    async def on_start(self):
        """Initialize Strategy Miner"""
        self.logger.info("🚀 Iniciando Strategy Miner...")
        
        # Subscribe to messages
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                task_types=[
                    "START_MINING",
                    "STOP_MINING",
                    "GET_BEST_STRATEGY",
                    "GET_GENERATION_STATUS",
                    "SET_DATA"
                ]
            )
        
        self.logger.info("✅ Strategy Miner listo")
    
    async def on_shutdown(self):
        """Shutdown"""
        self.logger.info("🛑 Deteniendo Strategy Miner...")
        self.logger.info(f"📊 Mejor PnL encontrado: ${self.best_pnl:.2f}")
    
    async def run_cycle(self):
        """Main cycle - mining continues if active"""
        if not self.data:
            return
        
        # Mining is event-driven, not continuous
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # MINING OPERATIONS
    # ═══════════════════════════════════════════════════════════════
    
    async def start_mining(
        self,
        data,
        target_pnl: float = 500,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Start mining process
        
        Args:
            data: DataFrame with OHLCV data
            target_pnl: Target PnL to stop mining
            progress_callback: Callback for progress updates
            
        Returns:
            Best genome found
        """
        self.data = data
        self.pop_manager.initialize_random()
        
        self.logger.info(f"🧬 Iniciando mining: {self.miner_config.population_size} pop × {self.miner_config.generations} gens")
        
        for gen in range(self.miner_config.generations):
            self.current_generation = gen
            
            self.logger.info(f"🧬 Generación {gen + 1}/{self.miner_config.generations}")
            
            # Progress callback
            if progress_callback:
                progress_callback("START_GEN", gen)
            
            # Evaluate
            def eval_callback(pct):
                if progress_callback:
                    global_pct = (gen + pct) / self.miner_config.generations
                    progress_callback("BATCH_PROGRESS", global_pct)
            
            evaluated = self.pop_manager.evaluate(
                fitness_func=self._evaluate_genome,
                progress_callback=eval_callback
            )
            
            # Check for cancellation (could be extended)
            
            # Get best of generation
            gen_best = evaluated[0]
            gen_best_pnl = gen_best[2].get("Total PnL", 0)
            
            self.logger.info(f"   🏆 Best PnL: ${gen_best_pnl:.2f}")
            
            # Track history
            self.generation_history.append({
                "generation": gen,
                "best_pnl": gen_best_pnl,
                "avg_pnl": sum(r[2].get("Total PnL", 0) for r in evaluated) / len(evaluated)
            })
            
            # Check target
            if gen_best_pnl >= target_pnl:
                self.logger.info(f"🎯 Target alcanzado: ${gen_best_pnl:.2f}")
                break
            
            # Evolve
            self.pop_manager.evolve(evaluated)
            
            # Update best
            if gen_best_pnl > self.best_pnl:
                self.best_pnl = gen_best_pnl
                self.best_genome = gen_best[0]
            
            # Progress callback
            if progress_callback:
                progress_callback("BEST_GEN", {
                    "generation": gen,
                    "pnl": gen_best_pnl,
                    "genome": gen_best[0].to_dict()
                })
        
        self.logger.info(f"✅ Mining completado. Mejor PnL: ${self.best_pnl:.2f}")
        
        return {
            "best_genome": self.best_genome.to_dict() if self.best_genome else None,
            "best_pnl": self.best_pnl,
            "generations": self.current_generation + 1,
            "history": self.generation_history
        }
    
    def _evaluate_genome(self, genome: Genome) -> Dict:
        """
        Evaluate a genome using the backtester
        This needs to be connected to the backtest system
        """
        if self.backtester:
            # Use actual backtester
            try:
                metrics, _ = self.backtester.run_backtest(
                    self.data,
                    genome.to_dict()
                )
                return metrics
            except Exception as e:
                self.logger.warning(f"Backtest error: {e}")
                return {"Total PnL": -9999, "Total Trades": 0}
        
        # Mock evaluation for testing
        return {
            "Total PnL": random.uniform(-500, 1000),
            "Total Trades": random.randint(0, 50),
            "Win Rate %": random.uniform(30, 70)
        }
    
    def set_backtester(self, backtester):
        """Set the backtester to use for evaluation"""
        self.backtester = backtester
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        
        if message.task_type == "START_MINING":
            return await self._handle_start_mining(message)
        
        elif message.task_type == "GET_BEST_STRATEGY":
            return self._handle_get_best(message)
        
        elif message.task_type == "GET_GENERATION_STATUS":
            return self._handle_get_status(message)
        
        elif message.task_type == "SET_DATA":
            return self._handle_set_data(message)
        
        return None
    
    async def _handle_start_mining(self, message: AgentMessage) -> AgentMessage:
        """Handle start mining request"""
        data = message.payload.get("data")
        target_pnl = message.payload.get("target_pnl", 500)
        
        def progress_callback(event, data):
            # This would send progress updates
            pass
        
        result = await self.start_mining(data, target_pnl, progress_callback)
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result=result
        )
    
    def _handle_get_best(self, message: AgentMessage) -> AgentMessage:
        """Get best strategy found"""
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "best_genome": self.best_genome.to_dict() if self.best_genome else None,
                "best_pnl": self.best_pnl,
                "generation": self.current_generation
            }
        )
    
    def _handle_get_status(self, message: AgentMessage) -> AgentMessage:
        """Get current mining status"""
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "current_generation": self.current_generation,
                "total_generations": self.miner_config.generations,
                "best_pnl": self.best_pnl,
                "history": self.generation_history,
                "population_size": len(self.pop_manager.population)
            }
        )
    
    def _handle_set_data(self, message: AgentMessage) -> AgentMessage:
        """Set data for mining"""
        self.data = message.payload.get("data")
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={"data_set": self.data is not None}
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def get_miner_status(self) -> Dict[str, Any]:
        """Get miner status"""
        return {
            "best_pnl": self.best_pnl,
            "current_generation": self.current_generation,
            "target_generations": self.miner_config.generations,
            "population_size": self.miner_config.population_size,
            "history": self.generation_history
        }
    
    def __repr__(self) -> str:
        return f"<StrategyMiner(gen={self.current_generation}, best_pnl=${self.best_pnl:.2f})>"
