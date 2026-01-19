"""Threaded task runner for monitoring Meshy generation progress."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

from PySide6.QtCore import QThread, Signal

from app.core.meshy_client import MeshyClient


@dataclass
class TaskUpdate:
    """Progress update emitted from Meshy task monitoring."""

    task_id: str
    status: str
    progress: Optional[float]
    payload: Dict[str, object]


class TaskRunner(QThread):
    """Runs Meshy task monitoring in a background thread."""

    progressChanged = Signal(int)
    statusChanged = Signal(str)
    taskCompleted = Signal(dict)
    taskFailed = Signal(str)

    def __init__(self, client: MeshyClient, task_id: str, interval_s: float = 3.0) -> None:
        super().__init__()
        self.client = client
        self.task_id = task_id
        self.interval_s = interval_s
        self._running = True

    def run(self) -> None:
        """Execute the monitoring loop."""
        try:
            self._run_streaming()
        except Exception as exc:
            if not self._running:
                return
            try:
                self._run_polling()
            except Exception as poll_exc:
                self.taskFailed.emit(str(poll_exc) or str(exc))

    def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False

    def _run_streaming(self) -> None:
        for payload in self.client.stream_image_to_3d_task(self.task_id):
            if not self._running:
                return
            self._handle_payload(payload)
            status = str(payload.get("status", ""))
            if status in {"succeeded", "failed", "canceled"}:
                return

    def _run_polling(self) -> None:
        while self._running:
            payload = self.client.get_image_to_3d_task(self.task_id)
            self._handle_payload(payload)
            status = str(payload.get("status", ""))
            if status in {"succeeded", "failed", "canceled"}:
                return
            time.sleep(self.interval_s)

    def _handle_payload(self, payload: Dict[str, object]) -> None:
        status = str(payload.get("status", ""))
        if status:
            self.statusChanged.emit(status)
        progress_value = payload.get("progress")
        if progress_value is not None:
            try:
                progress_float = float(progress_value)
                if 0 <= progress_float <= 1:
                    progress_float *= 100
                progress = int(progress_float)
                self.progressChanged.emit(progress)
            except (TypeError, ValueError):
                pass
        if status == "succeeded":
            self.taskCompleted.emit(payload)
        elif status in {"failed", "canceled"}:
            self.taskFailed.emit(f"Task {status}")
