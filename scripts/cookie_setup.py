#!/usr/bin/env python3
# scripts/cookie_setup.py
"""
Interactive Cookie & Storage State setup helper.
Converts Chrome / Cookie-Editor JSON exports or cookie key-values into Playwright storage state.

Usage:
  python scripts/cookie_setup.py [--vps-url http://localhost:8000] [--admin-token my-secure-admin-token]
"""

import sys
import json
import argparse
from pathlib import Path

try:
    import httpx
except ImportError:
    import urllib.request as httpx  # fallback


NEEDED_COOKIES = [
    "__Secure-1PSID",
    "__Secure-1PSIDTS",
    "__Secure-3PSID",
    "__Secure-3PSIDTS",
    "HSID", "SSID", "APISID", "SAPISID", "SID", "NID",
]


def format_cookies(cookies_raw):
    formatted = []
    if isinstance(cookies_raw, dict):
        for name, val in cookies_raw.items():
            formatted.append({
                "name": name,
                "value": str(val),
                "domain": ".google.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            })
    elif isinstance(cookies_raw, list):
        for item in cookies_raw:
            if isinstance(item, dict) and "name" in item and "value" in item:
                formatted.append({
                    "name": item["name"],
                    "value": str(item["value"]),
                    "domain": item.get("domain", ".google.com"),
                    "path": item.get("path", "/"),
                    "expires": item.get("expires", -1),
                    "httpOnly": item.get("httpOnly", True),
                    "secure": item.get("secure", True),
                    "sameSite": item.get("sameSite", "Lax"),
                })
    return formatted


def main():
    parser = argparse.ArgumentParser(description="NotebookLM Cookie & Storage State Setup")
    parser.add_argument("--vps-url", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--admin-token", default="my-secure-admin-token", help="X-Admin-Token")
    parser.add_argument("--account-id", default="main", help="Account identifier")
    parser.add_argument("--input-file", help="Path to exported Cookie-Editor JSON file")
    args = parser.parse_args()

    print("========================================")
    print("  NotebookLM Cookie & Auth Setup")
    print("========================================")

    cookies = {}

    if args.input_file:
        file_path = Path(args.input_file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            cookies = data
            print(f"✅ Loaded cookies from {file_path}")
        except Exception as e:
            print(f"❌ Error parsing {file_path}: {e}")
            sys.exit(1)
    else:
        print("\nPaste your Cookie-Editor JSON export or press Ctrl+C to cancel:\n")
        try:
            lines = []
            while True:
                line = input()
                if not line and lines:
                    break
                lines.append(line)
            raw = "\n".join(lines)
            data = json.loads(raw)
            cookies = data
            print(f"✅ Parsed cookies successfully!")
        except (KeyboardInterrupt, json.JSONDecodeError) as e:
            print(f"\nManual input failed or cancelled: {e}")
            print("\nYou can save your cookies to a file and run:")
            print("  python scripts/cookie_setup.py --input-file my_cookies.json")
            sys.exit(1)

    formatted = format_cookies(cookies)
    storage_state = {"cookies": formatted, "origins": []}

    local_save_path = Path(f"storage/tokens/{args.account_id}_storage_state.json")
    local_save_path.parent.mkdir(parents=True, exist_ok=True)
    local_save_path.write_text(json.dumps(storage_state, indent=2), encoding="utf-8")
    print(f"✅ Local storage state saved to: {local_save_path}")

    # Push to Gateway
    vps_url = args.vps_url.rstrip("/")
    target_endpoint = f"{vps_url}/admin/accounts/setup-cookies"
    print(f"\nAttempting to push cookies to Gateway at: {target_endpoint}...")

    payload = json.dumps({
        "account_id": args.account_id,
        "cookies": cookies,
    }).encode("utf-8")

    try:
        import urllib.request
        req = urllib.request.Request(
            target_endpoint,
            data=payload,
            headers={
                "X-Admin-Token": args.admin_token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            print("✅ Gateway uploaded successfully:")
            print(body)
    except Exception as exc:
        print(f"⚠️ Gateway unreachable at {target_endpoint} ({exc}). Local storage file remains ready!")


if __name__ == "__main__":
    main()
