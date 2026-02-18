
import psutil
from typing import Optional, Dict


def get_battery_info() -> Optional[Dict[str, object]]:
    """
    Returns battery info as a dict with keys 'percent' and 'charging', or None if not available.
    Suppresses Pylance unknown type warnings for psutil.sensors_battery().
    """
    battery: object = psutil.sensors_battery()  # type: ignore
    if battery:
        percent = getattr(battery, 'percent', None)  # type: ignore
        charging = getattr(battery, 'power_plugged', None)  # type: ignore
        return {
            'percent': percent,
            'charging': charging
        }
    return None
