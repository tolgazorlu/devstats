#!/usr/bin/env python3
"""Write ~/.config/asc-menubar/config.json and install the App Store Connect .p8 key.

Usage:
  .venv/bin/python scripts/configure.py --issuer-id UUID --key-id KEYID \
      --vendor-number 12345678 --p8 ~/Downloads/AuthKey_KEYID.p8

The key file is moved (not copied) into the config dir with 0600 permissions, so no
second copy stays in Downloads. Its contents are never printed.
"""
import argparse
import json
import os
import re
import shutil
import stat

CONFIG_DIR = os.path.expanduser("~/.config/asc-menubar")
PATTERNS = {
    "issuer_id": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I),
    "key_id": re.compile(r"^[A-Z0-9]{10}$"),
    "vendor_number": re.compile(r"^[0-9]{5,12}$"),
    "currency": re.compile(r"^[A-Z]{3}$"),
}


def check(name, value):
    if not PATTERNS[name].match(value):
        raise SystemExit(f"--{name.replace('_', '-')} looks wrong: {value!r}")
    return value


def write_private(path, text):
    """Create or replace a file that is 0600 from the first byte."""
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--issuer-id", required=True)
    p.add_argument("--key-id", required=True)
    p.add_argument("--vendor-number", required=True)
    p.add_argument("--p8", help="path to AuthKey_<KEYID>.p8; omit if it is already in the config dir")
    p.add_argument("--currency", help="display currency for revenue, e.g. TRY, USD, EUR (default: keep, else USD)")
    a = p.parse_args()
    issuer, key_id, vendor = check("issuer_id", a.issuer_id), check("key_id", a.key_id), \
        check("vendor_number", a.vendor_number)

    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    os.chmod(CONFIG_DIR, stat.S_IRWXU)
    target = os.path.join(CONFIG_DIR, f"AuthKey_{key_id}.p8")
    if a.p8:
        src = os.path.expanduser(a.p8)
        if os.path.islink(src) or not os.path.isfile(src):
            raise SystemExit(f"{src} is not a regular file")
        with open(src) as f:
            if "BEGIN PRIVATE KEY" not in f.read(64):
                raise SystemExit(f"{src} does not look like a .p8 private key")
        if os.path.abspath(src) != target:
            shutil.move(src, target)
    if not os.path.exists(target):
        raise SystemExit(f"missing {target}; pass --p8")
    os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)

    cfg_path = os.path.join(CONFIG_DIR, "config.json")
    old = {}
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            old = json.load(f)
    currency = check("currency", (a.currency or old.get("currency") or "USD").upper())
    write_private(cfg_path, json.dumps({"key_id": key_id, "issuer_id": issuer, "vendor_number": vendor,
                                        "currency": currency}))
    print(f"ok: {cfg_path} and {os.path.basename(target)} (0600)")


if __name__ == "__main__":
    main()
