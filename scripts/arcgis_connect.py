"""
ArcGIS connection for SAML/SSO organisations.

The arcgis library's built-in OAuth2 flow calls input() to ask you to paste
the authorisation code, which doesn't work in many terminals (SSH, containers,
VS Code integrated terminal, etc.) — especially when the org uses SAML/SSO
and username+password login is disabled.

This script bypasses the library's OAuth handler entirely. It:
  1. Starts a local HTTP server on localhost:8888
  2. Opens your browser to the ArcGIS authorisation URL
  3. Captures the redirect automatically (no paste required)
  4. Exchanges the code for a token via the REST API
  5. Returns a GIS object authenticated with that token

Usage:
    python scripts/arcgis_connect.py

Requirements:
    pip install arcgis requests
"""

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from arcgis.gis import GIS

PORTAL_URL = "https://theriverstrust.maps.arcgis.com"
CLIENT_ID = "QqCukKbHG8MFzv3Q"
REDIRECT_URI = "http://localhost:8888"
PORT = 8888
TIMEOUT_SECONDS = 120


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Captures the ?code= parameter from the OAuth redirect."""

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body>"
                b"<h2>Authentication successful!</h2>"
                b"<p>You can close this tab and return to your terminal.</p>"
                b"</body></html>"
            )
        else:
            self.server.auth_code = None
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: authorisation code not found in redirect.")
        self.server.got_code.set()

    def log_message(self, format, *args):  # suppress request logs
        pass


def connect() -> GIS:
    """
    Authenticate to ArcGIS via SAML/OAuth2 without any terminal input.

    Opens a browser window, waits for the SAML login to complete, then
    captures the authorisation code automatically via a local callback server.
    """
    # Build the authorisation URL
    auth_url = (
        f"{PORTAL_URL}/sharing/rest/oauth2/authorize?"
        + urlencode(
            {
                "client_id": CLIENT_ID,
                "response_type": "code",
                "redirect_uri": REDIRECT_URI,
                "expiration": 20160,  # token lifetime in minutes (~2 weeks)
            }
        )
    )

    # Start the local callback server
    server = HTTPServer(("localhost", PORT), _OAuthCallbackHandler)
    server.auth_code = None
    server.got_code = threading.Event()

    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    # Open browser
    print("Opening browser for ArcGIS login...")
    print(f"If the browser does not open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for the callback
    print(f"Waiting for login (timeout: {TIMEOUT_SECONDS}s)...")
    if not server.got_code.wait(timeout=TIMEOUT_SECONDS):
        server.server_close()
        raise RuntimeError(
            "Timed out waiting for authorisation. "
            "Did you complete the login in the browser?"
        )
    server.server_close()

    if not server.auth_code:
        raise RuntimeError(
            "Browser redirect received but no authorisation code was found. "
            "Check that the redirect URI registered for this client_id is "
            "exactly: http://localhost:8888"
        )

    # Exchange the code for a token
    resp = requests.post(
        f"{PORTAL_URL}/sharing/rest/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "code": server.auth_code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "f": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token_data = resp.json()

    if "access_token" not in token_data:
        raise RuntimeError(f"Token exchange failed: {token_data}")

    gis = GIS(PORTAL_URL, token=token_data["access_token"])
    return gis


if __name__ == "__main__":
    gis = connect()
    print("Connected as:", gis.users.me)
