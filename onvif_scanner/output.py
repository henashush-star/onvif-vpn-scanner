import json
import logging
from typing import List
from rich.console import Console
from rich.table import Table
from .models import CameraInfo
from dataclasses import asdict

logger = logging.getLogger(__name__)

def print_summary_table(cameras: List[CameraInfo]):
    console = Console()
    table = Table(title="ONVIF Camera Scan Results")

    table.add_column("IP Address", style="cyan", no_wrap=True)
    table.add_column("Manufacturer", style="magenta")
    table.add_column("Model", style="green")
    table.add_column("PTZ", style="yellow")
    table.add_column("RTSP Streams", justify="right")

    for cam in cameras:
        ptz_support = "Yes" if cam.ptz and cam.ptz.supported else "No"
        num_streams = str(len(cam.profiles))

        table.add_row(
            cam.ip,
            cam.manufacturer,
            cam.model,
            ptz_support,
            num_streams
        )

    console.print(table)

def export_to_json(cameras: List[CameraInfo], filename: str):
    try:
        data = [asdict(cam) for cam in cameras]
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Results exported to {filename}")
    except Exception as e:
        logger.error(f"Failed to export to JSON: {e}")
