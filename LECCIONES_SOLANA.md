# 📚 LECCIONES APRENDIDAS DEL PROYECTO SOLANA-CRIPTO-TRADER

## 📋 Resumen

Este documento contiene las lecciones aprendidas, bugs corregidos y mejoras implementadas en el proyecto **Solana-Cripto-Trader** que deben aplicarse al proyecto **Bittrading Corp** para evitar errores similares.

**Fuente:** https://github.com/enderjnets/Solana-Cripto-Trader  
**Fecha:** 2026-02-12  
**Commit analizado:** d5a1fa5 (3rd audit fix)

---

## 🚨 BUGS CRÍTICOS CORREGIDOS

### 1. **evaluate_genome() Usaba RSI<30 Hardcodeado** 🔴

**Problema:**
```python
# ANTES (BUGGY - solana_backtester.py)
def evaluate_genome():
    if HAS_NUMBA:
        return evaluate_genome_jit(...)  # ¡Hardcodeaba RSI < 30!
    else:
        return evaluate_genome_python(...)
```

El JIT version ignoraba las `entry_rules` del genome y usaba `RSI < 30` hardcodeado, haciendo que todas las estrategias evaluadas usaran los mismos parámetros sin importar lo que el genome especificara.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
def evaluate_genome():
    """Always uses Python version which correctly reads genome entry rules.
    The JIT version is legacy and hardcodes RSI < 30.
    """
    return evaluate_genome_python(indicators, genome, initial_balance)
```

**Impacto:** Todas las estrategias optimizadas eran iguales (RSI<30) sin importar sus reglas reales.

**Acción para Bittrading Corp:**
- [ ] Verificar que `numba_backtester.py` no tenga reglas hardcodeadas
- [ ] Asegurar que `strategy_miner.py` use las entry_rules del genome
- [ ] Testear con genomes que tengan reglas diferentes a RSI<30

---

### 2. **SQLite Connection Leak** 🔴

**Problema:**
```python
# ANTES (BUGGY)
def some_function():
    c = sqlite3.connect("db.sqlite")
    c.execute("SELECT ...")
    # ¡Nunca se cerraba la conexión!
```

Sin context manager, las conexiones SQLite se acumulaban hasta saturar el sistema.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
def some_function():
    with sqlite3.connect("db.sqlite") as c:
        c.execute("SELECT ...")
    # La conexión se cierra automáticamente
```

**Impacto:** Hasta 720 conexiones/día según el audit.

**Acción para Bittrading Corp:**
- [ ] Revisar `coordinator_port5001.py` y envolver todas las operaciones DB en context managers
- [ ] Revisar `shared/database.py` en Bittrading Corp
- [ ] Verificar que `optimization_persistence.py` use context managers

---

### 3. **AsyncClient Connection Leak (720/día)** 🔴

**Problema:**
```python
# ANTES (BUGGY)
async def get_balance():
    client = AsyncClient("https://api.devnet.solana.com")
    resp = await client.get_balance(...)
    await client.close()  # ¡Se olvidaba en muchos casos!
```

Cada llamada creaba un nuevo AsyncClient que raramente se cerraba.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
class JupiterWorker:
    def __init__(self):
        self.sol_client = None  # Cliente persistente
    
    async def get_balance(self):
        if self.sol_client is None:
            self.sol_client = AsyncClient("https://api.devnet.solana.com")
        # Reutilizar el mismo cliente
```

**Impacto:** 720 conexiones/día en el audit.

**Acción para Bittrading Corp:**
- [ ] En `coinbase_client.py`, usar cliente persistente
- [ ] Verificar que todas las llamadas APIusen el mismo cliente
- [ ] Implementar cleanup al shutdown

---

### 4. **_mutate() Corruption** 🔴

**Problema:**
```python
# ANTES (BUGGY)
def _mutate(self, genome):
    # ¡Modificaba el genome original!
    genome["params"]["sl_pct"] = random.uniform(...)
    return genome  # ¡Población GA corrompida!
```

Sin deep copy, las mutaciones afectaban el genome original, corrompiendo la población del algoritmo genético.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
import copy

def _mutate(self, genome):
    new_genome = copy.deepcopy(genome)  # Copia antes de modificar
    new_genome["params"]["sl_pct"] = random.uniform(...)
    return new_genome  # Retorna copia modificada
```

**Impacto:** La población GA convergía prematuramente a soluciones subóptimas.

**Acción para Bittrading Corp:**
- [ ] En `strategy_generator.py`, verificar que _mutate use deep copy
- [ ] En `strategy_miner.py`, verificarpopulation management
- [ ] Testear convergencia de GA con genomas conocidos

