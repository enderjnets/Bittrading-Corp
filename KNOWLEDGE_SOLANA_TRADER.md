# 📚 CONOCIMIENTO EXTRAÍDO - Solana Trading System
# ============================================
# Basado en: https://github.com/enderjnets/Solana-Cripto-Trader
# Fecha: Febrero 2026

Este documento contiene todo el conocimiento valioso extraído del proyecto
Solana Cripto Trader para integrar en Bittrading Trading Corp.

---

## 🎯 PRINCIPALES INNOVACIONES

### 1. MiniMax 2.1 Integration
- Thinking mode para Chain of Thought reasoning
- 230B parámetros totales, 10B activos (MoE)
- 204,800 tokens context window
- 128,000 tokens max output

### 2. Multi-Agent Orchestrator
- Agent registry con capacidades
- Inter-agent messaging (sessions_send)
- Sub-agent spawner (sessions_spawn)
- Task delegation con prioridades P0-P3

### 3. Genetic Strategy Miner
- Numba JIT accelerated (4000x speedup!)
- SQLite persistence
- Genome encoding para backtesting
- Elitism y tournament selection

### 4. Mission Control v2
- Thinking mode para razonamiento profundo
- Agentes especializados con memoria
- Activity feed
- Memory flush protocol

---

## 🏗️ ARQUITECTURA COMPLETA

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MISSION CONTROL V2                              │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                    MiniMax 2.1 (MoE)                      │   │
│  │  230B params, 10B active, Thinking mode enabled            │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                   BASE AGENT (Thinking)                      │   │
│  │                                                              │   │
│  │  async def think(task, context)                              │   │
│  │  def remember(key, value)                                   │   │
│  │  def recall(key)                                            │   │
│  │  async def run_task(task, context)                           │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│              ┌───────────────┼───────────────┐                     │
│              ▼               ▼               ▼                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ TradingAgent │ │AnalysisAgent│ │  RiskAgent  │          │
│  │              │ │              │ │              │          │
│  │ - swap      │ │ - analyze   │ │- assess     │          │
│  │ - balance   │ │ - scan      │ │- validate   │          │
│  │ - get_price │ │ - sentiment │ │- calculate  │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│              ┌───────────────┼───────────────┐                     │
│              ▼               ▼               ▼                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │Communication │ │Optimization  │ │ Orchestrator │          │
│  │   Agent     │ │   Agent     │ │              │          │
│  │- send_msg  │ │- optimize   │ │- delegate   │          │
│  │- send_voice│ │- backtest   │ │- route_task │          │
│  │- format    │ │- evolve     │ │- workflow   │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 AGENTES ESPECIALIZADOS

### Coordinator Agent
```python
{
    "agent_id": "coordinator",
    "name": "Eko Coordinator",
    "role": "Project Lead",
    "specialty": "Task breakdown and delegation",
    "capabilities": [
        "planning", "delegation", "monitoring", "reporting"
    ]
}
```

### Trading Agent
```python
{
    "agent_id": "trading_agent",
    "name": "Eko Trader",
    "role": "Trading Specialist",
    "specialty": "Solana/Jupiter DEX",
    "capabilities": [
        "swap", "balance", "orders", "backtest"
    ]
}
```

### Risk Agent
```python
{
    "agent_id": "risk_agent", 
    "name": "Eko Risk Manager",
    "role": "Risk Specialist",
    "specialty": "Risk assessment",
    "capabilities": [
        "risk_assessment", "limit_check", "validation"
    ]
}
```

---

## 🧠 THINKING MODE (MiniMax 2.1)

```python
async def think(self, task: str, context: Dict = None) -> Dict:
    """
    Use MiniMax 2.1 thinking mode for deep reasoning.
    
    CRUCIAL for agentic tasks - without thinking mode,
    the model loses its chain of reasoning.
    """
    system_prompt = """You are a specialized trading agent.
    Think through the problem step by step.
    Output your thinking in <thinking> tags.
    Then provide your final answer."""
    
    full_prompt = f"{system_prompt}\n\nContext: {context}\n\nTask: {task}"
    
    # Call MiniMax 2.1 API with thinking enabled
    return {
        "thinking": reasoning_content,
        "reasoning_steps": [
            "Analyzing the task...",
            "Reviewing context...",
            "Formulating strategy...",
            "Validating approach..."
        ],
        "response": final_answer,
        "tokens_used": len(prompt.split())
    }
```

---

## 🔄 MULTI-AGENT COMMUNICATION

