"""SSRF-safe HTTP transport for fetching untrusted product URLs."""
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests as _requests
from requests.adapters import HTTPAdapter

RequestException = _requests.RequestException
Timeout = _requests.Timeout
InvalidURL = _requests.exceptions.InvalidURL
TooManyRedirects = _requests.TooManyRedirects

_REDIRECT_CODES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 5
_ALLOWED_PORTS = {"http": 80, "https": 443}


class _PinnedHTTPSAdapter(HTTPAdapter):
    """Connect to a vetted IP while verifying TLS for the original hostname."""

    def __init__(self, hostname: str):
        self._hostname = hostname
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["assert_hostname"] = self._hostname
        pool_kwargs["server_hostname"] = self._hostname
        return super().init_poolmanager(connections, maxsize, block, **pool_kwargs)


def _validated_target(url: str) -> tuple[str, str, int, str]:
    """Return normalized URL, hostname, port and one vetted/pinned public IP."""
    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in _ALLOWED_PORTS or not parts.hostname:
            raise InvalidURL("Only absolute HTTP(S) URLs are allowed")
        if parts.username is not None or parts.password is not None:
            raise InvalidURL("URL credentials are not allowed")
        hostname = parts.hostname.rstrip(".").encode("idna").decode("ascii")
        if not hostname or "%" in hostname:
            raise InvalidURL("Invalid URL hostname")
        port = parts.port or _ALLOWED_PORTS[scheme]
        if port != _ALLOWED_PORTS[scheme]:
            raise InvalidURL("Non-standard URL ports are not allowed")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise InvalidURL("Invalid URL") from exc

    try:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise InvalidURL("URL hostname could not be resolved") from exc
    if not answers:
        raise InvalidURL("URL hostname could not be resolved")

    public_ips = []
    for _, _, _, _, sockaddr in answers:
        try:
            address = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
        except ValueError as exc:
            raise InvalidURL("URL resolved to an invalid address") from exc
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if not address.is_global:
            raise InvalidURL("Private or reserved network addresses are not allowed")
        if str(address) not in public_ips:
            public_ips.append(str(address))

    normalized = urlunsplit((scheme, parts.netloc, parts.path or "/", parts.query, ""))
    return normalized, hostname, port, public_ips[0]


def _get_once(url: str, **kwargs):
    normalized, hostname, port, pinned_ip = _validated_target(url)
    parts = urlsplit(normalized)
    ip_netloc = f"[{pinned_ip}]" if ":" in pinned_ip else pinned_ip
    if port != _ALLOWED_PORTS[parts.scheme]:
        ip_netloc = f"{ip_netloc}:{port}"
    pinned_url = urlunsplit((parts.scheme, ip_netloc, parts.path, parts.query, ""))

    headers = dict(kwargs.pop("headers", {}) or {})
    headers["Host"] = hostname
    kwargs.pop("allow_redirects", None)
    kwargs.pop("proxies", None)

    session = _requests.Session()
    session.trust_env = False
    if parts.scheme == "https":
        session.mount(f"https://{ip_netloc}", _PinnedHTTPSAdapter(hostname))
    try:
        response = session.get(
            pinned_url,
            headers=headers,
            allow_redirects=False,
            **kwargs,
        )
        response.url = normalized
        return response
    finally:
        session.close()


def get(url: str, **kwargs):
    """GET an untrusted URL, validating DNS and pinning every redirect hop."""
    current = url
    for redirect_count in range(_MAX_REDIRECTS + 1):
        response = _get_once(current, **kwargs)
        if response.status_code not in _REDIRECT_CODES:
            return response

        location = response.headers.get("Location")
        response.close()
        if not location:
            return response
        if redirect_count >= _MAX_REDIRECTS:
            raise TooManyRedirects("Too many redirects")
        current = urljoin(current, location)

    raise TooManyRedirects("Too many redirects")