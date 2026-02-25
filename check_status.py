#!/usr/bin/env python3
"""
📊 Monitor - Bittrading Trading System
"""

import subprocess
from datetime import datetime

def check_status():
    print("="*70)
    print("🏢 BITTRADING-CORP - TRADING SYSTEM MONITOR")
    print("="*70)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S MST')}")
    print()
    
    # Check process
    result = subprocess.run(['pgrep', '-af', 'python main.py'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ SISTEMA: OPERATIVO")
        for line in result.stdout.strip().split('\n'):
            if 'main.py' in line:
                parts = line.split()
                print(f"   PID: {parts[0]}")
    else:
        print("❌ SISTEMA: DETENIDO")
        print()
        print("Últimos errores:")
        try:
            with open('/tmp/bittrading_corp.log') as f:
                lines = f.readlines()[-20:]
                for line in lines:
                    if "ERROR" in line or "Traceback" in line:
                        print(f"   {line.strip()}")
        except:
            pass
        return
    
    print()
    print("📊 Últimas Actividades:")
    print("-"*70)
    try:
        with open('/tmp/bittrading_corp.log') as f:
            lines = f.readlines()[-15:]
            for line in lines:
                if "INFO" in line and any(k in line for k in ['Cycle', 'Portfolio', 'Position', 'BITTRADING']):
                    print(f"   {line.strip()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    print("="*70)

if __name__ == "__main__":
    check_status()
