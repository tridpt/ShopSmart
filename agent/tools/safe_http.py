"""SSRF-safe HTTP transport for fetching untrusted product URLs."""
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests as _requests
from requests.adapters import HTTPAdapter

RequestException = _requests.RequestException
Timeout = _requests.Timeout
InvalidURL = _requests.exceptions.InvalidURL
TooManyRedirects = _requests.TooManyRedirects


class ResponseTooLarge(RequestException):
    """Raised when a response body exceeds the allowed size."""


class UnsupportedContentType(RequestException):
    """Raised when a response is not an allowed content type."""


_REDIRECT_CODES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 5
_ALLOWED_PORTS = {"http": 80, "https": 443}

# Cap the body we download from untrusted URLs (a product page or JSON API is
# small; anything huge is likely abuse or a wrong URL). Configurable via env.
try:
    _MAX_RESPONSE_BYTES = int(os.environ.get("SCRAPE_MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))
except (TypeError, ValueError):
    _MAX_RESPONSE_BYTES = 5 * 1024 * 1024

# Only parse text/HTML/JSON — never binaries, images or downloads.
_ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/json",
    "application/ld+json",
    "text/xml",
    "application/xml",
)


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
            stream=True,
            **kwargs,
        )
        response.url = normalized
    except BaseException:
        session.close()
        raise
    # Caller is responsible for closing the session once the body is read.
    return response, session


def _check_content_type(response):
    """Reject responses that aren't text/HTML/JSON (never binaries/downloads)."""
    content_type = response.headers.get("Content-Type", "")
    main_type = content_type.split(";", 1)[0].strip().lower()
    # Allow servers that omit the header; reject explicit unsupported types.
    if main_type and main_type not in _ALLOWED_CONTENT_TYPES:
        raise UnsupportedContentType(f"Unsupported content type: {main_type}")


def _read_capped(response):
    """Read the body up to the size cap, raising if it is exceeded."""
    declared = response.headers.get("Content-Length")
    if declared is not None:
        try:
            if int(declared) > _MAX_RESPONSE_BYTES:
                raise ResponseTooLarge("Response exceeds maximum allowed size")
        except ValueError:
            pass  # malformed header; fall back to streamed enforcement

    chunks = bytearray()
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        chunks.extend(chunk)
        if len(chunks) > _MAX_RESPONSE_BYTES:
            raise ResponseTooLarge("Response exceeds maximum allowed size")
    # Populate the buffered content so .text/.json() work as usual.
    response._content = bytes(chunks)
    response._content_consumed = True


def get(url: str, **kwargs):
    """GET an untrusted URL, validating DNS and pinning every redirect hop.

    Streams the body, enforces a content-type allowlist and a maximum size, and
    re-validates every redirect target. The returned response has its (capped)
    body already buffered.
    """
    current = url
    for redirect_count in range(_MAX_REDIRECTS + 1):
        response, session = _get_once(current, **kwargs)
        try:
            if response.status_code in _REDIRECT_CODES:
                location = response.headers.get("Location")
                if not location:
                    _read_capped(response)
                    return response
                if redirect_count >= _MAX_REDIRECTS:
                    raise TooManyRedirects("Too many redirects")
                current = urljoin(current, location)
                continue

            _check_content_type(response)
            _read_capped(response)
            return response
        finally:
            response.close()
            session.close()

    raise TooManyRedirects("Too many redirects")