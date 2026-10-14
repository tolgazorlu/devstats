"""Minimal App Store Connect API client (JWT auth, stdlib HTTP)."""
import gzip
import json
import os
import stat
import time
import urllib.error
import urllib.parse
import urllib.request

import jwt

CONFIG_DIR = os.path.expanduser("~/.config/asc-menubar")
BASE = "https://api.appstoreconnect.apple.com"
API_HOST = "api.appstoreconnect.apple.com"
TOKEN_TTL = 1200  # Apple rejects tokens that live longer than 20 minutes


def ensure_private_dir():
    """Create the config dir as 0700 and tighten it if it already exists looser."""
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    if stat.S_IMODE(os.stat(CONFIG_DIR).st_mode) & 0o077:
        os.chmod(CONFIG_DIR, 0o700)


def load_config():
    with open(os.path.join(CONFIG_DIR, "config.json")) as f:
        return json.load(f)


def key_path(cfg):
    key_id = str(cfg["key_id"])
    if not key_id.isalnum():  # the id becomes part of a file name
        raise ValueError("config key_id must be alphanumeric")
    return os.path.join(CONFIG_DIR, f"AuthKey_{key_id}.p8")


def token(cfg):
    path = key_path(cfg)
    if stat.S_IMODE(os.stat(path).st_mode) & 0o077:
        os.chmod(path, 0o600)  # private key must not be readable by other users
    with open(path) as f:
        key = f.read()
    now = int(time.time())
    return jwt.encode(
        {"iss": cfg["issuer_id"], "iat": now, "exp": now + TOKEN_TTL, "aud": "appstoreconnect-v1"},
        key,
        algorithm="ES256",
        headers={"kid": cfg["key_id"], "typ": "JWT"},
    )


def api_url(path):
    """Absolute URL on the App Store Connect API host; anything else is refused.

    Paging follows `links.next` from responses, so this guarantees the bearer token is
    only ever sent to Apple's API over HTTPS.
    """
    url = path if path.startswith("http") else BASE + path
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname != API_HOST:
        raise ValueError(f"refusing to send credentials to {parts.scheme}://{parts.hostname}")
    return url


def request(cfg, path, params=None, method="GET", body=None, raw=False):
    url = api_url(path)
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
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
    if urllib.parse.urlsplit(url).scheme != "https":
        raise ValueError("report segment URL must be https")
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
