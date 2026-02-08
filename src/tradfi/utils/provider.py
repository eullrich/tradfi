"""Shared remote data provider factory.

Centralizes the construction of RemoteDataProvider so every CLI command
uses the same env-var lookup and default URL.
"""

import os

from tradfi.core.remote_provider import RemoteDataProvider

# Default API URL - can be overridden with TRADFI_API_URL env var
DEFAULT_API_URL = "https://deepv-production.up.railway.app"


def get_provider() -> RemoteDataProvider:
    """Get the remote data provider using API URL and admin key from environment."""
    api_url = os.environ.get("TRADFI_API_URL", DEFAULT_API_URL)
    admin_key = os.environ.get("TRADFI_ADMIN_KEY")
    return RemoteDataProvider(api_url, admin_key=admin_key)
