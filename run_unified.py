#!/usr/bin/env python3
"""
🚀 UNIFIED LAUNCHER - Sistema Completo
======================================
Inicia tanto el Coordinator legacy como el nuevo sistema de agentes.

Usage:
    python run_unified.py --all           # Ejecutar todo
    python run_unified.py --coordinator    # Solo coordinator
    python run_unified.py --agents        # Solo agentes
    python run_unified.py --workers       # Solo workers
    python run_unified.py --status        # Ver estado

Author: Bittrading Trading Corp
Version: 1.0.0
"""

import asyncio
import subprocess
import sys
import os
import time
import signal
from datetime import datetime
from typing import Dict, List, Optional
import requests

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

COORDINATOR_PATH = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
AGENTS_PATH = "/Users/enderj/Bittrading_Trading_Corp"
COORDINATOR_URL = "http://localhost:5000"

# ═══════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

class UnifiedLauncher:
    """
    Launcher unificado para ejecutar todo el sistema.
    """
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        
        # Colores para output
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.RED = '\033[91m'
        self.BLUE = '\033[94m'
        self.ENDC = '\033[0m'
    
    def print_status(self, msg: str, color: str = "GREEN"):
        """Print con colores"""
        color_code = getattr(self, color.upper(), self.GREEN)
        print(f"{color_code}[{datetime.now().strftime('%H:%M:%S')}] {msg}{self.ENDC}")
    
    # ═══════════════════════════════════════════════════════════════
    # GESTIÓN DE PROCESOS
    # ═══════════════════════════════════════════════════════════════
    
    def start_coordinator(self) -> bool:
        """Iniciar el Coordinator legacy"""
        self.print_status("🚀 Iniciando Coordinator legacy...", "BLUE")
        
        try:
            # Cambiar al directorio del coordinator
            os.chdir(COORDINATOR_PATH)
            
            # Iniciar coordinator
            proc = subprocess.Popen(
                [sys.executable, "coordinator.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.processes["coordinator"] = proc
            
            # Esperar a que esté listo
            time.sleep(3)
            
            # Verificar
            if self._wait_for_coordinator(30):
                self.print_status("✅ Coordinator ejecutándose", "GREEN")
                return True
            else:
                self.print_status("❌ Coordinator no respondió", "RED")
                return False
                
        except Exception as e:
            self.print_status(f"❌ Error iniciando Coordinator: {e}", "RED")
            return False
    
    def start_agents(self) -> bool:
        """Iniciar el nuevo sistema de agentes"""
        self.print_status("🚀 Iniciando sistema de agentes...", "BLUE")
        
        try:
            # Cambiar al directorio de agentes
            os.chdir(AGENTS_PATH)
            
            # Iniciar agentes
            proc = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.processes["agents"] = proc
            
            # Esperar un momento
            time.sleep(5)
            
            self.print_status("✅ Sistema de agentes iniciándose...", "GREEN")
            return True
                
        except Exception as e:
            self.print_status(f"❌ Error iniciando agentes: {e}", "RED")
            return False
    
    def start_workers(self) -> bool:
        """Iniciar workers legacy"""
        self.print_status("🚀 Verificando workers...", "BLUE")
        
        # Los workers se inician separadamente
        # Este método es placeholder para futuras mejoras
        
        workers = self._get_workers_from_coordinator()
        self.print_status(f"📊 Workers activos: {len(workers)}", "YELLOW")
        
        return True
    
    def stop_all(self):
        """Detener todos los procesos"""
        self.print_status("🛑 Deteniendo todos los procesos...", "RED")
        
        for name, proc in self.processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                self.print_status(f"✅ {name} detenido", "GREEN")
            except Exception as e:
                self.print_status(f"⚠️ Error deteniendo {name}: {e}", "YELLOW")
                proc.kill()
        
        self.processes.clear()
        self.running = False
    
    def _wait_for_coordinator(self, timeout: int = 30) -> bool:
        """Esperar a que el Coordinator esté listo"""
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                resp = requests.get(f"{COORDINATOR_URL}/api/status", timeout=2)
                if resp.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # CONSULTA DE ESTADO
    # ═══════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict:
        """Obtener estado del sistema"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "coordinator": {"running": False, "url": COORDINATOR_URL},
            "agents": {"running": False},
            "workers": {"count": 0}
        }
        
        # Verificar coordinator
        try:
            resp = requests.get(f"{COORDINATOR_URL}/api/status", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                status["coordinator"]["running"] = True
                status["coordinator"]["work_units"] = data.get("work_units", {})
                status["workers"]["count"] = data.get("workers", {}).get("active", 0)
        except:
            pass
        
        # Verificar agentes (si proceso está ejecutándose)
        if "agents" in self.processes:
            poll = self.processes["agents"].poll()
            status["agents"]["running"] = poll is None
        
        return status
    
    def _get_workers_from_coordinator(self) -> List[Dict]:
        """Obtener lista de workers del Coordinator"""
        try:
            resp = requests.get(f"{COORDINATOR_URL}/api/workers", timeout=2)
            if resp.status_code == 200:
                return resp.json().get("workers", [])
        except:
            pass
        return []
    
    def print_dashboard(self):
        """Mostrar dashboard del sistema"""
        status = self.get_status()
        
        print("\n" + "="*60)
        print("🏢 OPENCLAW TRADING CORP - DASHBOARD")
        print("="*60)
        
        # Coordinator
        if status["coordinator"]["running"]:
            print(f"✅ Coordinator: {COORDINATOR_URL}")
            wu = status["coordinator"]["work_units"]
            print(f"   📦 Work Units: {wu.get('total', 0)} | ✅ {wu.get('completed', 0)} | ⏳ {wu.get('pending', 0)}")
        else:
            print(f"❌ Coordinator: NO EJECUTANDO")
        
        # Workers
        workers = status["workers"]["count"]
        if workers > 0:
            print(f"✅ Workers activos: {workers}")
        else:
            print(f"⚠️ Workers activos: 0")
        
        # Agents
        if status["agents"]["running"]:
            print(f"✅ Sistema de agentes: EJECUTANDO")
        else:
            print(f"⚠️ Sistema de agentes: NO EJECUTANDO")
        
        print("="*60 + "\n")
    
    # ═══════════════════════════════════════════════════════════════
    # MONITOREO
    # ═══════════════════════════════════════════════════════════════
    
    async def monitor_loop(self):
        """Loop de monitoreo"""
        self.running = True
        
        while self.running:
            try:
                # Verificar procesos
                for name, proc in self.processes.items():
                    poll = proc.poll()
                    if poll is not None:
                        self.print_status(f"⚠️ {name} terminó con código: {poll}", "YELLOW")
                
                # Mostrar dashboard cada 10 segundos
                self.print_dashboard()
                
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.print_status(f"Error en monitor: {e}", "RED")
                await asyncio.sleep(5)
    
    # ═══════════════════════════════════════════════════════════════
    # SEÑALES
    # ═══════════════════════════════════════════════════════════════
    
    def setup_signal_handlers(self):
        """Configurar handlers de señales"""
        def shutdown_handler(sig, frame):
            self.print_status("🛑 Señal de shutdown recibida", "RED")
            self.stop_all()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)


# ═══════════════════════════════════════════════════════════════════
# FUNCIONES DE COMANDOS
# ═══════════════════════════════════════════════════════════════════

def cmd_status():
    """Mostrar estado del sistema"""
    launcher = UnifiedLauncher()
    launcher.print_dashboard()
    
    status = launcher.get_status()
    print("\n📋 Workers Registrados:")
    workers = launcher._get_workers_from_coordinator()
    
    if workers:
        for w in workers[:10]:  # Mostrar top 10
            print(f"   • {w.get('id', 'Unknown')[:20]}... | {w.get('work_units_completed', 0)} WUs | {w.get('hostname', 'Unknown')}")
    else:
        print("   No hay workers registrados")
    
    if len(workers) > 10:
        print(f"   ... y {len(workers) - 10} más")


def cmd_coordinator():
    """Iniciar solo coordinator"""
    launcher = UnifiedLauncher()
    
    if not launcher.start_coordinator():
        sys.exit(1)
    
    try:
        asyncio.run(launcher.monitor_loop())
    except KeyboardInterrupt:
        launcher.stop_all()


def cmd_agents():
    """Iniciar solo agentes"""
    launcher = UnifiedLauncher()
    
    if not launcher.start_agents():
        sys.exit(1)
    
    try:
        asyncio.run(launcher.monitor_loop())
    except KeyboardInterrupt:
        launcher.stop_all()


def cmd_all():
    """Iniciar todo el sistema"""
    launcher = UnifiedLauncher()
    launcher.setup_signal_handlers()
    
    print("\n" + "="*60)
    print("🚀 INICIANDO SISTEMA COMPLETO")
    print("="*60 + "\n")
    
    # 1. Iniciar Coordinator
    if not launcher.start_coordinator():
        print("❌ Error: Coordinator no pudo iniciar")
        sys.exit(1)
    
    # 2. Iniciar Workers (se inician manualmente o vía script)
    launcher.start_workers()
    
    # 3. Iniciar Agentes
    if not launcher.start_agents():
        print("❌ Error: Agentes no pudieron iniciar")
        launcher.stop_all()
        sys.exit(1)
    
    # 4. Monitorear
    try:
        asyncio.run(launcher.monitor_loop())
    except KeyboardInterrupt:
        launcher.stop_all()


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    """Punto de entrada"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python run_unified.py --all           # Ejecutar todo el sistema")
        print("  python run_unified.py --coordinator  # Solo coordinator")
        print("  python run_unified.py --agents        # Solo agentes")
        print("  python run_unified.py --status        # Ver estado")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "--all":
        cmd_all()
    elif command == "--coordinator":
        cmd_coordinator()
    elif command == "--agents":
        cmd_agents()
    elif command == "--workers":
        launcher = UnifiedLauncher()
        launcher.start_workers()
    elif command == "--status":
        cmd_status()
    else:
        print(f"Comando desconocido: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
