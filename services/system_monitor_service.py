from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SystemStatus:
    cpu_percent: float
    ram_percent: float
    ram_used_mb: int
    ram_total_mb: int
    disk_percent: float
    disk_used_gb: int
    disk_total_gb: int
    battery_percent: float | None
    battery_plugged: bool | None


class SystemMonitorService:
    def __init__(self) -> None:
        try:
            import psutil  # type: ignore
        except Exception as exc:
            raise RuntimeError("psutil is required for SystemMonitorService") from exc

        self._psutil = psutil

    def get_status(self) -> Dict[str, Any]:
        psutil = self._psutil

        cpu_percent = float(psutil.cpu_percent(interval=0.15))

        vm = psutil.virtual_memory()
        ram_percent = float(vm.percent)
        ram_used_mb = int(vm.used / (1024 * 1024))
        ram_total_mb = int(vm.total / (1024 * 1024))

        du = psutil.disk_usage("/")
        disk_percent = float(du.percent)
        disk_used_gb = int(du.used / (1024 * 1024 * 1024))
        disk_total_gb = int(du.total / (1024 * 1024 * 1024))

        battery_percent: float | None = None
        battery_plugged: bool | None = None
        try:
            batt = psutil.sensors_battery()
            if batt is not None:
                battery_percent = None if batt.percent is None else float(batt.percent)
                battery_plugged = None if batt.power_plugged is None else bool(batt.power_plugged)
        except Exception:
            pass

        status = SystemStatus(
            cpu_percent=cpu_percent,
            ram_percent=ram_percent,
            ram_used_mb=ram_used_mb,
            ram_total_mb=ram_total_mb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            battery_percent=battery_percent,
            battery_plugged=battery_plugged,
        )

        return {
            "cpu": {"percent": status.cpu_percent},
            "ram": {
                "percent": status.ram_percent,
                "used_mb": status.ram_used_mb,
                "total_mb": status.ram_total_mb,
            },
            "disk": {
                "percent": status.disk_percent,
                "used_gb": status.disk_used_gb,
                "total_gb": status.disk_total_gb,
            },
            "battery": {
                "percent": status.battery_percent,
                "plugged": status.battery_plugged,
            },
        }
