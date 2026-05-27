import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import requests
import threading
import time
from app.healthcare_analytics import app, server


BASE_URL = "http://127.0.0.1:8151"


def _start_server():
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    server.run(host="127.0.0.1", port=8151, debug=False, use_reloader=False)


def setup_module():
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()
    time.sleep(2)  # wait for server to be ready


def test_homepage_returns_200():
    resp = requests.get(BASE_URL)
    assert resp.status_code == 200


def test_homepage_contains_dash_root():
    resp = requests.get(BASE_URL)
    assert "dash" in resp.text.lower() or "_dash" in resp.text.lower()


def test_assets_css_served():
    """style.css should be reachable from the assets route."""
    resp = requests.get(f"{BASE_URL}/assets/style.css")
    assert resp.status_code == 200
