"""
📊 DASHBOARD INTEGRATION - Dashboards del Sistema
=================================================
Este módulo mantiene los dashboards legacy del Coordinator
y los integra con el nuevo sistema de agentes.

Dashboards disponibles:
- Status del sistema
- Workers activos
- Resultados de backtests
- Gráficos en tiempo real
- Métricas de performance

Author: OpenClaw Trading Corp
Version: 2.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict
import json

from workers_integration.complete_coordinator_bridge import CoordinatorClient


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD DATA CLASSES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DashboardConfig:
    """Configuración del dashboard"""
    refresh_interval: int = 5  # Segundos
    max_history_points: int = 100  # Puntos de histórico
    auto_refresh: bool = True
    theme: str = "dark"


@dataclass
class DashboardMetrics:
    """Métricas del dashboard"""
    timestamp: datetime
    work_units: Dict[str, int]
    workers: Dict[str, Any]
    performance: Dict[str, float]
    system: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD SERVICE
# ═══════════════════════════════════════════════════════════════════

class DashboardService:
    """
    Servicio central de dashboards.
    
    Mantiene los dashboards legacy funcionando y añade
    nuevas funcionalidades para el sistema de agentes.
    """
    
    def __init__(self, coordinator_url: str = "http://localhost:5000"):
        self.logger = logging.getLogger("DashboardService")
        self.coordinator = CoordinatorClient(
            CoordinatorConfig(coordinator_url=coordinator_url)
        )
        
        # Configuración
        self.config = DashboardConfig()
        
        # Histórico de métricas
        self._metrics_history: List[DashboardMetrics] = []
        
        # Callbacks de actualización
        self._update_callbacks: List[Callable[[DashboardMetrics], None]] = []
        
        # Estado en tiempo real
        self._latest_metrics: Optional[DashboardMetrics] = None
        
        # Contadores
        self._total_results = 0
        self._positive_results = 0
        self._total_compute_time = 0.0
        
        self.logger.info("📊 Dashboard Service inicializado")
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTRICAS PRINCIPALES
    # ═══════════════════════════════════════════════════════════════
    
    async def get_full_metrics(self) -> DashboardMetrics:
        """
        Obtener métricas completas del sistema.
        
        Esta función replica y mejora la API /api/dashboard_stats
        """
        stats = await self.coordinator.get_system_stats()
        
        if not stats:
            return DashboardMetrics(
                timestamp=datetime.now(),
                work_units={"total": 0, "completed": 0, "pending": 0},
                workers={"active": 0, "total": 0},
                performance={},
                system={"healthy": False}
            )
        
        # Extraer métricas
        wu = stats.get("work_units", {})
        workers_stats = stats.get("workers", {})
        perf = stats.get("performance", {})
        
        # Calcular métricas derivadas
        total_results = perf.get("total_results", 0)
        positive = perf.get("positive_pnl_count", 0)
        compute_time = perf.get("total_compute_time", 0)
        
        # Actualizar counters
        if total_results > self._total_results:
            self._total_results = total_results
            self._positive_results = positive
            self._total_compute_time = compute_time
        
        # Crear métricas
        metrics = DashboardMetrics(
            timestamp=datetime.now(),
            work_units={
                "total": wu.get("total", 0),
                "completed": wu.get("completed", 0),
                "pending": wu.get("pending", 0),
                "in_progress": wu.get("in_progress", 0)
            },
            workers={
                "active": workers_stats.get("active", 0),
                "total": workers_stats.get("total_registered", 0)
            },
            performance={
                "total_results": self._total_results,
                "positive_results": self._positive_results,
                "avg_pnl": perf.get("avg_pnl", 0),
                "results_per_hour": perf.get("results_per_hour", 0),
                "avg_execution_time": perf.get("avg_execution_time", 0),
                "total_compute_time": self._total_compute_time,
                "success_rate": (
                    self._positive_results / self._total_results * 100 
                    if self._total_results > 0 else 0
                )
            },
            system={
                "healthy": True,
                "coordinator_url": self.coordinator.url,
                "uptime_seconds": (datetime.now() - datetime.now()).total_seconds()
            }
        )
        
        # Guardar en histórico
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self.config.max_history_points:
            self._metrics_history = self._metrics_history[-self.config.max_history_points:]
        
        # Actualizar latest
        self._latest_metrics = metrics
        
        # Notificar callbacks
        for callback in self._update_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                self.logger.warning(f"Callback error: {e}")
        
        return metrics
    
    # ═══════════════════════════════════════════════════════════════
    # WORKERS
    # ═══════════════════════════════════════════════════════════════
    
    async def get_workers_metrics(self) -> Dict[str, Any]:
        """Métricas de workers"""
        workers = await self.coordinator.api_workers()
        
        now = datetime.now()
        active = []
        inactive = []
        
        for w in workers:
            last_seen = datetime.fromtimestamp(w.get("last_seen", 0))
            mins_ago = (now - last_seen).total_seconds() / 60
            
            worker_data = {
                "id": w.get("id", "")[:20],
                "hostname": w.get("hostname", "Unknown"),
                "completed": w.get("work_units_completed", 0),
                "total_time": round(w.get("total_execution_time", 0), 2),
                "last_seen": mins_ago,
                "status": "active" if mins_ago < 30 else "inactive"
            }
            
            if mins_ago < 30:
                active.append(worker_data)
            else:
                inactive.append(worker_data)
        
        return {
            "active": active,
            "inactive": inactive,
            "active_count": len(active),
            "total_count": len(workers),
            "top_performers": sorted(active, key=lambda x: x["completed"], reverse=True)[:5]
        }
    
    # ═══════════════════════════════════════════════════════════════
    # RESULTADOS
    # ═══════════════════════════════════════════════════════════════
    
    async def get_results_metrics(self, limit: int = 20) -> Dict[str, Any]:
        """Métricas de resultados"""
        results = await self.coordinator.api_results(limit)
        
        # Calcular estadísticas
        pnls = [r.get("pnl", 0) for r in results]
        trades = [r.get("trades", 0) for r in results]
        win_rates = [r.get("win_rate", 0) for r in results]
        
        return {
            "results": results[:limit],
            "count": len(results),
            "stats": {
                "best_pnl": max(pnls) if pnls else 0,
                "worst_pnl": min(pnls) if pnls else 0,
                "avg_pnl": sum(pnls) / len(pnls) if pnls else 0,
                "avg_trades": sum(trades) / len(trades) if trades else 0,
                "avg_win_rate": sum(win_rates) / len(win_rates) if win_rates else 0
            },
            "best_result": results[0] if results else None
        }
    
    # ═══════════════════════════════════════════════════════════════
    # TIMELINE & CHARTS
    # ═══════════════════════════════════════════════════════════════
    
    async def get_timeline_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Obtener timeline de métricas"""
        # Usar el histórico interno
        cutoff = datetime.now() - timedelta(hours=hours)
        history = [m for m in self._metrics_history if m.timestamp > cutoff]
        
        # PnL timeline
        pnl_timeline = []
        for m in history:
            pnl_timeline.append({
                "timestamp": m.timestamp.isoformat(),
                "total_completed": m.work_units.get("completed", 0)
            })
        
        # Completion timeline
        completion_timeline = []
        completed_count = 0
        for m in history:
            completed_count = m.work_units.get("completed", 0)
            completion_timeline.append({
                "timestamp": m.timestamp.isoformat(),
                "completed": completed_count
            })
        
        return {
            "pnl_timeline": pnl_timeline,
            "completion_timeline": completion_timeline,
            "data_points": len(history),
            "period_hours": hours
        }
    
    # ═══════════════════════════════════════════════════════════════
    # CALLBACKS & SUBSCRIPTIONS
    # ═══════════════════════════════════════════════════════════════
    
    def subscribe(self, callback: Callable[[DashboardMetrics], None]):
        """Suscribirse a updates del dashboard"""
        self._update_callbacks.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Desuscribirse"""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
    
    # ═══════════════════════════════════════════════════════════════
    # DASHBOARD HTML LEGACY (REPLICADO)
    # ═══════════════════════════════════════════════════════════════
    
    def get_legacy_dashboard_html(self) -> str:
        """
        Generar HTML del dashboard legacy (compatible con coordinator.py).
        
        Este HTML es 100% compatible con el dashboard original.
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <title>OpenClaw Trading Corp - Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="10">
    <style>
        body {
            font-family: 'Monaco', 'Courier New', monospace;
            background: #1a1a1a;
            color: #0f0;
            padding: 20px;
        }
        h1 {
            text-align: center;
            border-bottom: 2px solid #0f0;
            padding-bottom: 10px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-box {
            background: #0a0a0a;
            border: 2px solid #0f0;
            padding: 20px;
            text-align: center;
        }
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #0f0;
        }
        .stat-label {
            font-size: 14px;
            color: #0f0;
            opacity: 0.7;
            margin-top: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #0f0;
            padding: 10px;
            text-align: left;
        }
        th {
            background: #0f0;
            color: #000;
        }
        .timestamp {
            text-align: center;
            margin-top: 20px;
            opacity: 0.5;
        }
        .agent-status {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }
        .agent-box {
            background: #0a0a0a;
            border: 1px solid #0f0;
            padding: 10px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏢 OPENCLAW TRADING CORP - DASHBOARD</h1>
        
        <!-- Work Units Stats -->
        <div class="stats" id="wu-stats">
            <div class="stat-box">
                <div class="stat-value" id="wu-total">-</div>
                <div class="stat-label">Total Work Units</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="wu-completed">-</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="wu-pending">-</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="wu-workers">-</div>
                <div class="stat-label">Active Workers</div>
            </div>
        </div>
        
        <!-- Agent Status -->
        <h2>🤖 Agent Status</h2>
        <div class="agent-status" id="agent-status">
            <!-- Populated by JavaScript -->
        </div>
        
        <!-- Workers Table -->
        <h2>👷 Workers</h2>
        <table id="workers-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Hostname</th>
                    <th>Completed</th>
                    <th>Last Seen</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="workers-body">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
        
        <!-- Results Table -->
        <h2>📈 Top Results</h2>
        <table id="results-table">
            <thead>
                <tr>
                    <th>Work ID</th>
                    <th>PnL</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>Worker</th>
                </tr>
            </thead>
            <tbody id="results-body">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
        
        <div class="timestamp" id="timestamp">Last update: -</div>
    </div>
    
    <script>
        const API_URL = '/api';
        
        async function updateDashboard() {
            try {
                // Get dashboard stats
                const statsResp = await fetch(API_URL + '/dashboard_stats');
                const stats = await statsResp.json();
                
                // Update WU stats
                const wu = stats.work_units || {};
                document.getElementById('wu-total').textContent = wu.total || 0;
                document.getElementById('wu-completed').textContent = wu.completed || 0;
                document.getElementById('wu-pending').textContent = wu.pending || 0;
                document.getElementById('wu-workers').textContent = stats.workers?.active || 0;
                
                // Update workers table
                const workersResp = await fetch(API_URL + '/workers');
                const workersData = await workersResp.json();
                updateWorkersTable(workersData.workers || []);
                
                // Update results table
                const resultsResp = await fetch(API_URL + '/results?limit=10');
                const resultsData = await resultsResp.json();
                updateResultsTable(resultsData.results || []);
                
                // Update timestamp
                document.getElementById('timestamp').textContent = 
                    'Last update: ' + new Date().toLocaleTimeString();
                
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }
        
        function updateWorkersTable(workers) {
            const tbody = document.getElementById('workers-body');
            tbody.innerHTML = '';
            
            if (workers.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No workers</td></tr>';
                return;
            }
            
            workers.slice(0, 20).forEach(w => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = (w.id || '').substring(0, 15);
                row.insertCell(1).textContent = (w.hostname || 'Unknown').substring(0, 20);
                row.insertCell(2).textContent = w.work_units_completed || 0;
                
                const lastSeen = new Date((w.last_seen || 0) * 1000);
                row.insertCell(3).textContent = lastSeen.toLocaleTimeString();
                
                const status = w.status || 'unknown';
                row.insertCell(4).textContent = status;
                row.insertCell(4).style.color = status === 'active' ? '#0f0' : '#f00';
            });
        }
        
        function updateResultsTable(results) {
            const tbody = document.getElementById('results-body');
            tbody.innerHTML = '';
            
            if (results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No results yet</td></tr>';
                return;
            }
            
            results.slice(0, 10).forEach(r => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = r.work_id || 0;
                row.insertCell(1).textContent = '$' + (r.pnl || 0).toFixed(2);
                row.insertCell(2).textContent = r.trades || 0;
                row.insertCell(3).textContent = ((r.win_rate || 0) * 100).toFixed(1) + '%';
                row.insertCell(4).textContent = (r.worker_id || 'Unknown').substring(0, 15);
            });
        }
        
        // Update every 10 seconds
        setInterval(updateDashboard, 10000);
        updateDashboard();
    </script>
