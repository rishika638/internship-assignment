import pytest
from app.services.ssrf import validate_url_security, is_ip_disallowed
import ipaddress

def test_disallowed_ip_ranges():
    # Loopback
    assert is_ip_disallowed(ipaddress.ip_address("127.0.0.1")) is True
    assert is_ip_disallowed(ipaddress.ip_address("127.0.0.53")) is True
    assert is_ip_disallowed(ipaddress.ip_address("::1")) is True

    # Private IPv4 (RFC 1918)
    assert is_ip_disallowed(ipaddress.ip_address("10.0.0.1")) is True
    assert is_ip_disallowed(ipaddress.ip_address("172.16.0.1")) is True
    assert is_ip_disallowed(ipaddress.ip_address("172.31.255.255")) is True
    assert is_ip_disallowed(ipaddress.ip_address("192.168.1.1")) is True

    # Cloud Metadata (Link-Local)
    assert is_ip_disallowed(ipaddress.ip_address("169.254.169.254")) is True
    assert is_ip_disallowed(ipaddress.ip_address("169.254.1.1")) is True

    # Carrier Grade NAT & Reserved
    assert is_ip_disallowed(ipaddress.ip_address("100.64.0.1")) is True
    assert is_ip_disallowed(ipaddress.ip_address("0.0.0.0")) is True

    # Public IP should not be disallowed
    assert is_ip_disallowed(ipaddress.ip_address("8.8.8.8")) is False
    assert is_ip_disallowed(ipaddress.ip_address("1.1.1.1")) is False
    assert is_ip_disallowed(ipaddress.ip_address("93.184.216.34")) is False

def test_ssrf_rejects_localhost_and_internal():
    bad_urls = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:4000/admin",
        "http://[::1]",
        "http://10.0.0.5/api",
        "http://192.168.1.100/router",
        "http://172.16.5.10/database",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/computeMetadata/v1",
        "http://0.0.0.0",
    ]
    for url in bad_urls:
        safe, msg = validate_url_security(url)
        assert safe is False, f"Expected {url} to be blocked by SSRF validator, but passed! Msg: {msg}"

def test_ssrf_rejects_unsupported_schemes():
    bad_schemes = [
        "file:///etc/passwd",
        "ftp://ftp.example.com",
        "gopher://gopher.example.com",
        "ldap://localhost",
        "javascript:alert(1)",
    ]
    for url in bad_schemes:
        safe, msg = validate_url_security(url)
        assert safe is False
        assert "Unsupported URL scheme" in msg or "Invalid URL structure" in msg

def test_ssrf_rejects_embedded_credentials():
    url = "http://admin:secretpass@example.com"
    safe, msg = validate_url_security(url)
    assert safe is False
    assert "Embedded credentials" in msg

def test_ssrf_allows_legitimate_domains():
    good_urls = [
        "https://example.com",
        "https://www.google.com",
        "http://example.org",
        "https://github.com",
    ]
    for url in good_urls:
        safe, msg = validate_url_security(url)
        assert safe is True, f"Expected {url} to be valid, got: {msg}"
