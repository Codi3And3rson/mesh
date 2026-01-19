"""History view definitions for listing and selecting previous tasks."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import Qt, QStandardPaths, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.meshy_client import MeshyApiError, MeshyClient
from app.core.storage import TaskHistoryRecord, TaskStorage


class HistoryView(QWidget):
    """Widget responsible for rendering stored task history."""

    openViewerRequested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("history_view")
        self._api_key: Optional[str] = None
        self._client: Optional[MeshyClient] = None

        self._storage = TaskStorage(self._db_path())
        self._network = QNetworkAccessManager(self)
        self._thumbnail_replies: Dict[int, QLabel] = {}

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._handle_selection)

        self._status_label = QLabel("Select a task to see details.")
        self._open_button = QPushButton("Open in Viewer")
        self._open_button.setEnabled(False)
        self._open_button.clicked.connect(self._handle_open)

        self._build_layout()
        self.refresh()

    def set_api_key(self, api_key: str) -> None:
        """Set the API key for refreshing task status from Meshy."""
        self._api_key = api_key
        self._client = MeshyClient(api_key)

    def refresh(self) -> None:
        """Reload the task list from storage."""
        self._list.clear()
        for record in self._storage.list_all():
            self._add_task_item(record)

    def _db_path(self) -> str:
        base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        return str(base / "task_history.sqlite3")

    def _build_layout(self) -> None:
        layout = QVBoxLayout()
        layout.addWidget(self._list)
        layout.addWidget(self._status_label)
        layout.addWidget(self._open_button)
        self.setLayout(layout)

    def _add_task_item(self, record: TaskHistoryRecord) -> None:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, record)

        widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(6, 6, 6, 6)

        thumbnail = QLabel("No thumbnail")
        thumbnail.setFixedSize(64, 64)
        thumbnail.setAlignment(Qt.AlignCenter)
        thumbnail.setStyleSheet("border: 1px solid #ccc;")

        text = QLabel(self._format_row_text(record))
        text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        row_layout.addWidget(thumbnail)
        row_layout.addWidget(text, 1)
        widget.setLayout(row_layout)

        item.setSizeHint(widget.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)

        if record.thumbnail_url:
            reply = self._network.get(QNetworkRequest(QUrl(record.thumbnail_url)))
            reply_id = id(reply)
            self._thumbnail_replies[reply_id] = thumbnail
            reply.finished.connect(lambda r=reply, rid=reply_id: self._handle_thumbnail(r, rid))

    def _format_row_text(self, record: TaskHistoryRecord) -> str:
        created_at = record.created_at
        try:
            created_at = datetime.fromisoformat(record.created_at).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
        return f"{record.status} • {created_at}"

    def _handle_thumbnail(self, reply, reply_id: int) -> None:
        label = self._thumbnail_replies.pop(reply_id, None)
        if not label:
            reply.deleteLater()
            return
        if reply.error():
            label.setText("No preview")
        else:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(bytes(data))
            if not pixmap.isNull():
                label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        reply.deleteLater()

    def _handle_selection(self) -> None:
        items = self._list.selectedItems()
        if not items:
            self._open_button.setEnabled(False)
            return
        record = items[0].data(Qt.UserRole)
        if not record:
            return
        self._refresh_task_status(record)

    def _refresh_task_status(self, record: TaskHistoryRecord) -> None:
        if not self._client:
            self._status_label.setText("Log in to refresh task status.")
            self._update_open_state(record)
            return
        try:
            payload = self._client.get_image_to_3d_task(record.task_id)
        except MeshyApiError as exc:
            self._status_label.setText(str(exc))
            self._update_open_state(record)
            return
        updated = TaskHistoryRecord(
            task_id=record.task_id,
            created_at=str(payload.get("created_at") or record.created_at),
            status=str(payload.get("status") or record.status),
            progress=payload.get("progress"),
            thumbnail_url=payload.get("thumbnail_url") or record.thumbnail_url,
            model_urls=payload.get("model_urls") or record.model_urls,
            options=payload.get("options") or record.options,
            local_glb_path=record.local_glb_path,
        )
        self._storage.upsert(updated)
        self._status_label.setText(f"Status: {updated.status}")
        self.refresh()
        self._update_open_state(updated)

    def _update_open_state(self, record: TaskHistoryRecord) -> None:
        url = self._resolve_model_url(record)
        if record.local_glb_path or url:
            self._open_button.setEnabled(True)
        else:
            self._open_button.setEnabled(False)
            self._status_label.setText("No downloadable model available (missing or expired URL).")

    def _resolve_model_url(self, record: TaskHistoryRecord) -> Optional[str]:
        model_urls = record.model_urls or {}
        url = None
        if isinstance(model_urls, dict):
            url = model_urls.get("glb") or next(iter(model_urls.values()), None)
        if not url:
            return None
        if self._is_url_expired(url):
            return None
        return str(url)

    def _is_url_expired(self, url: str) -> bool:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        expires = params.get("Expires") or params.get("expires")
        if not expires:
            return False
        try:
            expiry = int(expires[0])
        except (TypeError, ValueError):
            return False
        return time.time() > expiry

    def _handle_open(self) -> None:
        items = self._list.selectedItems()
        if not items:
            return
        record = items[0].data(Qt.UserRole)
        if not record:
            return
        if record.local_glb_path:
            self.openViewerRequested.emit(Path(record.local_glb_path).as_uri())
            return
        url = self._resolve_model_url(record)
        if url:
            self.openViewerRequested.emit(url)
        else:
            self._status_label.setText("Model URL expired or unavailable.")
            self._open_button.setEnabled(False)
