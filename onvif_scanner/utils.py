import re
import subprocess
import socket
import ipaddress
from typing import List

def get_network_interfaces() -> List[str]:
    """
    Returns a list of CIDR subnets associated with network interfaces.
    Example: ['192.168.1.0/24', '10.0.0.0/8']
    """
    subnets = []
    try:
        # Try using the 'ip' command
        output = subprocess.check_output(['ip', '-4', 'addr', 'show'], stderr=subprocess.DEVNULL).decode('utf-8')
        for line in output.split('\n'):
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', line)
            if match:
                cidr = match.group(1)
                if not cidr.startswith('127.'):
                    try:
                        network = ipaddress.ip_interface(cidr).network
                        subnets.append(str(network))
                    except ValueError:
                        pass
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback: get the primary IP using socket connection
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            # Assuming /24 as a fallback
            network = ipaddress.ip_interface(f"{ip}/24").network
            subnets.append(str(network))
        except Exception:
            pass

    return sorted(list(set(subnets)))
