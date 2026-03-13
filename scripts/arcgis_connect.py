"""
ArcGIS connection helper.

The standard OAuth2 flow (client_id + redirect_uri=localhost) fails in many
terminal environments because the browser redirects to localhost and the
arcgis library then calls input() to ask you to paste a code — but that
prompt is invisible or non-functional in SSH sessions, containers, etc.

This script provides three alternative authentication approaches:

  Method 1 (recommended for scripts): username + password
  Method 2: OAuth2 with OOB redirect (code shown in browser, paste once)
  Method 3: API key / pre-generated token (no interactive prompt at all)

Set credentials via environment variables rather than hardcoding them.
"""

import os
from arcgis.gis import GIS

PORTAL_URL = "https://theriverstrust.maps.arcgis.com"


def connect_username_password() -> GIS:
    """
    Authenticate with username and password.

    Set environment variables:
        ARCGIS_USERNAME
        ARCGIS_PASSWORD
    """
    username = os.environ.get("ARCGIS_USERNAME")
    password = os.environ.get("ARCGIS_PASSWORD")

    if not username or not password:
        raise EnvironmentError(
            "Set ARCGIS_USERNAME and ARCGIS_PASSWORD environment variables.\n"
            "  export ARCGIS_USERNAME='your_username'\n"
            "  export ARCGIS_PASSWORD='your_password'"
        )

    return GIS(PORTAL_URL, username, password)


def connect_oauth_oob(client_id: str) -> GIS:
    """
    OAuth2 with 'out-of-band' redirect.

    The browser will show the authorisation code directly on the page
    (instead of redirecting to localhost), so you can copy-paste it
    into the terminal prompt. This works in any terminal environment.

    Args:
        client_id: Your ArcGIS application client ID.
    """
    return GIS(
        PORTAL_URL,
        client_id=client_id,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )


def connect_api_key() -> GIS:
    """
    Authenticate with a pre-generated API key (no interactive prompt).

    Generate a key at:
      https://theriverstrust.maps.arcgis.com → Content → My Content → New item → API key

    Set the environment variable:
        ARCGIS_API_KEY
    """
    api_key = os.environ.get("ARCGIS_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "Set the ARCGIS_API_KEY environment variable.\n"
            "  export ARCGIS_API_KEY='your_api_key'"
        )

    return GIS(PORTAL_URL, api_key=api_key)


if __name__ == "__main__":
    # ---------------------------------------------------------------
    # Choose a method. Method 1 is the easiest for non-interactive
    # scripts. Method 2 still opens a browser but avoids the broken
    # localhost redirect. Method 3 requires no browser at all.
    # ---------------------------------------------------------------

    # Method 1: username + password
    # export ARCGIS_USERNAME=... ARCGIS_PASSWORD=...
    gis = connect_username_password()

    # Method 2: OAuth2 OOB (uncomment to use instead)
    # gis = connect_oauth_oob(client_id="QqCukKbHG8MFzv3Q")

    # Method 3: API key (uncomment to use instead)
    # gis = connect_api_key()

    print("Connected as:", gis.users.me)