---

### 5. **Corrupted Token Addresses** 🔴

**Problema:**
```python
# ANTES (BUGGY)
TOKENS = {
    "WIF": "EKpQGSJtjMFqKZ9KQanSqWJcNSPWfqHYJQD7i阜eLJ",  # Caracter chino!
    "USDT": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # ¿Correcto?
}
```

Direcciones con caracteres corruptos causaban fallos silenciosos en swaps.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
TOKENS = {
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",  # Verificado
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYW",  # Verificado Jupiter API
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoZGVixqUi5iA2ztETHuJXJP",  # Verificado
    "PYTH": "HZ1JovNiBEgZ1W7E2hKQzF8Tz3G6fZ6K3jKGn1c3bY7V",  # Verificado
}
```

**Verificación:** Usar `jupiter_api_skill.md` para validar direcciones contra Jupiter API.

**Acción para Bittrading Corp:**
- [ ] En `config.py`, verificar todas las direcciones de tokens de Coinbase
- [ ] Crear script de validación contra API oficial
- [ ] Documentar fuentes de direcciones verificadas

---

### 6. **SMA/EMA Logic Error** 🟡

**Problema:**
```python
# ANTES (BUGGY)
# El backtester comparaba indicator vs 0, no price vs indicator
if sma > 0:  # ¡SMA siempre es > 0 para precios positivos!
    buy_condition = True
```

SMA/EMA siempre son positivos para precios positivos, haciendo que la lógica fuera inútil.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
# Comparar price vs indicator con % deviation
deviation = threshold / 100.0  # 0.5% a 3%
if price < sma * (1 - deviation):  # Price está X% debajo de SMA
    buy_condition = True
```

**Acción para Bittrading Corp:**
- [ ] En `dynamic_strategy.py`, verificar lógica de SMA/EMA
- [ ] En `backtester.py`, verificar comparaciones
- [ ] Asegurar que random strategies usen % deviation thresholds

---

### 7. **Sell Signal Uses Wrong TP** 🟡

**Problema:**
```python
# ANTES (BUGGY)
# Sell overlay usaba 12.6% hardcodeado
sell_threshold = 0.126  # ¡No venía del brain!
```

El TP para sell no usaba los parámetros del genome.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
# Usar brain_params TP en lugar de valor hardcodeado
brain_params = active_strategy.get("brain_params", {})
tp_pct = brain_params.get("tp_pct", 0.02)  # 2% del brain
```

**Acción para Bittrading Corp:**
- [ ] En `strategy.py`, verificar que buy y sell usen mismos params
- [ ] Asegurar que dynamic_strategy.py use genome params correctamente
- [ ] Testear con estrategias que tengan diferentes TP

---

### 8. **Drawdown Tracking Bug** 🟡

**Problema:**
```python
# ANTES (BUGGY)
# Drawdown solo se trackeaba entre trades, no continuamente
if balance > max_balance:
    max_balance = balance
# ¡No actualizaba durante posiciones abiertas!
```

El drawdown máximo no se calculaba correctamente durante posiciones abiertas.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
# Trackear drawdown en CADA vela, no solo entre trades
for candle in candles:
    current_balance = calculate_balance(candle)
    if current_balance > max_balance:
        max_balance = current_balance
    dd = (max_balance - current_balance) / max_balance
    max_drawdown = max(max_drawdown, dd)
```

**Acción para Bittrading Corp:**
- [ ] En `backtester.py`, verificar que drawdown se calcule continuamente
- [ ] Verificar `autonomous_trading_system.py` para trading real
- [ ] Testear con posiciones abiertas por largos períodos

---

### 9. **.seconds vs .total_seconds()** 🟡

**Problema:**
```python
# ANTES (BUGGY)
elapsed = (end_time - start_time).seconds  # ¡Solo segundos, sin microsegundos!
```

`.seconds` retorna solo la componente de segundos, perdiendo precisión.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
elapsed = (end_time - start_time).total_seconds()  # Include microsegundos
```

**Acción para Bittrading Corp:**
- [ ] Buscar todos los `.seconds` en el código
- [ ] Reemplazar por `.total_seconds()`
- [ ] Verificar timing de operaciones críticas

---

### 10. **min_position_pct Not Enforced** 🟡

**Problema:**
```python
# ANTES (BUGGY)
# RiskAgent aceptaba positions menores a 10%
if amount < min_allowed:
    return {"approved": False, ...}  # Pero nadie respetaba esto!
