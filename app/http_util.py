"""Shared httpx client factory.

Builds clients that honor the standard proxy environment variables
(HTTPS_PROXY / https_proxy / ALL_PROXY) by passing the proxy explicitly.
This avoids a known httpx failure parsing NO_PROXY lists that contain
bracketed IPv6 entries (e.g. "[::1]" -> "Invalid port: ':1]'"), and lets
SSL_CERT_FILE point at a custom CA bundle when one is provided.
On a machine with no proxy variables set, this is just a direct client.
"""

import os

import httpx


def http_client(timeout: float = 20.0) -> httpx.Client:
    proxy = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("all_proxy")
        or os.environ.get("ALL_PROXY")
    )
    verify = os.environ.get("SSL_CERT_FILE") or True
    return httpx.Client(proxy=proxy, trust_env=False, timeout=timeout, verify=verify)
