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

    parser.add_argument("--mode", choices=["ws-discovery", "ip-range"], default=None, help="Discovery mode")
    parser.add_argument("--subnet", help="CIDR subnet for IP range scanning (e.g., 192.168.1.0/24)")
    parser.add_argument("--user", required=False, help="Camera username")
    parser.add_argument("--password", required=False, help="Camera password")
    parser.add_argument("--output", required=False, help="Output JSON file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
    logger = logging.getLogger("onvif_scanner")

    console = Console()

    found_ips = []
    subnets = []

    if args.mode == "ws-discovery":
        console.print("[bold blue]Starting WS-Discovery...[/bold blue]")
        scanner = WSDiscoveryScanner()
        # Note: get_network_interfaces now returns subnets, so we use default discovery
        found_ips = scanner.discover()
    else:
        if args.subnet:
            subnets.append(args.subnet)
        else:
            console.print("[bold blue]Auto-detecting network subnets...[/bold blue]")
            subnets = get_network_interfaces()
            console.print(f"[bold blue]Detected subnets: {', '.join(subnets)}[/bold blue]")

        if not subnets:
            console.print("[bold red]No active subnets found. Please specify --subnet manually.[/bold red]")
            sys.exit(1)

        for subnet in subnets:
            console.print(f"[bold blue]Starting IP Range Scan on {subnet}...[/bold blue]")
            scanner = IPRangeScanner(subnet)
            found_ips.extend(scanner.scan())

    # Remove duplicates
    found_ips = sorted(list(set(found_ips)))

    console.print(f"[green]Found {len(found_ips)} devices.[/green]")

    results = []
    default_credentials = [
        ('admin', 'admin'),
        ('admin', '12345'),
        ('admin', ''),
    ]

    for ip in found_ips:
        camera_info = None

        # Determine credentials to try
        creds_to_try = []
        if args.user and args.password:
            creds_to_try.append((args.user, args.password))

        # Add defaults if not already present
        for cred in default_credentials:
            if cred not in creds_to_try:
                creds_to_try.append(cred)

        # Tier 1: Automated
        for user, password in creds_to_try:
            logger.info(f"Trying to inspect {ip} with user '{user}'...")
            inspector = CameraInspector(ip, user, password)
            try:
                # connect() raises exception on auth failure
                inspector.connect()

                # If connected, get info
                cam_info = inspector.get_device_info()
                cam_info.profiles = inspector.get_profiles()
                cam_info.ptz = inspector.get_ptz_status()

                camera_info = cam_info
                logger.info(f"Successfully inspected {ip} with user '{user}'")
                break
            except Exception as e:
                logger.debug(f"Failed to inspect {ip} with user '{user}': {e}")
                continue

        # Tier 2: Interactive Fallback
        if not camera_info:
            console.print(f"[yellow]Could not login to {ip} with default credentials.[/yellow]")
            while True:
                resp = console.input(f"Please enter username for {ip} (or 'skip'): ")
                if resp.lower() == 'skip' or not resp:
                    break
                user = resp
                password = console.input(f"Please enter password for {ip}: ", password=True)

                logger.info(f"Trying manual credentials for {ip}...")
                inspector = CameraInspector(ip, user, password)
                try:
                    inspector.connect()
                    cam_info = inspector.get_device_info()
                    cam_info.profiles = inspector.get_profiles()
                    cam_info.ptz = inspector.get_ptz_status()

                    camera_info = cam_info
                    console.print(f"[green]Login successful![/green]")
                    break
                except Exception as e:
                    console.print(f"[red]Login failed: {e}[/red]")

        if camera_info:
            results.append(camera_info)
        else:
            logger.warning(f"Skipping {ip} due to authentication failure.")

    # Output filename generation
    if not args.output:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if subnets and len(subnets) == 1:
            subnet_str = subnets[0].replace('/', '_')
            args.output = f"scan_{subnet_str}_{timestamp}.json"
        else:
            args.output = f"scan_network_{timestamp}.json"

    print_summary_table(results)
    export_to_json(results, args.output)
    console.print(f"[bold blue]Results saved to {args.output}[/bold blue]")

if __name__ == "__main__":
    main()
