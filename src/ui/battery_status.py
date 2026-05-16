
import psutil
from typing import Optional, Dict
import ctypes
import sys


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def _get_windows_power_status() -> Optional[Dict[str, object]]:
    if sys.platform != "win32":
        return None

    status = _SystemPowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):  # type: ignore[attr-defined]
        return None

    charging: Optional[bool]
    if status.ACLineStatus == 1:
        charging = True
    elif status.ACLineStatus == 0:
        charging = False
    else:
        charging = None

    percent: Optional[int]
    battery_percent = int(status.BatteryLifePercent)
    percent = battery_percent if 0 <= battery_percent <= 100 else None

    return {
        "percent": percent,
        "charging": charging,
    }


def get_battery_info() -> Optional[Dict[str, object]]:
    """
    Returns battery info as a dict with keys 'percent' and 'charging', or None if not available.
    Suppresses Pylance unknown type warnings for psutil.sensors_battery().
    """
    windows_status = _get_windows_power_status()
    battery: object = psutil.sensors_battery()  # type: ignore
    if battery:
        percent = getattr(battery, 'percent', None)  # type: ignore
        charging = getattr(battery, 'power_plugged', None)  # type: ignore
        if windows_status is not None:
            windows_percent = windows_status.get("percent")
            windows_charging = windows_status.get("charging")
            if windows_percent is not None:
                percent = windows_percent
            if windows_charging is not None:
                charging = windows_charging
        return {
            'percent': percent,
            'charging': charging
        }
    if windows_status is not None:
        return windows_status
    return None
