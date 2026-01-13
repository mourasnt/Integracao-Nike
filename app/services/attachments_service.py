import base64
import os
import uuid
from pathlib import Path
from typing import Optional

from app.config.settings import ATTACHMENTS_DIR, ATTACHMENT_BASE_URL


class AttachmentService:
    """Simple local attachment storage service.

    Saves files under ATTACHMENTS_DIR and exposes a URL using ATTACHMENT_BASE_URL.
    """

    def __init__(self, storage_dir: Optional[str] = None, base_url: Optional[str] = None):
        self.storage_dir = Path(storage_dir or ATTACHMENTS_DIR)
        self.base_url = base_url or ATTACHMENT_BASE_URL
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _make_filename(self, original_name: Optional[str]) -> str:
        suffix = Path(original_name).suffix if original_name else ""
        return f"{uuid.uuid4().hex}{suffix}"

    def save_file(self, data: bytes, original_name: Optional[str] = None) -> dict:
        """Save raw bytes to disk and return metadata with a public URL."""
        filename = self._make_filename(original_name)
        path = self.storage_dir / filename
        with open(path, "wb") as f:
            f.write(data)
        url = f"{self.base_url.rstrip('/')}/{filename}"
        return {"url": url, "path": str(path), "filename": filename}

    def save_base64(self, b64: str, original_name: Optional[str] = None) -> dict:
        data = base64.b64decode(b64)
        return self.save_file(data, original_name)

    def get_base64_from_path(self, path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def get_base64_from_url(self, url: str) -> Optional[str]:
        # only supports local urls from ATTACHMENT_BASE_URL
        if not url.startswith(self.base_url.rstrip('/')) and self.base_url != "/":
            # try with slash normalized
            if not url.startswith(self.base_url):
                return None
        filename = Path(url).name
        p = self.storage_dir / filename
        if not p.exists():
            return None
        return self.get_base64_from_path(str(p))
