import socket
import struct
import uuid
import re
import ipaddress
import concurrent.futures
import requests
from typing import List, Optional, Set

class WSDiscoveryScanner:
    def discover(self, interfaces: Optional[List[str]] = None, timeout: float = 2.0, retries: int = 1) -> List[str]:
        """
        Discovers ONVIF devices using WS-Discovery multicast.
        If interfaces is provided, sends probe on each interface.
        """
        if not interfaces:
            return self._discover_on_interface(None, timeout, retries)

        results = set()
        for iface_ip in interfaces:
            results.update(self._discover_on_interface(iface_ip, timeout, retries))
        return sorted(list(results))

    def _discover_on_interface(self, interface_ip: Optional[str], timeout: float, retries: int) -> List[str]:
        message = f'''<?xml version="1.0" encoding="UTF-8"?>
        <e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
                    xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
                    xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
                    xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
            <e:Header>
                <w:MessageID>uuid:{uuid.uuid4()}</w:MessageID>
                <w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
                <w:Action a:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
            </e:Header>
            <e:Body>
                <d:Probe>
                    <d:Types>dn:NetworkVideoTransmitter</d:Types>
                </d:Probe>
            </e:Body>
        </e:Envelope>'''

        ips: Set[str] = set()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)

        ttl = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        if interface_ip:
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface_ip))
            except Exception:
                # If setting interface fails, fallback to default behavior or skip
                pass

        try:
            for _ in range(retries + 1):
                sock.sendto(message.encode('utf-8'), ('239.255.255.250', 3702))

                while True:
                    try:
                        data, addr = sock.recvfrom(65535)
                        # We extract XAddrs from the response
                        xaddrs = self._extract_xaddrs(data.decode('utf-8', errors='ignore'))
                        for xaddr in xaddrs:
                            # http://192.168.1.10:80/onvif/device_service
                            match = re.search(r'http://([^:/]+)', xaddr)
                            if match:
                                ips.add(match.group(1))

                        # Fallback: add the sender IP if no XAddrs found (though uncommon for valid response)
                        if not xaddrs:
                            ips.add(addr[0])

                    except socket.timeout:
                        break
        except Exception:
            pass
        finally:
            sock.close()

        return sorted(list(ips))

    def _extract_xaddrs(self, xml_data: str) -> List[str]:
        xaddrs = []
        # Look for XAddrs tag content regardless of namespace prefix
        # Regex for <*:XAddrs>content</*:XAddrs>
        match = re.search(r'(?i)<[^:]*:?XAddrs>(.*?)</[^:]*:?XAddrs>', xml_data, re.DOTALL)
        if match:
            content = match.group(1)
            uris = content.split()
            xaddrs.extend(uris)
        return xaddrs


class IPRangeScanner:
    def __init__(self, cidr: str):
        self.cidr = cidr

    def scan(self, timeout: float = 1.0, max_workers: int = 50) -> List[str]:
        try:
            network = ipaddress.ip_network(self.cidr, strict=False)
        except ValueError:
            return []

        ips_to_scan = [str(ip) for ip in network.hosts()]
        found_ips = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(self._check_onvif, ip, timeout): ip for ip in ips_to_scan}
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    if future.result():
                        found_ips.append(ip)
                except Exception:
                    pass

        return sorted(found_ips)

    def _check_onvif(self, ip: str, timeout: float) -> bool:
        ports = [80, 8080, 8000, 8888, 5005, 37777]

        for port in ports:
            try:
                # First check if port is open to avoid long timeout on requests
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    if s.connect_ex((ip, port)) == 0:
                        url = f"http://{ip}:{port}/onvif/device_service"
                        try:
                            response = requests.get(url, timeout=timeout)
                            # 200: OK (Service reachable)
                            # 401: Unauthorized (Service exists but needs auth)
                            # 500: Internal Server Error (SOAP Fault)
                            # 405: Method Not Allowed
                            if response.status_code in [200, 401, 500, 405]:
                                return True
                        except requests.RequestException:
                            pass
            except Exception:
                pass
        return False
