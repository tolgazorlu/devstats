"""Minimal App Store Connect API client (JWT auth, stdlib HTTP)."""
import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import jwt

CONFIG_DIR = os.path.expanduser("~/.config/asc-menubar")
BASE = "https://api.appstoreconnect.apple.com"


def load_config():
    with open(os.path.join(CONFIG_DIR, "config.json")) as f:
        return json.load(f)


def token(cfg):
    with open(os.path.join(CONFIG_DIR, f"AuthKey_{cfg['key_id']}.p8")) as f:
        key = f.read()
    now = int(time.time())
    return jwt.encode(
        {"iss": cfg["issuer_id"], "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"},
        key,
        algorithm="ES256",
        headers={"kid": cfg["key_id"], "typ": "JWT"},
    )


def request(cfg, path, params=None, method="GET", body=None, raw=False):
    url = path if path.startswith("http") else BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Authorization": f"Bearer {token(cfg)}",
        "Accept": "application/a-gzip" if raw else "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        content = r.read()
    if raw:
        return gzip.decompress(content) if content[:2] == b"\x1f\x8b" else content
    return json.loads(content) if content else {}


def download(url):
    """Fetch a presigned report segment URL (no auth header) and gunzip it."""
    with urllib.request.urlopen(url, timeout=120) as r:
        content = r.read()
    return gzip.decompress(content) if content[:2] == b"\x1f\x8b" else content


def paginate(cfg, path, params=None):
    """Yield every item of a paged collection endpoint."""
    page = request(cfg, path, params)
    while True:
        yield from page["data"]
        nxt = page.get("links", {}).get("next")
        if not nxt:
            return
        page = request(cfg, nxt)
