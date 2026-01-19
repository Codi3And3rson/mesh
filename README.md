# Meshy Desktop Lab

Cross-platform desktop app scaffold built with Python + PySide6. The project includes UI and core module stubs for Meshy API access, task monitoring, storage, and a bundled 3D viewer.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

## Meshy API notes

- Base path: `https://api.meshy.ai/openapi/v1/...`
- Auth header: `Authorization: Bearer <API_KEY>`
- Test-mode key supported (use the documented test-mode key from Meshy).
- Free tier task creation ended March 20, 2025. Use a paid key or the test-mode key for sample results.

## Packaging with PyInstaller

Install PyInstaller:

```bash
pip install pyinstaller
```

### Build commands

Windows:

```bash
pyinstaller --noconsole --name MeshyDesktopLab ^
  --add-data "app/resources;app/resources" ^
  --collect-all PySide6 ^
  --collect-all PySide6.QtWebEngineCore ^
  app/main.py
```

macOS:

```bash
pyinstaller --windowed --name MeshyDesktopLab \
  --add-data "app/resources:app/resources" \
  --collect-all PySide6 \
  --collect-all PySide6.QtWebEngineCore \
  app/main.py
```

Linux:

```bash
pyinstaller --noconsole --name MeshyDesktopLab \
  --add-data "app/resources:app/resources" \
  --collect-all PySide6 \
  --collect-all PySide6.QtWebEngineCore \
  app/main.py
```

### PyInstaller spec adjustments

If PyInstaller misses WebEngine assets in your environment, create a spec file and add explicit data/binaries. A minimal addition (in `datas` and `binaries`) looks like:

```python
from PySide6 import QtWebEngineCore
from PySide6.QtCore import QLibraryInfo
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = [
    *collect_data_files("PySide6"),
    *collect_data_files("PySide6.QtWebEngineCore"),
    ("app/resources", "app/resources"),
    (QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath), "qt_data"),
    (QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath), "qt_translations"),
]
binaries = [
    *collect_dynamic_libs("PySide6"),
    *collect_dynamic_libs("PySide6.QtWebEngineCore"),
]
```

### Qt WebEngine deployment notes

Qt WebEngine requires shipping the helper process and resources alongside your app. After building with PyInstaller, verify the following are bundled in your dist directory:

- `QtWebEngineProcess` executable
- `resources/` and `translations/` folders from Qt
- `qtwebengine_resources.pak`, `qtwebengine_resources_100p.pak`, `qtwebengine_resources_200p.pak`
- `qtwebengine_devtools_resources.pak`
- `locales/` (Chromium locale packs)

For macOS, ensure the `QtWebEngineProcess.app` helper is signed and includes appropriate entitlements (e.g., network access). If you notarize the app, sign the helper bundle and the main app with the same identity to avoid runtime failures.

Refer to Qt for Python deployment guidance and the Qt WebEngine deployment notes for the latest OS-specific steps.

### Viewer assets

The Three.js viewer HTML/JS is bundled via `--add-data` so the viewer works offline without CDN dependencies. If you prefer Qt Resources, add the HTML to a `.qrc` file and update the `QWebEngineView` load path accordingly.

### API keys and build artifacts

No API keys are stored in source or build artifacts. The app only reads keys from OS secure storage (keyring) at runtime, and PyInstaller bundles do not embed any keys.
