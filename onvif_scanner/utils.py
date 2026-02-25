import re
import subprocess
import socket
import ipaddress
from typing import List, Tuple

def get_network_interfaces() -> List[str]:
    """
    Returns a list of IP addresses associated with network interfaces.
    Kept for backward compatibility and WSDiscoveryScanner.
    """
    ips = []
    try:
        # Try using the 'ip' command
        output = subprocess.check_output(['ip', '-4', 'addr', 'show'], stderr=subprocess.DEVNULL).decode('utf-8')
        for line in output.split('\n'):
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
            if match:
                ip = match.group(1)
                if ip != '127.0.0.1':
                    ips.append(ip)
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback: get the primary IP using socket connection
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass

    return sorted(list(set(ips)))

def get_subnets() -> List[str]:
    """
    Returns a list of CIDR subnets derived from active network interfaces.
    Example: ['192.168.1.0/24', '10.8.0.0/24']
    """
    subnets = []
    try:
        # Try using the 'ip' command to get CIDR (e.g., 192.168.1.5/24)
        output = subprocess.check_output(['ip', '-4', 'addr', 'show'], stderr=subprocess.DEVNULL).decode('utf-8')
        for line in output.split('\n'):
            # Match inet <IP>/<CIDR>
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', line)
            if match:
                cidr = match.group(1)
                if not cidr.startswith('127.'):
                    try:
                        # Calculate network address from interface IP/CIDR
                        # strict=False allows passing an IP address with host bits set (e.g. 192.168.1.5/24)
                        network = ipaddress.ip_interface(cidr).network
                        subnets.append(str(network))
                    except ValueError:
                        pass
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback: simple /24 assumption on primary IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            # Assume /24 subnet for fallback
            network = ipaddress.ip_interface(f"{local_ip}/24").network
            subnets.append(str(network))
        except Exception:
            pass

    return sorted(list(set(subnets)))
