"""Shared dataclass models for Meshy tasks and options."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ImageTo3DOptions:
    """Configuration options for Meshy image-to-3d requests."""

    prompt: Optional[str] = None
    pose_mode: Optional[str] = None
    save_pre_remeshed_model: Optional[bool] = None
    model_type: Optional[str] = None
    extra: Dict[str, object] = field(default_factory=dict)


@dataclass
class TaskStatus:
    """Represents the latest status snapshot of a Meshy task."""

    task_id: str
    status: str
    progress: Optional[float] = None
    created_at: Optional[str] = None
    thumbnail_url: Optional[str] = None
    model_urls: Dict[str, object] = field(default_factory=dict)
    options: Dict[str, object] = field(default_factory=dict)


@dataclass
class TaskSummary:
    """Lightweight summary of a stored task."""

    task_id: str
    status: str
    created_at: str


@dataclass
class TaskRecord:
    """Full task history record for persistence."""

    task_id: str
    created_at: str
    status: str
    progress: Optional[int] = None
    thumbnail_url: Optional[str] = None
    model_urls: Dict[str, object] = field(default_factory=dict)
    options: Dict[str, object] = field(default_factory=dict)
    local_glb_path: Optional[str] = None
