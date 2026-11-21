import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional
from fastapi import HTTPException, status
from app.utils.logger import logger

# Disallowed IP Networks (IPv4 and IPv6)
DISALLOWED_NETWORKS = [
    # IPv4 Private & Loopback
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # Private-use (RFC 1918)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local (Cloud metadata 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-use (RFC 1918)
    ipaddress.ip_network("192.168.0.0/16"),     # Private-use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (CGNAT)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast

    # IPv6 Loopback, Link-Local, Private
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),       # IPv4/IPv6 translation
]

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
}

def is_ip_disallowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to any restricted or private network."""
    # Check standard attributes
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    
    # Check against explicit disallowed subnets
    for network in DISALLOWED_NETWORKS:
        if ip in network:
            return True
    return False

def validate_url_security(url: str) -> Tuple[bool, str]:
    """
    Validate that the given URL is safe from SSRF attacks:
    - Scheme must be http or https
    - Hostname must be present and not forbidden
    - Resolved IP address must not be private, loopback, or link-local
    - Disallows embedded credentials
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL structure: {str(e)}"

    # 1. Validate Scheme
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported URL scheme '{parsed.scheme}'. Only 'http' and 'https' are permitted."

    # 2. Check for userinfo (credentials in URL)
    if parsed.username or parsed.password:
        return False, "Embedded credentials in URL are prohibited."

    # 3. Check Hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL."

    hostname_clean = hostname.strip("[]").lower()
    if hostname_clean in FORBIDDEN_HOSTNAMES:
        return False, f"Access to hostname '{hostname}' is blocked for security (SSRF prevention)."

    # 4. Check if hostname is directly an IP literal
    try:
        ip = ipaddress.ip_address(hostname_clean)
        if is_ip_disallowed(ip):
            return False, f"Direct access to private or restricted IP '{ip}' is blocked."
        return True, ""
    except ValueError:
        # Not an IP literal, proceed to DNS resolution
        pass

    # 5. Resolve DNS and check all returned IPs
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        if not addr_info:
            return False, f"Could not resolve hostname '{hostname}'."

        for family, socktype, proto, canonname, sockaddr in addr_info:
            resolved_ip_str = sockaddr[0]
            try:
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                if is_ip_disallowed(resolved_ip):
                    logger.warning(f"SSRF blocked: Hostname '{hostname}' resolved to prohibited IP '{resolved_ip}'.")
                    return False, f"Hostname '{hostname}' resolves to restricted IP ({resolved_ip}). Request blocked."
            except ValueError:
                return False, f"Invalid IP address encountered during resolution: {resolved_ip_str}"

    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname '{hostname}': {str(e)}"
    except Exception as e:
        return False, f"Error validating hostname '{hostname}': {str(e)}"

    return True, ""

def enforce_safe_url(url: str):
    """Raise HTTP 400 with clear error message if URL fails SSRF safety validation."""
    is_safe, error_msg = validate_url_security(url)
    if not is_safe:
        logger.warning(f"SSRF Guard rejected request to: {url} - Reason: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "SSRF_SECURITY_VIOLATION",
                "message": error_msg,
                "url": url
            }
        )
