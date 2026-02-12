# 🏢 Bittrading Corp

## Sistema de Trading Autónoma Multi-Agente

¡Bienvenido a **Bittrading Corp** - una empresa de trading totalmente autónoma manejada por agentes de IA!

---

## 🎯 Descripción

Bittrading Corp es un sistema de trading avanzado donde cada fase del proceso es manejada por un agente IA especializado, trabajando colaborativamente bajo coordinación central.

### Estructura de Agentes

| Agente | Rol | Responsabilidad |
|--------|-----|-----------------|
| 🧠 **CEO** | Chief Executive Orchestrator | Coordinación general, decisiones estratégicas |
| 📊 **Market Scanner** | Head of Market Intelligence | Escaneo de mercados, identificación de oportunidades |
| 📈 **Analyst** | Senior Market Analyst | Análisis técnico y fundamental |
| 🧪 **Strategy Generator** | Chief Strategy Officer | Generación de estrategias de trading |
| ⚡ **Backtest Orchestrator** | Head of Backtesting | Coordinación de backtesting distribuido |
| 🎯 **Strategy Selector** | Chief Investment Officer | Selección de estrategias |
| 💰 **Risk Manager** | Chief Risk Officer | Control de riesgo (¡PODER DE VETO!) |
| 🤖 **Trader** | Execution Specialist | Ejecución de trades en exchanges |
| 🔧 **Worker Manager** | Infrastructure Manager | Gestión de infraestructura workers |
| 📋 **Task Manager** | Project Manager | Flujo de trabajo y tareas |

---

## 🚀 Inicio Rápido

### Prerrequisitos

```bash
# Python 3.10+
python --version

# pip o poetry
pip --version
```

### Instalación

```bash
# Clonar o navegar al directorio
cd /Users/enderj/Bittrading_Corp

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: .\venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Configuración

```bash
# Copiar archivo de configuración de ejemplo
cp config.example.yaml config.yaml

# Editar configuración
nano config.yaml
```

### Iniciar el Sistema

```bash
# Iniciar todos los agentes
python main.py

# O con opciones adicionales
python main.py --log-level DEBUG --config config.yaml
```

---

## 📁 Estructura del Proyecto

```
Bittrading_Corp/
├── agents/                          # Agentes especializados
│   ├── base_agent.py                # Clase base para todos los agentes
│   ├── ceo.py                       # Chief Executive Orchestrator
│   ├── market_scanner.py            # Head of Market Intelligence
│   ├── strategy_generator.py        # Chief Strategy Officer
│   ├── backtest_orchestrator.py     # Head of Backtesting
│   ├── risk_manager.py              # Chief Risk Officer (VETO POWER)
│   ├── trader.py                    # Execution Specialist
│   ├── analyst.py                   # Senior Market Analyst
│   ├── strategy_selector.py         # Chief Investment Officer
│   ├── worker_manager.py            # Infrastructure Manager
│   └── task_manager.py              # Project Manager
│
├── mission_control/                 # Núcleo de coordinación
│   └── message_bus.py              # Sistema de mensajería
│
├── shared/                          # Recursos compartidos
│   ├── database.py                 # Base de datos centralizada
│   └── models.py                   # Modelos de datos
│
├── workers_integration/             # Integración con workers
│   ├── complete_coordinator_bridge.py  # Bridge completo con Coordinator
│   ├── coordinator_adapter.py      # Adapter del Coordinator
│   ├── dashboard_integration.py    # Integración dashboards
│   └── strategy_miner_adapter.py   # Adapter del Miner
│
├── strategies/                      # Biblioteca de estrategias
│
├── database/                        # Base de datos SQLite
│
├── logs/                           # Logs del sistema
│   ├── agents/
│   ├── mission_control/
│   └── trades/
│
├── config/                          # Configuraciones
│   ├── agents.yaml                 # Configuración de agentes
│   ├── exchange.yaml               # Configuración exchanges
│   └── risk.yaml                   # Configuración de riesgo
│
├── main.py                          # Punto de entrada
├── run_unified.py                   # Script unificado
├── requirements.txt                 # Dependencias
└── README.md                        # Este archivo
```

---

## 🔧 Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Coinbase API
COINBASE_API_KEY=tu_api_key
COINBASE_API_SECRET=tu_api_secret
COINBASE_PASSPHRASE=tu_passphrase

# Base de datos (opcional)
DATABASE_URL=sqlite:///./trading_corp.db

# Workers Coordinator
COORDINATOR_URL=100.77.179.14:5001

# Configuración de riesgo
MAX_POSITION_SIZE=5
MAX_DAILY_DRAWDOWN=5
MAX_TOTAL_EXPOSURE=25
```

