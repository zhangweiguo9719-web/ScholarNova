"""
SSRF 防护模块

提供 URL 安全验证，防止服务器端请求伪造（SSRF）攻击。
"""

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

from app.config import settings


# 内网 IP 段（RFC 1918 / RFC 6890 / RFC 4291）
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Class A private
    ipaddress.ip_network("172.16.0.0/12"),     # Class B private
    ipaddress.ip_network("192.168.0.0/16"),    # Class C private
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
]

# 允许的协议
ALLOWED_SCHEMES = {"https"}
if settings.ALLOW_HTTP:
    ALLOWED_SCHEMES.add("http")


def _is_private_ip(ip_str: str) -> bool:
    """
    检查 IP 地址是否为内网地址

    Args:
        ip_str: IP 地址字符串

    Returns:
        True 如果是内网地址
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in PRIVATE_NETWORKS:
            if ip in network:
                return True
        return False
    except ValueError:
        return True  # 无法解析的 IP 视为不安全


def _resolve_hostname(hostname: str) -> list[str]:
    """
    解析域名为 IP 地址列表

    Args:
        hostname: 主机名

    Returns:
        IP 地址列表
    """
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        ips = []
        for family, _, _, _, sockaddr in results:
            ip_str = sockaddr[0]
            if ip_str not in ips:
                ips.append(ip_str)
        return ips
    except (socket.gaierror, OSError):
        return []


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    验证 URL 是否安全（防止 SSRF）

    检查规则：
    1. 必须是 http/https 协议
    2. 解析域名，检查是否为内网 IP
    3. localhost 仅在 DEBUG 模式下允许
    4. 禁止 IP 字面量中的内网地址

    Args:
        url: 待验证的 URL

    Returns:
        (is_valid, error_message) 元组
    """
    if not url or not isinstance(url, str):
        return False, "URL 不能为空"

    # 1. 解析 URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 格式无效"

    # 2. 协议检查
    if parsed.scheme not in ALLOWED_SCHEMES:
        allowed = ", ".join(sorted(ALLOWED_SCHEMES))
        return False, f"仅允许 {allowed} 协议"

    # 3. 主机名检查
    hostname = parsed.hostname
    if not hostname:
        return False, "URL 缺少主机名"

    # 4. localhost 检查
    localhost_names = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if hostname.lower() in localhost_names:
        if not settings.ALLOW_PRIVATE_IPS and not settings.DEBUG:
            return False, "不允许访问 localhost（非调试模式）"

    # 5. IP 字面量检查
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_private_ip(str(ip)) and not settings.ALLOW_PRIVATE_IPS:
            return False, f"不允许访问内网 IP 地址: {hostname}"
        return True, None
    except ValueError:
        pass  # 不是 IP 字面量，继续检查域名

    # 6. 域名解析检查（防止 DNS Rebinding）
    if not settings.ALLOW_PRIVATE_IPS:
        resolved_ips = _resolve_hostname(hostname)
        if not resolved_ips:
            return False, f"无法解析域名: {hostname}"
        for ip_str in resolved_ips:
            if _is_private_ip(ip_str):
                return False, f"域名 {hostname} 解析到内网 IP: {ip_str}"

    return True, None


def validate_base_url(url: str) -> tuple[bool, Optional[str]]:
    """
    验证 LLM API Base URL 是否安全

    除了 SSRF 检查外，还检查：
    - 必须是 HTTPS（除非是 localhost 且 DEBUG 模式）

    Args:
        url: Base URL

    Returns:
        (is_valid, error_message) 元组
    """
    if not url:
        return True, None  # 空 URL 使用默认值

    is_valid, error = validate_url(url)
    if not is_valid:
        return False, error

    parsed = urlparse(url)

    # 非 localhost 必须使用 HTTPS
    hostname = parsed.hostname or ""
    localhost_names = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme == "http" and hostname.lower() not in localhost_names:
        if not settings.ALLOW_HTTP:
            return False, "非 localhost 地址必须使用 HTTPS"

    return True, None
