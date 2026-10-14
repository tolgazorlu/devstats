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
import shutil
import stat

CONFIG_DIR = os.path.expanduser("~/.config/asc-menubar")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--issuer-id", required=True)
    p.add_argument("--key-id", required=True)
    p.add_argument("--vendor-number", required=True)
    p.add_argument("--p8", help="path to AuthKey_<KEYID>.p8; omit if it is already in the config dir")
    a = p.parse_args()

    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.chmod(CONFIG_DIR, stat.S_IRWXU)
    target = os.path.join(CONFIG_DIR, f"AuthKey_{a.key_id}.p8")
    if a.p8:
        src = os.path.expanduser(a.p8)
        with open(src) as f:
            if "BEGIN PRIVATE KEY" not in f.read(64):
                raise SystemExit(f"{src} does not look like a .p8 private key")
        if os.path.abspath(src) != target:
            shutil.move(src, target)
    if not os.path.exists(target):
        raise SystemExit(f"missing {target}; pass --p8")
    os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)

    cfg_path = os.path.join(CONFIG_DIR, "config.json")
    with open(cfg_path, "w") as f:
        json.dump({"key_id": a.key_id, "issuer_id": a.issuer_id, "vendor_number": a.vendor_number}, f)
    os.chmod(cfg_path, stat.S_IRUSR | stat.S_IWUSR)
    print(f"ok: {cfg_path} and {os.path.basename(target)} (0600)")


if __name__ == "__main__":
    main()