### Inter-Agent Messaging
```python
class InterAgentMessaging:
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: str,
        priority: str = "normal",  # normal, high, urgent
        context: Dict = None
    ) -> Dict:
        """Send message from one agent to another"""
        message_id = str(uuid4())[:8]
        
        envelope = {
            "message_id": message_id,
            "from": from_agent,
            "to": to_agent,
            "message": message,
            "priority": priority,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "status": "delivered"
        }
        
        # Queue message
        if to_agent in registry.message_queue:
            registry.message_queue[to_agent].append(envelope)
        
        return {
            "status": "delivered",
            "message_id": message_id,
            "to": to_agent
        }
    
    async def broadcast(
        self,
        from_agent: str,
        message: str,
        to_agents: List[str] = None
    ):
        """Broadcast message to multiple agents"""
        targets = to_agents or list(registry.agents.keys())
        for agent_id in targets:
            if agent_id != from_agent:
                await self.send_message(from_agent, agent_id, message)
```

### Sub-Agent Spawner
```python
class SubAgentSpawner:
    async def spawn(
        self,
        parent_agent: str,
        task: str,
        model: str = "minimax/MiniMax-M2.1-lightning"
    ) -> Dict:
        """Spawn a sub-agent for parallel task execution"""
        session_id = f"sub_{uuid4().hex[:12]}"
        sub_agent_id = f"{parent_agent}_sub_{len(active_subagents)}"
        
        subagent = {
            "session_id": session_id,
            "agent_id": sub_agent_id,
            "parent": parent_agent,
            "task": task,
            "model": model,
            "status": "running",
            "created_at": datetime.now().isoformat()
        }
        
        active_subagents[session_id] = subagent
        return {
            "session_id": session_id,
            "agent_id": sub_agent_id,
            "status": "running"
        }
```

---

## 🎯 TASK DELEGATION PROTOCOL

### Priority Levels

| Level | Description | Examples |
|-------|-------------|----------|
| P0 | Urgent, immediate action | Emergency stop, large trades |
| P1 | High priority today | Strategy deployment |
| P2 | This week | Research, optimization |
| P3 | Backlog | Documentation, improvements |

### Delegation Steps
```
1. Receive task from user or cron
2. Analyze complexity and requirements
3. Decompose into subtasks
4. Select agents based on capabilities
5. Spawn/delegate with context
6. Monitor progress
7. Validate results
8. Report to user
```

### Workflow Example
```python
workflow = {
    "name": "Deploy New Trading Strategy",
    "steps": [
        {"task": "Research market conditions", "agent": "web_search", "priority": "high"},
        {"task": "Implement strategy code", "agent": "write", "priority": "normal"},
        {"task": "Security audit", "agent": "security_scan", "priority": "high"},
        {"task": "Create monitoring dashboard", "agent": "dashboard", "priority": "normal"}
    ]
}
```

---

## 🧬 GENETIC STRATEGY MINER (AVANZADO)

### Genome Encoding
```python
class GenomeEncoder:
    """Encode genomes for Numba JIT backtesting"""
    
    IND_CLOSE = 0
    IND_HIGH = 1
    IND_LOW = 2
    IND_RSI = 3
    IND_SMA = 4
    IND_EMA = 5
    IND_BB_HIGH = 6
    IND_BB_LOW = 7
    IND_BB_MID = 8
    
    OP_GT = 0  # >
    OP_LT = 1  # <
    
    MAX_RULES = 3
    GENOME_SIZE = 20  # [sl_pct, tp_pct, size, num_entry, num_exit, rules...]
    
    @classmethod
    def encode(cls, genome: Genome) -> np.ndarray:
        """Encode genome to fixed-size numpy array for JIT"""
        arr = np.zeros(cls.GENOME_SIZE, dtype=np.float64)
        
        # Basic params
        arr[0] = genome.params.get("sl_pct", 0.03)
        arr[1] = genome.params.get("tp_pct", 0.05)
        arr[2] = genome.params.get("position_size", 0.1)
        
        # Entry rules encoding
        for i, rule in enumerate(genome.entry_rules[:cls.MAX_RULES]):
            base = 5 + i * 5
            arr[base] = cls._encode_indicator(rule.get("indicator", "RSI"))
            arr[base + 1] = rule.get("period", 14)
            arr[base + 2] = cls._encode_operator(rule.get("operator", ">"))
            arr[base + 3] = rule.get("threshold", 30)
        
        return arr
```

