#!/usr/bin/env python3
"""
📊 Monitor para Bittrading-Corp
"""

import json
import time
from pathlib import Path
from datetime import datetime

STATE_FILE = Path("/home/enderj/.openclaw/workspace/Bittrading-Corp/logs/system.log")

def get_status():
    """Obtener estado del sistema"""
    
    print("="*70)
    print("🏢 BITTRADING-CORP - MONITOR DE ESTADO")
    print("="*70)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S MST')}")
    print()
    
    # Verificar proceso
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'python main.py'], capture_output=True, text=True)
    if result.returncode == 0:
        pid = result.stdout.strip()
        print("✅ SISTEMA: OPERATIVO")
        print(f"   PID: {pid}")
    else:
        print("❌ SISTEMA: DETENIDO")
        return
    
    print()
    print("🤖 AGENTES")
    print("-"*70)
    
    # Leer últimos logs
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            lines = f.readlines()[-10:]
            for line in lines:
                if "INFO" in line:
                    print(f"   {line.strip()}")
    
    print()
    print("="*70)

if __name__ == "__main__":
    get_status()
