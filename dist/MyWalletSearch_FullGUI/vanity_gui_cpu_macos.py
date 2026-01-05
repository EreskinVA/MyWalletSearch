#!/usr/bin/env python3
"""
DEPRECATED: используйте `vanity_gui_unified.py`.

Этот файл оставлен как совместимый entrypoint: `python vanity_gui_cpu_macos.py`.
"""

from __future__ import annotations

from vanity_gui_unified import main


if __name__ == "__main__":
    # Исторически macOS GUI был CPU-ориентированным.
    raise SystemExit(main(default_backend="cpu", default_workdir="runs"))