</body>
</html>
        """
    
    # ═══════════════════════════════════════════════════════════════
    # API FORMAT (PARA STREAMLET/OTROS)
    # ═══════════════════════════════════════════════════════════════
    
    def get_api_format(self) -> Dict[str, Any]:
        """
        Obtener métricas en formato API (compatible con todos los dashboards).
        """
        if not self._latest_metrics:
            return {}
        
        m = self._latest_metrics
        
        return {
            "timestamp": m.timestamp.isoformat(),
            "work_units": m.work_units,
            "workers": m.workers,
            "performance": m.performance,
            "system": m.system,
            "api_version": "2.0.0",
            "source": "OpenClaw Trading Corp"
        }
    
    def get_json_export(self) -> str:
        """Exportar todas las métricas como JSON"""
        return json.dumps(self.get_api_format(), indent=2)
    
    # ═══════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════
    
    def get_service_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio"""
        return {
            "coordinator_url": self.coordinator.url,
            "latest_update": self._latest_metrics.timestamp.isoformat() if self._latest_metrics else None,
            "history_points": len(self._metrics_history),
            "subscribers": len(self._update_callbacks),
            "client_stats": self.coordinator.get_client_stats()
        }
    
    def __repr__(self) -> str:
        stats = self.get_service_status()
        return f"<DashboardService(updates={stats['history_points']}, subscribers={stats['subscribers']})>"


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD AGENT
# ═══════════════════════════════════════════════════════════════════

