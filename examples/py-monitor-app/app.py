"""
Python monitoring application that connects to Grandmaster.
Collects and reports system metrics.
"""

import asyncio
import json
import logging
import os
import platform
import psutil
import time
from datetime import datetime
from grandmaster_client import GrandmasterClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("monitor-app")

# Configuration
METRICS_INTERVAL = 5  # Collect metrics every 5 seconds
REPORT_INTERVAL = 30  # Send detailed report every 30 seconds
MAX_HISTORY = 100     # Maximum number of metrics to keep in history
ALERT_THRESHOLDS = {
    "cpu_percent": 80.0,
    "memory_percent": 85.0,
    "disk_percent": 90.0
}

class MonitoringApp:
    """Main monitoring application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.start_time = time.time()
        self.metrics_history = []
        self.active_alerts = set()
        self.last_report_time = 0
        
        # Initialize Grandmaster client
        self.client = GrandmasterClient(
            url=os.environ.get("GRANDMASTER_URL"),
            app_name=os.environ.get("APP_NAME", "py-monitor-app"),
            on_connect=self.on_connect,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            reconnect_interval=5.0,
            max_reconnect_attempts=20
        )
    
    async def on_connect(self):
        """Called when connected to Grandmaster."""
        logger.info("Connected to Grandmaster")
        
        # Send system information
        await self.send_system_info()
        
        # Start monitoring loop
        asyncio.create_task(self.metrics_loop())
    
    async def on_message(self, message):
        """Handle messages from Grandmaster."""
        logger.info(f"Received: {message}")
        
        # Check if this is a command message
        if isinstance(message, dict) and "command" in message:
            await self.handle_command(message)
    
    async def handle_command(self, message):
        """Handle command messages from Grandmaster."""
        command = message["command"]
        
        if command == "get_metrics":
            # Send immediate metrics report
            await self.send_current_metrics()
        
        elif command == "get_history":
            # Send metrics history
            count = int(message.get("count", 10))
            await self.client.send("Metrics History", {
                "type": "metrics_history",
                "data": self.metrics_history[-count:],
                "count": min(count, len(self.metrics_history))
            })
        
        elif command == "set_threshold":
            # Update alert thresholds
            if "thresholds" in message:
                global ALERT_THRESHOLDS
                ALERT_THRESHOLDS.update(message["thresholds"])
                logger.info(f"Updated thresholds: {ALERT_THRESHOLDS}")
                await self.client.send("Thresholds Updated", {
                    "success": True,
                    "thresholds": ALERT_THRESHOLDS
                })
        
        elif command == "restart":
            # Simulate restart
            logger.info("Restart command received")
            await self.client.send("Restarting", {"status": "restarting"})
            # In a real app, you might do:
            # os._exit(0)  # Exit and let Docker restart the container
    
    def on_error(self, error):
        """Handle connection errors."""
        logger.error(f"Connection error: {error}")
    
    def on_close(self):
        """Handle connection closure."""
        logger.info("Connection closed")
    
    async def send_system_info(self):
        """Send system information to Grandmaster."""
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
            "disk_total_gb": round(psutil.disk_usage('/').total / (1024 ** 3), 2),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
        
        await self.client.send("System Information", {
            "type": "system_info",
            "data": info
        })
        logger.info("System information sent")
    
    async def metrics_loop(self):
        """Main metrics collection and reporting loop."""
        logger.info("Starting metrics collection")
        
        while self.client.connected:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                
                # Store in history
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > MAX_HISTORY:
                    self.metrics_history = self.metrics_history[-MAX_HISTORY:]
                
                # Check for alerts
                await self.check_alerts(metrics)
                
                # Send periodic detailed report
                current_time = time.time()
                if current_time - self.last_report_time >= REPORT_INTERVAL:
                    await self.send_metrics_report()
                    self.last_report_time = current_time
                
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}", exc_info=True)
            
            # Wait for next collection interval
            await asyncio.sleep(METRICS_INTERVAL)
    
    def collect_metrics(self):
        """Collect current system metrics."""
        # Get basic metrics
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network metrics
        net = psutil.net_io_counters()
        
        # Get process count
        process_count = len(psutil.pids())
        
        # Build metrics object
        return {
            "timestamp": time.time(),
            "isotime": datetime.now().isoformat(),
            "cpu_percent": cpu,
            "memory": {
                "percent": memory.percent,
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2)
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2)
            },
            "network": {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv
            },
            "processes": process_count,
            "uptime_seconds": time.time() - self.start_time
        }
    
    async def check_alerts(self, metrics):
        """Check metrics against thresholds and send alerts if needed."""
        new_alerts = set()
        
        # CPU alert
        if metrics["cpu_percent"] > ALERT_THRESHOLDS["cpu_percent"]:
            alert_id = f"cpu_high"
            new_alerts.add(alert_id)
            if alert_id not in self.active_alerts:
                await self.client.send("🚨 ALERT: High CPU Usage", {
                    "type": "alert",
                    "alert_id": alert_id,
                    "severity": "warning",
                    "value": metrics["cpu_percent"],
                    "threshold": ALERT_THRESHOLDS["cpu_percent"]
                })
                self.active_alerts.add(alert_id)
        
        # Memory alert
        if metrics["memory"]["percent"] > ALERT_THRESHOLDS["memory_percent"]:
            alert_id = f"memory_high"
            new_alerts.add(alert_id)
            if alert_id not in self.active_alerts:
                await self.client.send("🚨 ALERT: High Memory Usage", {
                    "type": "alert",
                    "alert_id": alert_id,
                    "severity": "warning",
                    "value": metrics["memory"]["percent"],
                    "threshold": ALERT_THRESHOLDS["memory_percent"]
                })
                self.active_alerts.add(alert_id)
        
        # Disk alert
        if metrics["disk"]["percent"] > ALERT_THRESHOLDS["disk_percent"]:
            alert_id = f"disk_high"
            new_alerts.add(alert_id)
            if alert_id not in self.active_alerts:
                await self.client.send("🚨 ALERT: High Disk Usage", {
                    "type": "alert",
                    "alert_id": alert_id,
                    "severity": "warning",
                    "value": metrics["disk"]["percent"],
                    "threshold": ALERT_THRESHOLDS["disk_percent"]
                })
                self.active_alerts.add(alert_id)
        
        # Clear resolved alerts
        resolved_alerts = self.active_alerts - new_alerts
        for alert_id in resolved_alerts:
            await self.client.send("✅ RESOLVED: Alert cleared", {
                "type": "alert_resolved",
                "alert_id": alert_id
            })
            self.active_alerts.remove(alert_id)
    
    async def send_current_metrics(self):
        """Send current metrics immediately."""
        metrics = self.collect_metrics()
        await self.client.send("Current Metrics", {
            "type": "metrics",
            "data": metrics
        })
        logger.info("Sent immediate metrics")
    
    async def send_metrics_report(self):
        """Send a detailed metrics report."""
        if not self.metrics_history:
            return
        
        # Get current metrics
        current = self.metrics_history[-1]
        
        # Calculate averages from recent history
        recent = self.metrics_history[-6:]  # Last 30 seconds (assuming 5-second intervals)
        avg_cpu = sum(m["cpu_percent"] for m in recent) / len(recent)
        avg_memory = sum(m["memory"]["percent"] for m in recent) / len(recent)
        
        # Send report
        await self.client.send("System Metrics Report", {
            "type": "metrics_report",
            "current": current,
            "averages": {
                "cpu_percent": round(avg_cpu, 1),
                "memory_percent": round(avg_memory, 1),
                "measurement_period_seconds": len(recent) * METRICS_INTERVAL
            },
            "system_status": "healthy" if not self.active_alerts else "warning"
        })
        logger.info(f"Sent metrics report. CPU: {current['cpu_percent']}%, Memory: {current['memory']['percent']}%")
    
    def start(self):
        """Start the monitoring application."""
        logger.info("Starting monitoring application")
        try:
            self.client.start()
        except KeyboardInterrupt:
            logger.info("Application interrupted")
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
        finally:
            logger.info("Application shutdown")

if __name__ == "__main__":
    app = MonitoringApp()
    app.start()