```

El límite mínimo existía pero no se aplicaba consistentemente.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
class RiskAgent:
    def validate(self, trade, portfolio):
        min_pos = PROFIT_TARGETS["min_position_pct"]  # 10%
        if amount < portfolio * min_pos:
            return {"approved": False, "reason": f"Below min {min_pos:.0%}"}
```

**Acción para Bittrading Corp:**
- [ ] En `risk_manager.py`, verificar que todos los límites se apliquen
- [ ] Testear edge cases (posiciones muy pequeñas)
- [ ] Documentar todos los límites de riesgo

---

### 11. **cbBTC Decimal Handling** 🟡

**Problema:**
```python
# ANTES (BUGGY)
# cbBTC tiene 8 decimales, no 9 como SOL
amount = lamports / 1e9  # ¡Wrong para cbBTC!
```

cbBTC usa 8 decimales, diferente a SOL (9).

**Solución:**
```python
# DESPUÉS (CORREGIDO)
DECIMALS = {
    "SOL": 9,
    "USDC": 6,
    "USDT": 6,
    "cbBTC": 8,  # ¡Correcto!
}

amount = lamports / (10 ** DECIMALS[token])
```

**Acción para Bittrading Corp:**
- [ ] En `coinbase_client.py`, verificar decimales para cada token
- [ ] Crear diccionario de decimals para todos los pares
- [ ] Testear con tokens de diferentes precisiones

---

### 12. **Duplicate Except Clause SyntaxError** 🔴

**Problema:**
```python
# ANTES (BUGGY)
try:
    something()
except ValueError:
    handle()
except ValueError:  # ¡Duplicate!
    handle_again()
```

Error de sintaxis que crasheaba el dashboard.

**Solución:**
```python
# DESPUÉS (CORREGIDO)
try:
    something()
except ValueError as e:
    handle(e)
```

**Acción para Bittrading Corp:**
- [ ] Revisar todos los blocks try/except
- [ ] Usar linter para detectar duplicados
- [ ] Testear todos los paths de error

---

## ✅ MEJORAS RECOMENDADAS PARA BITTRADING CORP

### Prioridad ALTA

1. **Verificar evaluate_genome en numba_backtester.py**
   - Comparar con solana_backtester.py corregido
   - Asegurar que use entry_rules del genome

2. **SQLite Context Managers**
   - Revisar coordinator_port5001.py
   - Revisar optimization_persistence.py
   - Revisar shared/database.py

3. **Deep Copy en Strategy Generator**
   - Verificar _mutate() en strategy_generator.py
   - Verificar _crossover() si existe

4. **Validación de Token Addresses**
   - Crear script de validación
   - Verificar contra API de Coinbase
   - Documentar fuentes

### Prioridad MEDIA

5. **Drawdown Tracking Continuo**
   - Verificar backtester.py
   - Implementar si falta

6. **SMA/EMA Logic**
   - Revisar dynamic_strategy.py
   - Comparar con lógica corregida

7. **.seconds → .total_seconds()**
   - Buscar y reemplazar en todo el código

8. **Risk Limits Enforcement**
   - Verificar risk_manager.py
   - Testear edge cases

### Prioridad BAJA

9. **cbBTC-style Decimal Handling**
   - Crear diccionario de decimals
   - Testear con diferentes tokens

10. **Syntax Review**
    - Usar linter
    - Revisar try/except blocks

---

## 📊 CHECKLIST DE VERIFICACIÓN

```markdown
## Bug Criticos
- [ ] evaluate_genome() usa entry_rules del genome (no hardcoded)
- [ ] SQLite usa context managers
- [ ] AsyncClient es persistente
- [ ] _mutate() usa deep copy
- [ ] Token addresses están verificados

## Mejoras
- [ ] Drawdown tracking es continuo
- [ ] SMA/EMA compara price vs indicator
- [ ] .total_seconds() usado en lugar de .seconds
- [ ] Risk limits se aplican consistentemente
- [ ] Decimales son correctos para cada token

## Testing
- [ ] GA converge correctamente
- [ ] Backtests usan reglas del genome
- [ ] Drawdown es preciso
- [ ] No hay connection leaks
```

---

## 🔗 RECURSOS

- **Proyecto Solana:** https://github.com/enderjnets/Solana-Cripto-Trader
- **Commit 3rd Audit:** d5a1fa5
- **Commit 2nd Audit:** 31aeebb
- **Jupiter API:** https://dev.jup.ag/api-reference
- **Coinbase API:** https://docs.cloud.coinbase.com/

---

*Documento generado: 2026-02-12*
*Para aplicar en: Bittrading Corp*