---

## 📊 Límites de Riesgo

El **Risk Manager** tiene los siguientes límites por defecto:

| Límite | Valor | Severidad |
|--------|-------|-----------|
| Tamaño máx. posición | 5% | CRITICAL |
| Exposición total | 25% | CRITICAL |
| Drawdown diario | 5% | HARD_STOP |
| Drawdown semanal | 10% | HARD_STOP |
| Drawdown desde peak | 15% | HARD_STOP |

⚠️ **IMPORTANTE**: El Risk Manager tiene **PODER DE VETO** y puede detener cualquier operación.

---

## 🔄 Flujo de Trabajo

```
┌──────────────────────────────────────────────────────────────────┐
│                    BITTRADING CORP                                │
└──────────────────────────────────────────────────────────────────┘

   ┌─────────────────┐
   │  Market Scanner │ ← Escanea mercados 24/7
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │    Analyst      │ ← Análisis técnico
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │Strategy Generator│ ← Crea estrategias
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │Backtest Orchestrator│ ← Coordina backtests
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │    Optimizer    │ ← Optimiza parámetros
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │Strategy Selector│ ← Selecciona portfolio
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │ Risk Manager    │ ← ⭐ VETO POWER
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │     Trader      │ ← Ejecuta trades
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │   CEO           │ ← Coordina todo
   └─────────────────┘
```

---

## 🛠️ Uso Avanzado

### Iniciar Solo Agentes Específicos

```python
from agents.ceo import CEOAgent
from mission_control.message_bus import MessageBus
import asyncio

async def main():
    message_bus = MessageBus()
    await message_bus.start_delivery_workers(3)

    ceo = CEOAgent(message_bus)
    await ceo.start()

asyncio.run(main())
```

### Enviar Tareas a Agentes

```python
from agents.base_agent import AgentMessage, TaskPriority

# Enviar solicitud de escaneo al Market Scanner
message = AgentMessage(
    to_agent="MARKET_SCANNER",
    task_type="SCAN_NOW",
    priority=TaskPriority.HIGH,
    payload={"priority": "HIGH"}
)

await message_bus.publish(message)
```

### Ver Estado del Sistema

```python
# Obtener dashboard del CEO
ceo = agents["CEO"]
status = ceo.get_ceo_dashboard()
print(status)
```

---

## 📈 Monitoreo

### Ver Logs

```bash
# Logs en tiempo real
tail -f logs/system_*.log

# Logs de un agente específico
tail -f logs/agents/RISK_MANAGER.log
```

### Endpoints de Estado

Accede a través del CEO Agent:
- `STATUS_REQUEST`: Estado general
- `GET_RISK_STATUS`: Estado de riesgo
- `GET_POSITIONS`: Posiciones actuales

---

## 🔒 Seguridad

1. **API Keys**: Nunca compartas tus API keys
2. **Limit Testing**: Siempre prueba con paper trading primero
3. **Emergency Stop**: El sistema tiene múltiples niveles de emergencia
4. **Audit Log**: Todas las acciones son registradas

---

## 🚨 Emergency Procedures

### Detener Trading Inmediatamente

```python
# Enviar emergency stop
message = AgentMessage(
    to_agent="RISK_MANAGER",
    task_type="EMERGENCY_STOP",
    priority=TaskPriority.CRITICAL,
    payload={"reason": "Manual intervention"}
)
```

### Cerrar Todas las Posiciones

```python
# A través del Trader
message = AgentMessage(
    to_agent="TRADER",
    task_type="CLOSE_POSITION",
    payload={"symbol": "ALL", "force": True}
)
```

---

## 📝 Contribuir

1. Fork el proyecto
2. Crea tu rama de feature (`git checkout -b feature/NuevaEstrategia`)
3. Commit tus cambios (`git commit -am 'Agregar nueva estrategia'`)
4. Push a la rama (`git push origin feature/NuevaEstrategia`)
5. Crea un Pull Request

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

---

## 🤝 Contacto

- **GitHub**: https://github.com/enderjnets/Bittrading-Corp

---

*Built with ❤️ by Bittrading Corp*
*Trading Automatizado de Próxima Generación*
