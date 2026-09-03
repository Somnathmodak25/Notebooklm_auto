# gateway/auth_manager.py
"""
Authentication and session storage state manager for NotebookLM Gateway.
Converts uploaded cookies (flat dict or list) into standard Playwright storage state files
and manages client initialization.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
from notebooklm import NotebookLMClient

logger = logging.getLogger(__name__)


class GatewayAuthManager:
    """
    Manages accounts and storage_state files for notebooklm-py.
    """

    def __init__(self, token_dir: Optional[str] = None):
        self.token_dir = Path(token_dir or os.getenv("TOKEN_DIR", "./storage/tokens"))
        self.token_dir.mkdir(parents=True, exist_ok=True)

    def get_storage_path(self, account_id: str) -> Path:
        return self.token_dir / f"{account_id}_storage_state.json"

    def save_cookies(
        self,
        account_id: str,
        cookies_input: Union[Dict[str, str], List[Dict[str, Any]]],
    ) -> Path:
        """
        Saves cookies in Playwright storage state JSON format.
        Accepts flat dict `{"name": "val"}` or list `[{"name": "...", "value": "..."}]`.
        """
        formatted_cookies = []

        if isinstance(cookies_input, dict):
            for name, val in cookies_input.items():
                formatted_cookies.append({
                    "name": name,
                    "value": str(val),
                    "domain": ".google.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                })
        elif isinstance(cookies_input, list):
            for item in cookies_input:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookie_dict = {
                        "name": item["name"],
                        "value": str(item["value"]),
                        "domain": item.get("domain", ".google.com"),
                        "path": item.get("path", "/"),
                        "expires": item.get("expires", -1),
                        "httpOnly": item.get("httpOnly", True),
                        "secure": item.get("secure", True),
                        "sameSite": item.get("sameSite", "Lax"),
                    }
                    formatted_cookies.append(cookie_dict)

        storage_data = {
            "cookies": formatted_cookies,
            "origins": [],
        }

        file_path = self.get_storage_path(account_id)
        file_path.write_text(json.dumps(storage_data, indent=2), encoding="utf-8")
        logger.info("Storage state written for account '%s' to %s", account_id, file_path)
        return file_path

    def has_account(self, account_id: str) -> bool:
        return self.get_storage_path(account_id).exists()

    def list_accounts(self) -> List[Dict[str, Any]]:
        accounts = []
        for file in self.token_dir.glob("*_storage_state.json"):
            acc_id = file.name.replace("_storage_state.json", "")
            stat = file.stat()
            accounts.append({
                "account_id": acc_id,
                "file_path": str(file),
                "last_modified": stat.st_mtime,
                "size_bytes": stat.st_size,
            })
        return accounts

    def get_client(self, account_id: str) -> NotebookLMClient:
        """
        Creates a NotebookLMClient initialized with the account's storage state.
        """
        path = self.get_storage_path(account_id)
        if not path.exists():
            alt_path = self.token_dir / f"{account_id}_cookies.json"
            if alt_path.exists():
                path = alt_path
            else:
                raise FileNotFoundError(
                    f"No storage state found for account '{account_id}'. "
                    "Upload cookies via /admin/accounts/setup-cookies first."
                )

        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(content, list):
                storage_data = {"cookies": content, "origins": []}
                path.write_text(json.dumps(storage_data, indent=2), encoding="utf-8")
        except Exception:
            pass

        return NotebookLMClient.from_storage(str(path))

