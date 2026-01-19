"""HTTP client wrapper for Meshy OpenAPI endpoints."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Generator

import httpx

BASE_URL = "https://api.meshy.ai"
OPENAPI_PREFIX = "/openapi/v1"


class MeshyApiError(RuntimeError):
    """Represents an HTTP error response from the Meshy API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class MeshyResponse:
    """Lightweight response placeholder for Meshy API interactions."""

    status_code: int
    payload: Dict[str, object]


class MeshyClient:
    """Encapsulates Meshy API calls and SSE streaming logic."""

    def __init__(self, api_key: str, base_url: str = BASE_URL, timeout: float = 15.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{OPENAPI_PREFIX}{path}"

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        body = response.text.strip().replace("\n", " ")
        snippet = body[:200]
        message = f"Meshy API error {response.status_code}: {snippet}"
        raise MeshyApiError(message, status_code=response.status_code)

    def validate_key(self) -> bool:
        """Validate the API key with a lightweight Meshy request."""
        url = self._build_url("/image-to-3d/nonexistent")
        try:
            response = httpx.get(url, headers=self._headers(), timeout=self.timeout)
        except httpx.HTTPError:
            return False
        if response.status_code in {401, 403}:
            return False
        if response.status_code == 404:
            return True
        return 200 <= response.status_code < 300

    def create_image_to_3d_task(self, payload: dict) -> str:
        """Create an Image-to-3D task and return the task id."""
        url = self._build_url("/image-to-3d")
        try:
            response = httpx.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise MeshyApiError(f"Meshy API request failed: {exc}") from exc
        self._raise_for_status(response)
        data = response.json()
        task_id = data.get("result") or data.get("id")
        if not task_id:
            raise MeshyApiError("Meshy API response missing task id", status_code=response.status_code)
        return str(task_id)

    def get_image_to_3d_task(self, task_id: str) -> dict:
        """Retrieve an Image-to-3D task by id."""
        url = self._build_url(f"/image-to-3d/{task_id}")
        try:
            response = httpx.get(url, headers=self._headers(), timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise MeshyApiError(f"Meshy API request failed: {exc}") from exc
        self._raise_for_status(response)
        return response.json()

    def stream_image_to_3d_task(self, task_id: str) -> Generator[dict, None, None]:
        """Stream Image-to-3D task updates via SSE."""
        url = self._build_url(f"/image-to-3d/{task_id}/stream")
        headers = self._headers()
        headers["Accept"] = "text/event-stream"
        try:
            with httpx.Client(timeout=None) as client:
                with client.stream("GET", url, headers=headers) as response:
                    self._raise_for_status(response)
                    event_type = None
                    data_lines: list[str] = []
                    for line in response.iter_lines():
                        if not line:
                            if event_type == "message" and data_lines:
                                payload = "\n".join(data_lines)
                                try:
                                    yield json.loads(payload)
                                except json.JSONDecodeError as exc:
                                    raise MeshyApiError(f"Meshy SSE invalid JSON: {payload}") from exc
                            elif event_type == "error" and data_lines:
                                payload = "\n".join(data_lines)
                                try:
                                    error_payload = json.loads(payload)
                                    message = error_payload.get("message", payload)
                                except json.JSONDecodeError:
                                    message = payload
                                raise MeshyApiError(f"Meshy SSE error: {message}")
                            event_type = None
                            data_lines = []
                            continue
                        decoded = line.decode("utf-8")
                        if decoded.startswith("event:"):
                            event_type = decoded.split(":", 1)[1].strip()
                        elif decoded.startswith("data:"):
                            data_lines.append(decoded.split(":", 1)[1].strip())
        except httpx.HTTPError as exc:
            raise MeshyApiError(f"Meshy API request failed: {exc}") from exc

    def download_file(self, url: str, destination: Path) -> Path:
        """Stream a file download to disk."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with httpx.stream("GET", url, headers=self._headers(), timeout=self.timeout) as response:
                self._raise_for_status(response)
                with destination.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
        except httpx.HTTPError as exc:
            raise MeshyApiError(f"Meshy download failed: {exc}") from exc
        return destination