### Evolution with Elitism
```python
def evolve(self, verbose: bool = True) -> Dict:
    """Run the genetic algorithm with elitism"""
    
    # Initialize population
    population = [self.generate_random_genome() for _ in range(self.pop_size)]
    
    best_genome = None
    best_pnl = float('-inf')
    
    for gen in range(self.generations):
        # Evaluate all
        results = []
        for genome in population:
            pnl, win_rate, sharpe = self.evaluate(genome)
            results.append((genome, pnl, win_rate, sharpe))
            
            if pnl > best_pnl:
                best_pnl = pnl
                best_genome = genome
        
        # Sort by PnL
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Elitism: keep top 5
        elite = [r[0] for r in results[:5]]
        
        # Create next generation
        new_population = elite.copy()
        
        while len(new_population) < self.pop_size:
            # Tournament selection
            parent1 = random.choice(elite)
            parent2 = random.choice(elite)
            
            # Crossover
            child = self.crossover(parent1, parent2)
            
            # Mutation
            child = self.mutate(child)
            
            new_population.append(child)
        
        population = new_population
        
        if verbose and gen % 5 == 0:
            print(f"Gen {gen}: Best PnL={results[0][1]:.4f}, Win Rate={results[0][2]:.1%}")
    
    return self.evaluate(best_genome)
```

---

## 💾 MEMORY FLUSH PROTOCOL

```python
async def memory_flush(self) -> Dict:
    """
    Perform memory flush before context compaction.
    Critical for preventing context loss.
    """
    flush_report = {
        "timestamp": datetime.now().isoformat(),
        "pending_tasks": len(task_history),
        "active_agents": [
            a for a in registry.agents.values() 
            if a.status != "available"
        ],
        "recent_decisions": task_history[-10:],
        "sub_agents_active": len(spawner.list_active())
    }
    
    # Save to persistent storage
    with open("data/multi_agent_memory.json", 'w') as f:
        json.dump(flush_report, f, indent=2, default=str)
    
    logger.info(f"Memory flush completed: {len(task_history)} tasks recorded")
    
    return flush_report
```

---

## 🔐 SECURITY FRAMEWORK

### Config Protection
```json
{
  "security": {
    "approvals": {
      "exec": { "enabled": true },
      "trades": { "enabled": true, "threshold": 0.1 }
    },
    "sandbox": {
      "enabled": true,
      "docker": true
    }
  },
  "gateway": {
    "bind": "loopback"
  }
}
```

### Trade Limits
- **Max position:** 20% of portfolio
- **Daily loss limit:** 5%
- **Approval required:** Above 10%

---

## 📊 DASHBOARD INTEGRATION

### Activity Feed
```python
class MissionControlV2:
    def _log_activity(self, event_type: str, data: Dict):
        """Log activity for feed"""
        self.activity_feed.append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_activity_feed(self, limit: int = 50) -> List[Dict]:
        """Get activity feed for dashboard"""
        return self.activity_feed[-limit:]
```

---

## 🚀 QUICK START (DEL PROYECTO)

```bash
# Start multi-agent orchestrator
python3 agents/multi_agent_orchestrator.py

# Run Mission Control v2
python3 mission_control_v2.py

# Start trading dashboard
streamlit run dashboard/solana_dashboard.py

# Connect workers to coordinator
COORDINATOR_URL="http://localhost:5001" python3 crypto_worker.py
```

---

## 📁 ARCHIVOS CLAVE

| File | Propósito |
|------|-----------|
| `mission_control_v2.py` | Multi-agent orchestrator con MiniMax |
| `agents/multi_agent_orchestrator.py` | Agent registry y messaging |
| `strategies/genetic_miner.py` | Genetic algorithm optimizer |
| `agents/AGENTS.md` | Documentación de agentes |
| `dashboard/solana_dashboard.py` | Dashboard de trading |
| `telegram_bot.py` | Telegram integration |

---

## 🎓 LECCIONES APRENDIDAS

1. **Thinking mode es crucial** para razonamiento complejo
2. **Elitism mejora** la convergencia del genetic algorithm
3. **Sub-agents permiten** paralelismo efectivo
4. **Memory flush previene** pérdida de contexto
5. **Priority levels** organizan el trabajo eficientemente
6. **Activity feed** es esencial para debugging
7. **Sandboxing** es crítico para seguridad

---

## 🔄 INTEGRACIÓN CON OPENCLAW

El proyecto Solana Cripto Trader tiene avanzadas implementaciones que
debemos integrar en Bittrading Trading Corp:

### Prioridad Alta
- [ ] Implementar MiniMax 2.1 thinking mode
- [ ] Agregar sub-agent spawner
- [ ] Implementar genetic miner con Numba JIT
- [ ] Mejorar activity feed

### Prioridad Media
- [ ] Agregar memory flush protocol
- [ ] Implementar priority levels P0-P3
- [ ] Mejorar agent registry
- [ ] Integrar communication agent

### Prioridad Baja
- [ ] Telegram bot integration
- [ ] Voice interface (PersonaPlex)
- [ ] Docker sandboxing

---

*Extraído de: https://github.com/enderjnets/Solana-Cripto-Trader*
*Fecha: Febrero 2026*
