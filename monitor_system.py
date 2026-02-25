#!/usr/bin/env python3
"""
📊 Monitor Bittrading-Corp Completo
"""

import subprocess
from datetime import datetime

def monitor():
    print("="*70)
    print("🏢 BITTRADING-CORP - SISTEMA COMPLETO MULTI-AGENTE")
    print("="*70)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S MST')}")
    print()
    
    # Verificar proceso
    result = subprocess.run(['pgrep', '-af', 'python main.py'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ SISTEMA: OPERATIVO")
        for line in result.stdout.strip().split('\n'):
            print(f"   PID: {line}")
    else:
        print("❌ SISTEMA: DETENIDO")
        return
    
    print()
    print("🤖 AGENTES ACTIVOS")
    print("-"*70)
    print("   1. 🧠 CEO - Coordinador")
    print("   2. 📊 Market Scanner - Inteligencia")
    print("   3. 💰 Risk Manager - VETO POWER")
    print("   4. 🤖 Trader - Paper Trading")
    print("   5. 🧪 Strategy Generator - Estrategias")
    print("   6. ⚡ Backtest Orchestrator - Backtesting")
    print()
    
    print("📊 ESTADÍSTICAS")
    print("-"*70)
    
    # Leer últimos logs
    try:
        with open('/tmp/bittrading_corp.log') as f:
            lines = f.readlines()[-15:]
            for line in lines:
                if "INFO" in line and any(k in line for k in ['SISTEMA', 'Agentes', 'MessageBus', '✓']):
                    print(f"   {line.strip()}")
    except Exception as e:
        print(f"   Error leyendo logs: {e}")
    
    print()
    print("="*70)

if __name__ == "__main__":
    monitor()