class DashboardAgent(BaseAgent):
    """
    Dashboard Agent - Genera y sirve dashboards.
    
    Responsabilidades:
    - Generar HTML del dashboard
    - Servir métricas en tiempo real
    - Integrar con Streamlit/UIs
    - Mantener compatibilidad legacy
    """
    
    def __init__(self, message_bus=None, config: Optional[Dict] = None):
        dash_config = AgentConfig(
            agent_id="DASHBOARD",
            agent_name="Dashboard Generator",
            agent_type="UI",
            log_level="INFO",
            cycle_interval=60,
            custom_config=config or {}
        )
        
        super().__init__(dash_config, message_bus)
        
        # Dashboard service
        self.coordinator_url = config.get("coordinator_url", "http://localhost:5000")
        self.dashboard = DashboardService(self.coordinator_url)
        
        # Estado
        self.refresh_count = 0
        
        self.logger.info("📊 Dashboard Agent inicializado")
    
    async def on_start(self):
        """Inicializar"""
        self.logger.info("🚀 Iniciando Dashboard Agent...")
        
        if self.message_bus:
            self.message_bus.subscribe(
                self.agent_id,
                task_types=[
                    "GET_DASHBOARD_HTML",
                    "GET_DASHBOARD_JSON",
                    "GET_WORKERS_TABLE",
                    "GET_RESULTS_TABLE",
                    "REFRESH_DASHBOARD"
                ]
            )
        
        self.logger.info("✅ Dashboard Agent listo")
    
    async def run_cycle(self):
        """Actualizar métricas periódicamente"""
        await self.dashboard.get_full_metrics()
        self.refresh_count += 1
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESAMIENTO DE MENSAJES
    # ═══════════════════════════════════════════════════════════════
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar mensajes"""
        
        if message.task_type == "GET_DASHBOARD_HTML":
            return await self._handle_get_html(message)
        
        elif message.task_type == "GET_DASHBOARD_JSON":
            return await self._handle_get_json(message)
        
        elif message.task_type == "GET_WORKERS_TABLE":
            return await self._handle_get_workers(message)
        
        elif message.task_type == "GET_RESULTS_TABLE":
            return await self._handle_get_results(message)
        
        elif message.task_type == "REFRESH_DASHBOARD":
            return await self._handle_refresh(message)
        
        return None
    
    async def _handle_get_html(self, message: AgentMessage) -> AgentMessage:
        """Obtener HTML del dashboard"""
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "html": self.dashboard.get_legacy_dashboard_html(),
                "type": "legacy_dashboard"
            }
        )
    
    async def _handle_get_json(self, message: AgentMessage) -> AgentMessage:
        """Obtener métricas en JSON"""
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result=self.dashboard.get_api_format()
        )
    
    async def _handle_get_workers(self, message: AgentMessage) -> AgentMessage:
        """Obtener tabla de workers"""
        workers = await self.dashboard.get_workers_metrics()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result=workers
        )
    
    async def _handle_get_results(self, message: AgentMessage) -> AgentMessage:
        """Obtener tabla de resultados"""
        results = await self.dashboard.get_results_metrics(
            limit=message.payload.get("limit", 20)
        )
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result=results
        )
    
    async def _handle_refresh(self, message: AgentMessage) -> AgentMessage:
        """Forzar refresh"""
        metrics = await self.dashboard.get_full_metrics()
        
        return self.create_result_message(
            to_agent=message.from_agent,
            original_task=message.task_type,
            result={
                "refreshed": True,
                "timestamp": metrics.timestamp.isoformat(),
                "metrics": self.dashboard.get_api_format()
            }
        )
    
    def get_dashboard_status(self) -> Dict[str, Any]:
        """Obtener estado del dashboard"""
        return {
            "refresh_count": self.refresh_count,
            "service_status": self.dashboard.get_service_status()
        }
    
    def __repr__(self) -> str:
        return f"<DashboardAgent(refreshes={self.refresh_count})>"
