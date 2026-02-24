import argparse
import logging
import sys
from rich.console import Console
from rich.logging import RichHandler
from .scanner import WSDiscoveryScanner, IPRangeScanner
from .inspector import CameraInspector
from .output import print_summary_table, export_to_json
from .utils import get_network_interfaces
from .models import CameraInfo

def main():
    parser = argparse.ArgumentParser(description="ONVIF Network Camera Scanner")

    parser.add_argument("--mode", choices=["ws-discovery", "ip-range"], default="ws-discovery", help="Discovery mode")
    parser.add_argument("--subnet", help="CIDR subnet for IP range scanning (e.g., 192.168.1.0/24)")
    parser.add_argument("--user", required=True, help="Camera username")
    parser.add_argument("--password", required=True, help="Camera password")
    parser.add_argument("--output", default="cameras.json", help="Output JSON file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
    logger = logging.getLogger("onvif_scanner")

    console = Console()

    found_ips = []

    if args.mode == "ws-discovery":
        console.print("[bold blue]Starting WS-Discovery...[/bold blue]")
        scanner = WSDiscoveryScanner()
        interfaces = get_network_interfaces()
        logger.info(f"Scanning on interfaces: {interfaces}")
        found_ips = scanner.discover(interfaces=interfaces)
    else:
        if not args.subnet:
            console.print("[bold red]Error: --subnet is required for ip-range mode[/bold red]")
            sys.exit(1)

        console.print(f"[bold blue]Starting IP Range Scan on {args.subnet}...[/bold blue]")
        scanner = IPRangeScanner(args.subnet)
        found_ips = scanner.scan()

    console.print(f"[green]Found {len(found_ips)} devices.[/green]")

    results = []
    with console.status("[bold green]Inspecting cameras...") as status:
        for ip in found_ips:
            logger.info(f"Inspecting {ip}...")
            inspector = CameraInspector(ip, args.user, args.password)
            try:
                cam_info = inspector.get_device_info()
                cam_info.profiles = inspector.get_profiles()
                cam_info.ptz = inspector.get_ptz_status()
                results.append(cam_info)
            except Exception as e:
                logger.error(f"Error inspecting {ip}: {e}")

    print_summary_table(results)
    export_to_json(results, args.output)

if __name__ == "__main__":
    main()
