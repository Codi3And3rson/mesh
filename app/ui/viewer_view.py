"""Viewer view definitions for embedded 3D previews."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget


class ViewerView(QWidget):
    """Widget responsible for displaying Meshy-generated 3D assets."""

    load_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("viewer_view")

        self._web_view = QWebEngineView(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)

        viewer_html = (
            Path(__file__).resolve().parents[1]
            / "resources"
            / "viewer"
            / "index.html"
        )
        self._web_view.setUrl(QUrl.fromLocalFile(str(viewer_html)))

    def load_glb(self, path: str) -> None:
        """Load a GLB file into the embedded Three.js viewer."""
        file_url = path
        if not path.startswith("file://"):
            file_url = QUrl.fromLocalFile(path).toString()
        payload = json.dumps(file_url)
        self._web_view.page().runJavaScript(f"window.loadModel({payload})")
        self.load_requested.emit(file_url)
