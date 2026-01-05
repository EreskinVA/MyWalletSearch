#!/usr/bin/env python3
"""
DEPRECATED: используйте `vanity_gui_unified.py`.

Этот файл оставлен как совместимый entrypoint: `python vanity_gui.py`.
"""

from __future__ import annotations

from vanity_gui_unified import main


if __name__ == "__main__":
    # Исторически Windows GUI был GPU-ориентированным.
    raise SystemExit(main(default_backend="gpu", default_workdir="runs"))


