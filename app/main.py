"""Application entry point and main window wiring."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.secrets import load_key
from app.ui.generator_view import GeneratorView
from app.ui.history_view import HistoryView
from app.ui.login_view import LoginView
from app.ui.viewer_view import ViewerView


class MainWindow(QMainWindow):
    """Main application window with stacked navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Meshy Desktop Lab")

        self._stack = QStackedWidget()
        self._login_view = LoginView()
        self._generator_view = GeneratorView()
        self._history_view = HistoryView()
        self._viewer_view = ViewerView()

        self._stack.addWidget(self._login_view)
        self._stack.addWidget(self._generator_view)
        self._stack.addWidget(self._history_view)
        self._stack.addWidget(self._viewer_view)

        self._login_view.loginSuccess.connect(self._handle_login)
        self._generator_view.openViewerRequested.connect(self._open_viewer)
        self._history_view.openViewerRequested.connect(self._open_viewer)

        self._nav_login = QPushButton("Login")
        self._nav_generator = QPushButton("Generator")
        self._nav_history = QPushButton("History")
        self._nav_viewer = QPushButton("Viewer")

        self._nav_login.clicked.connect(lambda: self._stack.setCurrentWidget(self._login_view))
        self._nav_generator.clicked.connect(
            lambda: self._stack.setCurrentWidget(self._generator_view)
        )
        self._nav_history.clicked.connect(lambda: self._stack.setCurrentWidget(self._history_view))
        self._nav_viewer.clicked.connect(lambda: self._stack.setCurrentWidget(self._viewer_view))

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self._nav_login)
        nav_layout.addWidget(self._nav_generator)
        nav_layout.addWidget(self._nav_history)
        nav_layout.addWidget(self._nav_viewer)
        nav_layout.addStretch()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(nav_layout)
        layout.addWidget(self._stack)
        layout.setContentsMargins(8, 8, 8, 8)
        self.setCentralWidget(container)

        self._bootstrap_session()

    def _bootstrap_session(self) -> None:
        api_key = load_key()
        if api_key:
            self._handle_login(api_key)
        else:
            self._stack.setCurrentWidget(self._login_view)

    def _handle_login(self, api_key: str) -> None:
        self._generator_view.set_api_key(api_key)
        self._history_view.set_api_key(api_key)
        self._stack.setCurrentWidget(self._generator_view)

    def _open_viewer(self, url: str) -> None:
        if url.startswith("file://"):
            self._viewer_view.load_glb(url)
        else:
            self._viewer_view.load_glb(url)
        self._stack.setCurrentWidget(self._viewer_view)


def main() -> None:
    """Launch the Qt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Meshy Desktop Lab")
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
