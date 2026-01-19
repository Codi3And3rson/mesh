"""Generator view definitions for creating Image-to-3D tasks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt, QStandardPaths, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.image_codec import encode_image_to_data_uri
from app.core.meshy_client import MeshyApiError, MeshyClient
from app.core.storage import TaskHistoryRecord, TaskStorage
from app.core.task_runner import TaskRunner


class GeneratorView(QWidget):
    """Widget responsible for selecting images and task options."""

    openViewerRequested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("generator_view")

        self._api_key: Optional[str] = None
        self._selected_image: Optional[Path] = None
        self._client: Optional[MeshyClient] = None
        self._task_runner: Optional[TaskRunner] = None
        self._last_download: Optional[Path] = None
        self._current_task_id: Optional[str] = None
        self._current_created_at: Optional[str] = None
        self._last_options: Dict[str, object] = {}
        self._last_progress: Optional[float] = None

        self._storage = TaskStorage(self._db_path())

        self._image_button = QPushButton("Select Image")
        self._image_button.clicked.connect(self._select_image)

        self._preview_label = QLabel("No image selected")
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setFixedSize(240, 240)
        self._preview_label.setStyleSheet("border: 1px solid #999;")

        self._prompt_input = QLineEdit()
        self._negative_prompt_input = QLineEdit()

        self._ai_model_input = QComboBox()
        self._ai_model_input.addItems(
            ["", "meshy-3d-v1", "meshy-3d-v2", "meshy-3d-v3", "custom"]
        )
        self._ai_model_custom = QLineEdit()
        self._ai_model_custom.setPlaceholderText("Custom AI model")
        self._ai_model_custom.setEnabled(False)
        self._ai_model_input.currentTextChanged.connect(
            lambda value: self._ai_model_custom.setEnabled(value == "custom")
        )

        self._topology_input = QComboBox()
        self._topology_input.addItems(
            ["", "triangle", "quad", "mixed", "custom"]
        )
        self._topology_custom = QLineEdit()
        self._topology_custom.setPlaceholderText("Custom topology")
        self._topology_custom.setEnabled(False)
        self._topology_input.currentTextChanged.connect(
            lambda value: self._topology_custom.setEnabled(value == "custom")
        )

        self._texture_input = QComboBox()
        self._texture_input.addItems(
            ["", "albedo", "pbr", "custom"]
        )
        self._texture_custom = QLineEdit()
        self._texture_custom.setPlaceholderText("Custom texture mode")
        self._texture_custom.setEnabled(False)
        self._texture_input.currentTextChanged.connect(
            lambda value: self._texture_custom.setEnabled(value == "custom")
        )

        self._should_remesh_toggle = QCheckBox("Remesh")
        self._pbr_toggle = QCheckBox("PBR")

        self._pose_mode_input = QComboBox()
        self._pose_mode_input.addItems(["", "a-pose", "t-pose"])

        self._save_pre_remesh = QCheckBox("Save pre-remeshed model")
        self._save_pre_remesh.setEnabled(False)
        self._should_remesh_toggle.toggled.connect(self._save_pre_remesh.setEnabled)

        self._model_type_input = QComboBox()
        self._model_type_input.addItems(["", "meshy-3d-v2", "meshy-3d-v3", "custom"])
        self._model_type_custom = QLineEdit()
        self._model_type_custom.setPlaceholderText("Custom model type")
        self._model_type_custom.setEnabled(False)
        self._model_type_input.currentTextChanged.connect(
            lambda value: self._model_type_custom.setEnabled(value == "custom")
        )

        self._polycount_input = QSpinBox()
        self._polycount_input.setRange(1000, 200000)
        self._polycount_input.setSingleStep(500)
        self._polycount_input.setValue(20000)

        self._generate_button = QPushButton("Generate")
        self._generate_button.clicked.connect(self._handle_generate)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._status_label = QLabel("Idle")

        self._open_viewer_button = QPushButton("Open in Viewer")
        self._open_viewer_button.setEnabled(False)
        self._open_viewer_button.clicked.connect(self._handle_open_viewer)

        self._build_layout()

    def set_api_key(self, api_key: str) -> None:
        """Provide the API key to use for Meshy requests."""
        self._api_key = api_key
        self._client = MeshyClient(api_key)

    def _db_path(self) -> str:
        base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        return str(base / "task_history.sqlite3")

    def _build_layout(self) -> None:
        image_layout = QHBoxLayout()
        image_layout.addWidget(self._image_button)
        image_layout.addStretch()

        image_group = QGroupBox("Image")
        image_group_layout = QVBoxLayout()
        image_group_layout.addLayout(image_layout)
        image_group_layout.addWidget(self._preview_label)
        image_group.setLayout(image_group_layout)

        form_layout = QFormLayout()
        form_layout.addRow("Prompt", self._prompt_input)
        form_layout.addRow("Negative prompt", self._negative_prompt_input)
        form_layout.addRow("AI model", self._row_with_custom(self._ai_model_input, self._ai_model_custom))
        form_layout.addRow("Topology", self._row_with_custom(self._topology_input, self._topology_custom))
        form_layout.addRow("Pose mode", self._pose_mode_input)
        form_layout.addRow("Model type", self._row_with_custom(self._model_type_input, self._model_type_custom))
        form_layout.addRow("Target polycount", self._polycount_input)
        form_layout.addRow("Texture", self._row_with_custom(self._texture_input, self._texture_custom))

        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(self._should_remesh_toggle)
        toggle_layout.addWidget(self._pbr_toggle)
        toggle_layout.addStretch()

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        options_layout.addLayout(form_layout)
        options_layout.addLayout(toggle_layout)
        options_layout.addWidget(self._save_pre_remesh)
        options_group.setLayout(options_layout)

        status_layout = QVBoxLayout()
        status_layout.addWidget(self._status_label)
        status_layout.addWidget(self._progress_bar)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self._generate_button)
        action_layout.addWidget(self._open_viewer_button)

        layout = QVBoxLayout()
        layout.addWidget(image_group)
        layout.addWidget(options_group)
        layout.addLayout(action_layout)
        layout.addLayout(status_layout)
        layout.addStretch()
        self.setLayout(layout)

    def _row_with_custom(self, combo: QComboBox, custom: QLineEdit) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(combo)
        row.addWidget(custom)
        return container

    def _select_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if not file_path:
            return
        self._selected_image = Path(file_path)
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self._preview_label.setPixmap(
                pixmap.scaled(
                    self._preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def _handle_generate(self) -> None:
        if not self._api_key or not self._client:
            self._status_label.setText("Please log in with an API key first.")
            return
        if not self._selected_image:
            self._status_label.setText("Please select an image.")
            return
        try:
            image_uri = encode_image_to_data_uri(str(self._selected_image))
        except ValueError as exc:
            self._status_label.setText(str(exc))
            return

        options = self._collect_options()
        payload = {"image_url": image_uri, **options}

        try:
            task_id = self._client.create_image_to_3d_task(payload)
        except MeshyApiError as exc:
            self._status_label.setText(str(exc))
            return
        self._current_task_id = task_id
        self._current_created_at = datetime.utcnow().isoformat()
        self._last_options = options

        record = TaskHistoryRecord(
            task_id=task_id,
            created_at=self._current_created_at,
            status="PENDING",
            progress=None,
            thumbnail_url=None,
            model_urls={},
            options=options,
            local_glb_path=None,
        )
        self._storage.upsert(record)

        self._progress_bar.setValue(0)
        self._status_label.setText("Task submitted. Awaiting progress...")
        self._open_viewer_button.setEnabled(False)

        self._task_runner = TaskRunner(self._client, task_id)
        self._task_runner.progressChanged.connect(self._progress_bar.setValue)
        self._task_runner.progressChanged.connect(self._handle_progress_update)
        self._task_runner.statusChanged.connect(self._handle_status_update)
        self._task_runner.taskCompleted.connect(self._handle_task_complete)
        self._task_runner.taskFailed.connect(self._handle_task_failed)
        self._task_runner.start()

    def _collect_options(self) -> Dict[str, object]:
        should_remesh = self._should_remesh_toggle.isChecked()
        payload = {
            "prompt": self._prompt_input.text().strip() or None,
            "negative_prompt": self._negative_prompt_input.text().strip() or None,
            "ai_model": self._custom_combo_value(self._ai_model_input, self._ai_model_custom),
            "should_remesh": should_remesh,
            "enable_pbr": self._pbr_toggle.isChecked(),
            "topology": self._custom_combo_value(self._topology_input, self._topology_custom),
            "target_polycount": self._polycount_input.value(),
            "texture": self._custom_combo_value(self._texture_input, self._texture_custom),
            "pose_mode": self._pose_mode_input.currentText().strip() or None,
            "save_pre_remeshed_model": self._save_pre_remesh.isChecked() if should_remesh else None,
            "model_type": self._custom_combo_value(self._model_type_input, self._model_type_custom),
        }
        return {key: value for key, value in payload.items() if value not in {None, ""}}

    def _custom_combo_value(self, combo: QComboBox, custom: QLineEdit) -> Optional[str]:
        value = combo.currentText().strip()
        if value == "custom":
            return custom.text().strip() or None
        return value or None

    def _handle_status_update(self, status: str) -> None:
        self._status_label.setText(f"Status: {status}")
        if not self._current_task_id:
            return
        record = TaskHistoryRecord(
            task_id=self._current_task_id,
            created_at=self._current_created_at or datetime.utcnow().isoformat(),
            status=status,
            progress=self._last_progress,
            thumbnail_url=None,
            model_urls={},
            options=self._last_options,
            local_glb_path=None,
        )
        self._storage.upsert(record)

    def _handle_progress_update(self, progress: int) -> None:
        self._last_progress = float(progress)
        if not self._current_task_id:
            return
        record = TaskHistoryRecord(
            task_id=self._current_task_id,
            created_at=self._current_created_at or datetime.utcnow().isoformat(),
            status="IN_PROGRESS",
            progress=self._last_progress,
            thumbnail_url=None,
            model_urls={},
            options=self._last_options,
            local_glb_path=None,
        )
        self._storage.upsert(record)

    def _handle_task_complete(self, payload: Dict[str, object]) -> None:
        model_urls = payload.get("model_urls") or {}
        thumbnail_url = payload.get("thumbnail_url")
        status = str(payload.get("status", "succeeded"))
        record = TaskHistoryRecord(
            task_id=self._current_task_id or str(payload.get("id") or payload.get("task_id") or ""),
            created_at=str(payload.get("created_at") or datetime.utcnow().isoformat()),
            status=status,
            progress=self._last_progress,
            thumbnail_url=thumbnail_url,
            model_urls=model_urls,
            options=payload.get("options") or self._last_options,
            local_glb_path=self._last_download.as_posix() if self._last_download else None,
        )
        self._storage.upsert(record)
        self._status_label.setText("Task complete. Downloading model...")
        self._download_glb(model_urls)

    def _handle_task_failed(self, message: str) -> None:
        self._status_label.setText(f"Task failed: {message}")

    def _download_glb(self, model_urls: Dict[str, object]) -> None:
        url = None
        if isinstance(model_urls, dict):
            url = model_urls.get("glb") or next(iter(model_urls.values()), None)
        if not url or not self._client:
            self._status_label.setText("Task finished but no model URL was returned.")
            return
        download_dir = Path(
            QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        ) / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        destination = download_dir / "meshy_model.glb"
        try:
            self._last_download = self._client.download_file(str(url), destination)
        except MeshyApiError as exc:
            self._status_label.setText(str(exc))
            return
        if self._current_task_id:
            record = TaskHistoryRecord(
                task_id=self._current_task_id,
                created_at=self._current_created_at or datetime.utcnow().isoformat(),
                status="succeeded",
                progress=self._last_progress,
                thumbnail_url=None,
                model_urls=model_urls,
                options=self._last_options,
                local_glb_path=self._last_download.as_posix(),
            )
            self._storage.upsert(record)
        self._open_viewer_button.setEnabled(True)
        self._status_label.setText("Model downloaded.")

    def _handle_open_viewer(self) -> None:
        if self._last_download:
            self.openViewerRequested.emit(self._last_download.as_uri())
