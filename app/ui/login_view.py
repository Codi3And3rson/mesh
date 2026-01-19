"""Login view definitions for API key entry and validation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.meshy_client import MeshyClient
from app.core.secrets import delete_key, load_key, save_key


class LoginView(QWidget):
    """Widget responsible for collecting and storing Meshy API credentials."""

    loginSuccess = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("login_view")

        self._api_input = QLineEdit()
        self._api_input.setPlaceholderText("Enter Meshy API key")
        self._api_input.setEchoMode(QLineEdit.Password)

        self._toggle_button = QToolButton()
        self._toggle_button.setText("Show")
        self._toggle_button.setCheckable(True)
        self._toggle_button.clicked.connect(self._toggle_password)

        self._continue_button = QPushButton("Continue")
        self._continue_button.clicked.connect(self._handle_continue)

        self._forget_button = QPushButton("Forget Key")
        self._forget_button.clicked.connect(self._handle_forget)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._build_layout()
        self._load_saved_key()

    def _build_layout(self) -> None:
        input_layout = QHBoxLayout()
        input_layout.addWidget(self._api_input)
        input_layout.addWidget(self._toggle_button)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self._continue_button)
        button_layout.addWidget(self._forget_button)

        layout = QVBoxLayout()
        layout.addLayout(input_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self._status_label)
        layout.addStretch()
        self.setLayout(layout)

    def _load_saved_key(self) -> None:
        saved = load_key()
        if saved:
            self._api_input.setText(saved)
            self._status_label.setText("Loaded saved API key.")

    def _toggle_password(self) -> None:
        if self._toggle_button.isChecked():
            self._api_input.setEchoMode(QLineEdit.Normal)
            self._toggle_button.setText("Hide")
        else:
            self._api_input.setEchoMode(QLineEdit.Password)
            self._toggle_button.setText("Show")

    def _handle_continue(self) -> None:
        api_key = self._api_input.text().strip()
        if not api_key:
            self._status_label.setText("Please enter an API key.")
            return
        self._status_label.setText("Validating API key...")
        client = MeshyClient(api_key)
        if client.validate_key():
            save_key(api_key)
            self._status_label.setText("API key saved.")
            self.loginSuccess.emit(api_key)
        else:
            self._status_label.setText("Invalid API key. Please try again.")

    def _handle_forget(self) -> None:
        delete_key()
        self._api_input.clear()
        self._status_label.setText("Saved API key removed.")
