import argparse
import logging
import sys
import datetime
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt
from .scanner import WSDiscoveryScanner, IPRangeScanner
from .inspector import CameraInspector
from .output import print_summary_table, export_to_json
from .utils import get_network_interfaces, get_subnets
from .models import CameraInfo

# Tier 1 Credentials
DEFAULT_CREDENTIALS = [
    ("admin", "admin"),
    ("admin", "12345"),
    ("admin", "password"),
    ("admin", "123456"),
    ("root", "root"),
    ("root", "pass"),
    ("root", "123456"),
    ("admin", "")
]

def main():
    parser = argparse.ArgumentParser(description="ONVIF Network Camera Scanner")

    parser.add_argument("--mode", choices=["ws-discovery", "ip-range"], help="Discovery mode (optional)")
    parser.add_argument("--subnet", help="CIDR subnet for IP range scanning (e.g., 192.168.1.0/24)")
    parser.add_argument("--user", help="Camera username (optional)")
    parser.add_argument("--password", help="Camera password (optional)")
    parser.add_argument("--output", help="Output JSON file (optional, auto-generated if missing)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
    logger = logging.getLogger("onvif_scanner")

    console = Console()

    # 1. Automated Network & Subnet Discovery
    subnets = []
    if args.subnet:
        subnets = [args.subnet]
    else:
        # Auto-discover subnets
        console.print("[bold blue]Discovering networks...[/bold blue]")
        subnets = get_subnets()
        if not subnets:
            console.print("[yellow]No subnets discovered. Scanning local interface IPs using WS-Discovery as fallback.[/yellow]")
        else:
            console.print(f"[green]Discovered subnets: {', '.join(subnets)}[/green]")

    found_ips = set()

    # 2. Scanning Logic
    # If mode is explicitly ip-range or we have subnets, do IP range scan
    # If mode is ws-discovery or default (and no specific subnet override), try WS-Discovery too

    scan_ws = False
    scan_ip = False

    if args.mode == "ws-discovery":
        scan_ws = True
    elif args.mode == "ip-range":
        scan_ip = True
    else:
        # "Zero-Config" default: Do both if possible
        scan_ws = True
        if subnets:
            scan_ip = True

    if scan_ws:
        console.print("[bold blue]Starting WS-Discovery...[/bold blue]")
        try:
            ws_scanner = WSDiscoveryScanner()
            interfaces = get_network_interfaces()
            logger.info(f"Scanning on interfaces: {interfaces}")
            ws_ips = ws_scanner.discover(interfaces=interfaces)
            found_ips.update(ws_ips)
        except Exception as e:
            logger.error(f"WS-Discovery failed: {e}")

    if scan_ip:
        for subnet in subnets:
            console.print(f"[bold blue]Starting IP Range Scan on {subnet}...[/bold blue]")
            try:
                ip_scanner = IPRangeScanner(subnet)
                range_ips = ip_scanner.scan()
                found_ips.update(range_ips)
            except Exception as e:
                logger.error(f"IP Range Scan failed for {subnet}: {e}")

    sorted_ips = sorted(list(found_ips))
    console.print(f"[green]Found {len(sorted_ips)} devices: {', '.join(sorted_ips)}[/green]")

    results = []

    # 3. Smart Two-Tier Authentication Logic
    for ip in sorted_ips:
        console.print(f"\n[bold]Inspecting {ip}...[/bold]")

        user = args.user
        password = args.password

        cam_info = None
        authenticated = False

        # If credentials provided via CLI, use them first
        if user and password:
            logger.info(f"Using provided credentials for {ip}")
            inspector = CameraInspector(ip, user, password)
            info = inspector.get_device_info()
            if info.inspection_status == "success":
                authenticated = True
                cam_info = info
                # Complete inspection
                cam_info.profiles = inspector.get_profiles()
                cam_info.ptz = inspector.get_ptz_status()

        # Tier 1: Try default credentials if not yet authenticated
        if not authenticated:
            logger.info(f"Attempting Tier 1 (Default Credentials) for {ip}...")
            for cred_user, cred_pass in DEFAULT_CREDENTIALS:
                if authenticated: break

                logger.debug(f"Trying {cred_user}:{cred_pass} on {ip}")
                inspector = CameraInspector(ip, cred_user, cred_pass)
                info = inspector.get_device_info()

                if info.inspection_status == "success":
                    console.print(f"[green]Login successful with {cred_user}:***[/green]")
                    authenticated = True
                    cam_info = info
                    cam_info.profiles = inspector.get_profiles()
                    cam_info.ptz = inspector.get_ptz_status()
                    break

        # Tier 2: Interactive Fallback
        if not authenticated:
            console.print(f"[bold red]Could not login to {ip} with default credentials.[/bold red]")
            try:
                # Ask user if they want to try manually
                prompt_retry = Prompt.ask("Do you want to enter credentials manually?", choices=["y", "n"], default="y")

                if prompt_retry == "y":
                    manual_user = Prompt.ask(f"Enter username for {ip}")
                    manual_pass = Prompt.ask(f"Enter password for {ip}", password=True)

                    inspector = CameraInspector(ip, manual_user, manual_pass)
                    info = inspector.get_device_info()

                    if info.inspection_status == "success":
                        console.print(f"[green]Login successful![/green]")
                        authenticated = True
                        cam_info = info
                        cam_info.profiles = inspector.get_profiles()
                        cam_info.ptz = inspector.get_ptz_status()
                    else:
                         console.print(f"[red]Login failed.[/red]")
            except KeyboardInterrupt:
                console.print("\n[yellow]Skipping...[/yellow]")

        if cam_info:
            results.append(cam_info)
        else:
            # Add a placeholder for failed device
            results.append(CameraInfo(
                ip=ip,
                manufacturer="Unknown",
                model="Unknown",
                firmware="Unknown",
                serial="Unknown",
                inspection_status="auth_failed"
            ))

    # 4. Aggregated Results & Output
    if results:
        print_summary_table(results)

        # Automatic Output Management
        output_file = args.output
        if not output_file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # If single subnet, include it in name
            if args.subnet:
                 # Sanitize subnet string for filename (replace / with _)
                 safe_subnet = args.subnet.replace('/', '_')
                 output_file = f"scan_{safe_subnet}_{timestamp}.json"
            elif len(subnets) == 1:
                 safe_subnet = subnets[0].replace('/', '_')
                 output_file = f"scan_{safe_subnet}_{timestamp}.json"
            else:
                 output_file = f"scan_all_{timestamp}.json"

        export_to_json(results, output_file)
    else:
        console.print("[yellow]No cameras found or inspected.[/yellow]")

if __name__ == "__main__":
    main()
