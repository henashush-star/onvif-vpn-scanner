import re
import subprocess
import socket

def get_network_interfaces():
    """
    Returns a list of IP addresses associated with network interfaces.
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
