#!/usr/bin/env python3
"""
Единый GUI-лаунчер для VanitySearch (Windows/macOS, CPU/GPU).

Цели:
- один скрипт вместо vanity_gui.py (Windows/GPU) и vanity_gui_cpu_macos.py (macOS/CPU)
- единое именование файлов в workdir (по умолчанию runs/)
- выбор backend: CPU/GPU (с учётом доступности бинарника/платформы)
- build/start/stop/tail/progress/found/analyze

Без внешних зависимостей: tkinter + стандартная библиотека.
Если tkinter недоступен (часто на macOS Homebrew/pyenv без tk) — есть CLI-режим.
"""

from __future__ import annotations

import os
import re
import sys
import time
import signal
import threading
import subprocess
import queue
from dataclasses import dataclass
from pathlib import Path

HAS_TK = True
try:
    from tkinter import (  # type: ignore
        Tk,
        ttk,
        StringVar,
        IntVar,
        BooleanVar,
        Text,
        END,
        BOTH,
        LEFT,
        RIGHT,
        X,
        Y,
        VERTICAL,
        HORIZONTAL,
        Menu,
        TclError,
    )
    from tkinter import filedialog  # type: ignore
except Exception as e:  # noqa: BLE001
    HAS_TK = False
    TK_IMPORT_ERROR = e

HAS_ANALYZER = True
try:
    import analyze_seg_74_5_76 as vs_analyzer  # type: ignore
except Exception as e:  # noqa: BLE001
    HAS_ANALYZER = False
    ANALYZER_IMPORT_ERROR = e


REPO_ROOT = Path(__file__).resolve().parent
SHOW_PROGRESS_PY = REPO_ROOT / "show_segment_progress.py"


@dataclass
class DerivedFiles:
    base: str
    workdir: Path
    seg_file: Path
    progress_file: Path
    out_file: Path
    log_file: Path
    patterns_file: Path
    pid_file: Path


def _is_windows() -> bool:
    return sys.platform == "win32"


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _platform_label() -> str:
    if _is_windows():
        return "Windows"
    if _is_macos():
        return "macOS"
    return sys.platform


def _safe_decode(b: bytes) -> str:
    """
    Декодирует байты из логов/подпроцессов максимально устойчиво.
    На Windows вывод может быть смешанным (UTF-8/ANSI), поэтому используем errors=replace.
    """
    if b is None:
        return ""
    try:
        return b.decode("utf-8", errors="replace")
    except Exception:
        pass
    for enc in ("utf-8-sig", "cp1251", "cp866"):
        try:
            return b.decode(enc, errors="replace")
        except Exception:
            pass
    return b.decode("latin-1", errors="replace")


def tail_lines(path: Path, n: int) -> str:
    if not path.exists():
        return f"[tail] файл не найден: {path}"
    if n <= 0:
        return ""
    block = 8192
    data = b""
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        while pos > 0 and data.count(b"\n") <= n + 2:
            read = min(block, pos)
            pos -= read
            f.seek(pos)
            data = f.read(read) + data
    text = _safe_decode(data)
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def run_capture(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            env=env,
            shell=False,
        )
        return p.returncode, _safe_decode(p.stdout or b"")
    except FileNotFoundError:
        return 127, f"Команда не найдена: {args[0]}"
    except Exception as e:
        return 1, f"Ошибка запуска {args}: {e}"


def _normalize_pattern_line(line: str) -> str:
    s = (line or "").strip()
    if not s:
        return ""
    if s.startswith("#") or s.startswith(";"):
        return ""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s


def _format_cmd_for_display(args: list[str]) -> str:
    def q(a: str) -> str:
        if a is None:
            return ""
        need = (" " in a) or ("\t" in a) or ("*" in a) or ("?" in a)
        if not need:
            return a
        a2 = a.replace('"', r"\"")
        return f"\"{a2}\""

    return " ".join(q(a) for a in args)


def attach_context_menu(widget, *, allow_edit: bool) -> None:
    """Контекстное меню Copy/Cut/Paste/Select All + горячие клавиши (Ctrl/Command)."""
    menu = Menu(widget, tearoff=0)

    def is_text(w) -> bool:
        return isinstance(w, Text)

    def do_copy():
        try:
            widget.event_generate("<<Copy>>")
        except TclError:
            pass

    def do_cut():
        if not allow_edit:
            return
        try:
            widget.event_generate("<<Cut>>")
        except TclError:
            pass

    def do_paste():
        if not allow_edit:
            return
        try:
            widget.event_generate("<<Paste>>")
        except TclError:
            pass

    def do_select_all():
        try:
            if is_text(widget):
                widget.tag_add("sel", "1.0", "end-1c")
                widget.mark_set("insert", "1.0")
                widget.see("insert")
            else:
                widget.selection_range(0, END)
                widget.icursor(0)
        except Exception:
            pass

    menu.add_command(label="Copy", command=do_copy)
    if allow_edit:
        menu.add_command(label="Cut", command=do_cut)
        menu.add_command(label="Paste", command=do_paste)
    menu.add_separator()
    menu.add_command(label="Select All", command=do_select_all)

    def popup(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    widget.bind("<Button-3>", popup, add=True)
    widget.bind("<Button-2>", popup, add=True)

    # Ctrl+A / Command+A
    def ctrl_a(_event):
        do_select_all()
        return "break"

    widget.bind("<Control-a>", ctrl_a, add=True)
    widget.bind("<Control-A>", ctrl_a, add=True)
    widget.bind("<Command-a>", ctrl_a, add=True)
    widget.bind("<Command-A>", ctrl_a, add=True)

    # Command/Ctrl C/X/V на macOS удобнее
    widget.bind("<Command-c>", lambda _e: do_copy(), add=True)
    widget.bind("<Command-C>", lambda _e: do_copy(), add=True)
    if allow_edit:
        widget.bind("<Command-x>", lambda _e: do_cut(), add=True)
        widget.bind("<Command-X>", lambda _e: do_cut(), add=True)
        widget.bind("<Command-v>", lambda _e: do_paste(), add=True)
        widget.bind("<Command-V>", lambda _e: do_paste(), add=True)


def sysctl_ncpu() -> int:
    if not _is_macos():
        return os.cpu_count() or 1
    rc, out = run_capture(["sysctl", "-n", "hw.ncpu"])
    if rc == 0:
        try:
            return int(out.strip())
        except Exception:
            pass
    return os.cpu_count() or 1


def detect_compute_cap() -> str:
    """
    Пытаемся получить compute capability через nvidia-smi.
    Работает на Windows/Linux при наличии NVIDIA драйверов.
    На macOS чаще всего вернёт пусто.
    """
    rc, out = run_capture(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"])
    if rc == 0:
        cc = (out.strip().splitlines()[:1] or [""])[0].strip()
        if re.match(r"^\d+(\.\d+)?$", cc):
            return cc
    return ""


def find_windows_vanity_exe(prefer_sm61: bool) -> Path | None:
    candidates: list[Path] = []
    if prefer_sm61:
        candidates.append(REPO_ROOT / "x64" / "ReleaseSM61" / "VanitySearch.exe")
    candidates.append(REPO_ROOT / "x64" / "Release" / "VanitySearch.exe")
    candidates.append(REPO_ROOT / "x64" / "ReleaseSM61" / "VanitySearch.exe")
    for c in candidates:
        if c.exists():
            return c
    return None


def find_vanity_binary(prefer_sm61: bool) -> Path | None:
    if _is_windows():
        return find_windows_vanity_exe(prefer_sm61)
    # macOS/posix
    p = REPO_ROOT / "VanitySearch"
    return p if p.exists() else None


def detect_sm_count_windows(vanity_exe: Path) -> int:
    rc, out = run_capture([str(vanity_exe), "-l"], cwd=vanity_exe.parent)
    if rc != 0 and not out:
        return 0
    m = re.search(r"\((\d+)x\d+\s+cores\)", out)
    if m:
        return int(m.group(1))
    return 0


def default_grid_for_current_gpu_windows(vanity_exe: Path) -> str:
    sm = detect_sm_count_windows(vanity_exe)
    if sm > 0:
        return f"{sm * 8},128"
    return "64,128"


def msbuild_path() -> Path | None:
    p = Path(r"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe")
    if p.exists():
        return p
    return None


def rebuild(output_cb, stop_event: threading.Event, *, backend: str, ccap: str | None = None) -> int:
    """Build на текущей платформе с учётом backend."""
    backend = (backend or "").strip().lower() or "cpu"
    if _is_windows():
        msb = msbuild_path()
        if not msb:
            output_cb("MSBuild.exe не найден. Установите Visual Studio Build Tools/VS.\n")
            return 1

        cc = detect_compute_cap()
        prefer_sm61 = cc.strip() == "6.1"
        config = "ReleaseSM61" if prefer_sm61 else "Release"
        if backend == "cpu":
            output_cb("[BUILD] Примечание: на Windows этот проект собирается через MSBuild как GPU-версия (VanitySearch.exe).\n")
        output_cb(f"GPU compute_cap={cc or 'N/A'} -> rebuild {config}|x64\n")

        args = [
            str(msb),
            "VanitySearch.sln",
            "/t:Rebuild",
            f"/p:Configuration={config}",
            "/p:Platform=x64",
            "/m",
            "/v:m",
        ]
        try:
            p = subprocess.Popen(
                args,
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
            )
        except Exception as e:
            output_cb(f"Не удалось запустить MSBuild: {e}\n")
            return 1
        assert p.stdout is not None
        while True:
            if stop_event.is_set():
                try:
                    p.terminate()
                except Exception:
                    pass
                return 130
            chunk = p.stdout.readline()
            if not chunk:
                break
            output_cb(_safe_decode(chunk))
        return p.wait()

    # macOS/posix: make cpu / make gpu=1 CCAP=...
    try:
        rc1, out1 = run_capture(["make", "clean"], cwd=REPO_ROOT)
        output_cb(out1 + ("" if out1.endswith("\n") else "\n"))
        if rc1 != 0:
            output_cb(f"[BUILD] make clean failed rc={rc1}\n")
            return rc1
        n = sysctl_ncpu()
        if backend == "gpu":
            cc = (ccap or "").strip() or detect_compute_cap()
            if not cc:
                output_cb("[BUILD] GPU build выбран, но CCAP не задан и не удалось определить через nvidia-smi.\n")
                output_cb("[BUILD] Укажи CCAP (например 8.9 для RTX 4090) в поле CCAP и повтори.\n")
                return 2
            args = ["make", "gpu=1", f"CCAP={cc}", "all", f"-j{n}"]
            output_cb(f"[BUILD] make gpu=1 CCAP={cc} all -j{n}\n")
        else:
            args = ["make", f"-j{n}"]
            output_cb(f"[BUILD] make -j{n}\n")
        rc2, out2 = run_capture(args, cwd=REPO_ROOT)
        output_cb(out2 + ("" if out2.endswith("\n") else "\n"))
        return rc2
    except Exception as e:  # noqa: BLE001
        output_cb(f"[BUILD] failed: {e}\n")
        return 1


def open_folder(path: Path) -> None:
    if _is_windows():
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    if _is_macos():
        subprocess.run(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    subprocess.run(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop_pid(pid: int) -> None:
    if pid <= 0:
        return
    if _is_windows():
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.25)
    except Exception:
        pass
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def stop_all_processes() -> None:
    if _is_windows():
        subprocess.run(["taskkill", "/F", "/T", "/IM", "VanitySearch.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    subprocess.run(["pkill", "-f", "VanitySearch"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class VanityUnifiedGUI:
    def __init__(self, *, default_backend: str | None = None, default_workdir: str | None = None) -> None:
        if not HAS_TK:
            raise RuntimeError("tkinter is not available")

        self.root = Tk()
        self.root.title(f"VanitySearch GUI (Unified) — {_platform_label()}")
        self.root.geometry("1120x820")

        # settings
        self.platform = StringVar(value=_platform_label())
        if default_backend:
            backend0 = default_backend
        else:
            backend0 = "gpu" if _is_windows() else "cpu"
        self.backend = StringVar(value=backend0)  # "cpu" | "gpu"

        self.base_name = StringVar(value="puzzle71_69_72" if _is_windows() else "cpu_run")
        self.prefix = StringVar(value="1PWo3JeB")
        self.suffix = StringVar(value="")
        self.target = StringVar(value="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU")
        self.bits = IntVar(value=71)
        self.cpu_threads = IntVar(value=(2 if _is_windows() else max(1, sysctl_ncpu() - 1)))
        self.maxfound = IntVar(value=1_000_000)
        self.autosave = IntVar(value=120)
        self.auto_resume = BooleanVar(value=True)
        self.tail_n = IntVar(value=40)

        # GPU-only
        self.gpuid = StringVar(value="0")
        self.grid = StringVar(value="")
        # posix GPU build
        self.ccap = StringVar(value="8.9")

        # paths
        wd = default_workdir or "runs"
        self.workdir_rel = StringVar(value=wd)
        self.binary_override = StringVar(value="")  # optional absolute/relative path

        # runtime
        self._proc_lock = threading.Lock()
        self._procs: dict[str, subprocess.Popen] = {}
        self._rebuild_thread: threading.Thread | None = None
        self._stop_rebuild = threading.Event()
        self._auto_refresh = BooleanVar(value=True)
        self._ui_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

        self._build_ui()
        self._init_defaults()
        self.root.after(100, self._drain_ui_queue)
        self._schedule_refresh()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill=X, padx=10, pady=8)

        btn_row = ttk.Frame(top)
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text="STOP (текущая база)", command=self.stop_search).pack(side=LEFT)
        ttk.Button(btn_row, text="STOP ALL", command=self.kill_all).pack(side=LEFT, padx=6)
        ttk.Button(btn_row, text="START", command=self.start_search).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text=("REBUILD" if _is_windows() else "BUILD"), command=self.rebuild).pack(side=LEFT)
        ttk.Button(btn_row, text="Tail log", command=self.show_tail).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="Progress", command=self.show_progress).pack(side=LEFT)
        ttk.Button(btn_row, text="Показать найденные", command=self.show_found).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="Анализировать", command=self.run_analysis).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="Open runs folder", command=self.open_runs_folder).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="Очистить вывод", command=self.clear_output).pack(side=RIGHT)

        row0 = ttk.Frame(top)
        row0.pack(fill=X, pady=(8, 0))
        ttk.Label(row0, text="Platform:").pack(side=LEFT)
        ttk.Label(row0, textvariable=self.platform, foreground="gray").pack(side=LEFT, padx=6)
        ttk.Label(row0, text="Backend:").pack(side=LEFT, padx=(14, 0))
        cb = ttk.Combobox(row0, textvariable=self.backend, values=("cpu", "gpu"), width=8, state="readonly")
        cb.pack(side=LEFT, padx=6)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._on_backend_changed())
        ttk.Checkbutton(row0, text="автообновление", variable=self._auto_refresh).pack(side=LEFT, padx=10)

        row_paths = ttk.Frame(top)
        row_paths.pack(fill=X, pady=(6, 0))
        ttk.Label(row_paths, text="Workdir (relative to repo):").pack(side=LEFT)
        e_wd = ttk.Entry(row_paths, textvariable=self.workdir_rel, width=20)
        e_wd.pack(side=LEFT, padx=6)
        attach_context_menu(e_wd, allow_edit=True)
        ttk.Label(row_paths, text="Binary override (optional):").pack(side=LEFT, padx=(14, 0))
        e_bin = ttk.Entry(row_paths, textvariable=self.binary_override, width=42)
        e_bin.pack(side=LEFT, padx=6)
        attach_context_menu(e_bin, allow_edit=True)
        ttk.Button(row_paths, text="Browse...", command=self.pick_binary).pack(side=LEFT)

        row1 = ttk.Frame(top)
        row1.pack(fill=X, pady=(8, 0))
        ttk.Label(row1, text="Базовое имя файлов:").pack(side=LEFT)
        e_base = ttk.Entry(row1, textvariable=self.base_name, width=28)
        e_base.pack(side=LEFT, padx=6)
        attach_context_menu(e_base, allow_edit=True)
        self.groups_label = ttk.Label(row1, text="Groups: 0", foreground="gray")
        self.groups_label.pack(side=LEFT, padx=10)

        row2 = ttk.Frame(top)
        row2.pack(fill=X, pady=(6, 0))
        ttk.Label(row2, text="Паттерн: prefix").pack(side=LEFT)
        e_pref = ttk.Entry(row2, textvariable=self.prefix, width=18)
        e_pref.pack(side=LEFT, padx=6)
        attach_context_menu(e_pref, allow_edit=True)
        ttk.Label(row2, text="suffix").pack(side=LEFT)
        e_suf = ttk.Entry(row2, textvariable=self.suffix, width=18)
        e_suf.pack(side=LEFT, padx=6)
        attach_context_menu(e_suf, allow_edit=True)
        ttk.Label(row2, text="bits").pack(side=LEFT, padx=(12, 0))
        e_bits = ttk.Entry(row2, textvariable=self.bits, width=6)
        e_bits.pack(side=LEFT, padx=6)
        attach_context_menu(e_bits, allow_edit=True)
        ttk.Checkbutton(row2, text="auto-resume если progress есть", variable=self.auto_resume).pack(side=LEFT, padx=8)

        row2c = ttk.Frame(top)
        row2c.pack(fill=X, pady=(6, 0))
        ttk.Label(row2c, text="Target (optional, для анализа):").pack(side=LEFT)
        e_target = ttk.Entry(row2c, textvariable=self.target, width=46)
        e_target.pack(side=LEFT, padx=6)
        attach_context_menu(e_target, allow_edit=True)

        row2b = ttk.Frame(top)
        row2b.pack(fill=X, pady=(6, 0))
        ttk.Label(row2b, text="Паттерны (-i, по одному в строке; пустые/#+комментарии игнорируются):").pack(side=LEFT)
        ttk.Button(row2b, text="Clear", command=self.clear_patterns).pack(side=RIGHT)

        pat_frame = ttk.Frame(top)
        pat_frame.pack(fill=X, pady=(4, 0))
        self.patterns_text = Text(pat_frame, height=4, wrap="none")
        self.patterns_text.pack(fill=X, expand=False)
        attach_context_menu(self.patterns_text, allow_edit=True)

        row3 = ttk.Frame(top)
        row3.pack(fill=X, pady=(6, 0))
        ttk.Label(row3, text="CPU t").pack(side=LEFT)
        e_t = ttk.Entry(row3, textvariable=self.cpu_threads, width=6)
        e_t.pack(side=LEFT, padx=6)
        attach_context_menu(e_t, allow_edit=True)
        ttk.Label(row3, text="maxFound (-m)").pack(side=LEFT)
        e_m = ttk.Entry(row3, textvariable=self.maxfound, width=10)
        e_m.pack(side=LEFT, padx=6)
        attach_context_menu(e_m, allow_edit=True)
        ttk.Label(row3, text="autosave (сек)").pack(side=LEFT)
        e_autosave = ttk.Entry(row3, textvariable=self.autosave, width=8)
        e_autosave.pack(side=LEFT, padx=6)
        attach_context_menu(e_autosave, allow_edit=True)
        ttk.Label(row3, text="tail lines").pack(side=LEFT, padx=(12, 0))
        e_tail = ttk.Entry(row3, textvariable=self.tail_n, width=6)
        e_tail.pack(side=LEFT, padx=6)
        attach_context_menu(e_tail, allow_edit=True)

        ttk.Label(row3, text="gpuId").pack(side=LEFT, padx=(14, 0))
        self._gpuid_entry = ttk.Entry(row3, textvariable=self.gpuid, width=6)
        self._gpuid_entry.pack(side=LEFT, padx=6)
        attach_context_menu(self._gpuid_entry, allow_edit=True)
        ttk.Label(row3, text="grid (-g)").pack(side=LEFT)
        self._grid_entry = ttk.Entry(row3, textvariable=self.grid, width=10)
        self._grid_entry.pack(side=LEFT, padx=6)
        attach_context_menu(self._grid_entry, allow_edit=True)
        ttk.Label(row3, text="CCAP (make gpu=1)").pack(side=LEFT, padx=(14, 0))
        self._ccap_entry = ttk.Entry(row3, textvariable=self.ccap, width=8)
        self._ccap_entry.pack(side=LEFT, padx=6)
        attach_context_menu(self._ccap_entry, allow_edit=True)

        mid = ttk.PanedWindow(self.root, orient=VERTICAL)
        mid.pack(fill=BOTH, expand=True, padx=10, pady=8)

        seg_frame = ttk.Labelframe(mid, text="Сегменты (вставьте текст seg-файла; группы разделяйте пустыми строками)")
        mid.add(seg_frame, weight=1)
        seg_hdr = ttk.Frame(seg_frame)
        seg_hdr.pack(fill=X, padx=8, pady=(8, 0))
        ttk.Button(seg_hdr, text="Load seg...", command=self.load_seg_file).pack(side=RIGHT)
        ttk.Button(seg_hdr, text="Save seg as...", command=self.save_seg_file_as).pack(side=RIGHT, padx=6)
        self.segments_text = Text(seg_frame, height=14, wrap="none")
        self.segments_text.pack(fill=BOTH, expand=True, padx=8, pady=8)
        attach_context_menu(self.segments_text, allow_edit=True)
        self.segments_text.bind("<KeyRelease>", lambda _e: self._update_groups_count())
        self.segments_text.bind("<Button-1>", lambda _e: self._update_groups_count())

        out_frame = ttk.Labelframe(mid, text="Вывод (лог / прогресс / build)")
        mid.add(out_frame, weight=2)
        out_wrap = ttk.Frame(out_frame)
        out_wrap.pack(fill=BOTH, expand=True, padx=8, pady=8)

        yscroll = ttk.Scrollbar(out_wrap, orient=VERTICAL)
        yscroll.pack(side=RIGHT, fill=Y)
        xscroll = ttk.Scrollbar(out_wrap, orient=HORIZONTAL)
        xscroll.pack(side="bottom", fill=X)

        self.output = Text(out_wrap, height=18, wrap="none", yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.output.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.config(command=self.output.yview)
        xscroll.config(command=self.output.xview)
        attach_context_menu(self.output, allow_edit=False)

    # ---------- helpers ----------
    def log(self, s: str) -> None:
        try:
            prev_state = str(self.output.cget("state"))
        except Exception:
            prev_state = "normal"
        if prev_state != "normal":
            try:
                self.output.configure(state="normal")
            except Exception:
                pass
        self.output.insert(END, s)
        self.output.see(END)
        if prev_state != "normal":
            try:
                self.output.configure(state=prev_state)
            except Exception:
                pass

    def _ui_log(self, s: str) -> None:
        self._ui_queue.put(("log", s))

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                kind, payload = self._ui_queue.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "report":
                    self.log("\n" + ("=" * 80) + "\n")
                    self.log("[ANALYZE] report\n")
                    self.log(("=" * 80) + "\n")
                    self.log(payload + ("\n" if not payload.endswith("\n") else ""))
                else:
                    self.log(f"[UI] unknown kind: {kind}\n")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_ui_queue)

    def clear_output(self) -> None:
        try:
            prev_state = str(self.output.cget("state"))
        except Exception:
            prev_state = "normal"
        if prev_state != "normal":
            try:
                self.output.configure(state="normal")
            except Exception:
                pass
        self.output.delete("1.0", END)
        if prev_state != "normal":
            try:
                self.output.configure(state=prev_state)
            except Exception:
                pass

    def clear_patterns(self) -> None:
        self.patterns_text.delete("1.0", END)

    def workdir(self) -> Path:
        rel = (self.workdir_rel.get().strip() or "runs").strip()
        wd = (REPO_ROOT / rel).resolve()
        wd.mkdir(parents=True, exist_ok=True)
        return wd

    def derived_files(self, *, group_num: int | None = None, groups_total: int | None = None) -> DerivedFiles:
        base = (self.base_name.get().strip() or "run").replace(" ", "_")
        # совместимость: если группа одна — не добавляем суффикс
        if group_num is not None and (groups_total or 0) > 1:
            base = f"{base}_{group_num}"
        wd = self.workdir()
        return DerivedFiles(
            base=base,
            workdir=wd,
            seg_file=wd / f"seg_{base}.txt",
            progress_file=wd / f"progress_{base}.dat",
            out_file=wd / f"out_{base}.txt",
            log_file=wd / f"log_{base}.log",
            patterns_file=wd / f"patterns_{base}.txt",
            pid_file=wd / f"pid_{base}.txt",
        )

    def _strip_wildcards_prefix(self, s: str) -> str:
        s = (s or "").strip()
        for i, ch in enumerate(s):
            if ch in ("*", "?"):
                return s[:i]
        return s

    def current_pattern(self) -> str:
        p = self.prefix.get().strip()
        s = self.suffix.get().strip()
        if not p and not s:
            return ""
        if "*" in p or "?" in p:
            return p
        if s:
            return f"{p}*{s}"
        return p

    def patterns_from_textbox(self) -> list[str]:
        raw = self.patterns_text.get("1.0", END).splitlines()
        out: list[str] = []
        for line in raw:
            p = _normalize_pattern_line(line)
            if p:
                out.append(p)
        return out

    def collect_patterns(self) -> list[str]:
        patterns: list[str] = []
        p0 = self.current_pattern()
        if p0:
            patterns.append(_normalize_pattern_line(p0) or p0)
        patterns.extend(self.patterns_from_textbox())
        seen = set()
        uniq: list[str] = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        return uniq

    def split_segments_into_groups(self) -> list[list[str]]:
        txt = self.segments_text.get("1.0", END)
        lines = txt.splitlines()
        groups: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            stripped = (line or "").strip()
            if not stripped or stripped.startswith("#") or stripped.startswith(";"):
                if current:
                    groups.append(current)
                    current = []
            else:
                current.append(line)
        if current:
            groups.append(current)
        if not groups:
            non_empty = [
                line
                for line in lines
                if line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith(";")
            ]
            if non_empty:
                groups.append(non_empty)
        return groups

    def _update_groups_count(self) -> None:
        groups = self.split_segments_into_groups()
        count = len(groups)
        if count > 0:
            self.groups_label.config(text=f"Groups: {count}", foreground="blue")
        else:
            self.groups_label.config(text="Groups: 0", foreground="gray")

    def pick_binary(self) -> None:
        p = filedialog.askopenfilename(title="Select VanitySearch binary", initialdir=str(REPO_ROOT))
        if not p:
            return
        self.binary_override.set(str(Path(p)))

    def resolve_binary(self) -> Path | None:
        ov = self.binary_override.get().strip()
        if ov:
            p = Path(ov)
            if not p.is_absolute():
                p = (REPO_ROOT / p).resolve()
            return p if p.exists() else None
        cc = detect_compute_cap()
        prefer_sm61 = cc.strip() == "6.1"
        return find_vanity_binary(prefer_sm61)

    def _init_defaults(self) -> None:
        # segments sample if empty
        if not self.segments_text.get("1.0", END).strip():
            sample = (
                "# Пример:\n"
                "# abs <start_dec> <end_dec> <up|down> <name> [priority]\n"
                "abs 0 1000 up seg1 1\n"
                "abs 1000 0 down seg2 1\n"
                "\n"
                "# Пустая строка разделяет группы (каждая группа = отдельный процесс)\n"
                "abs 2000 3000 up seg3 1\n"
            )
            self.segments_text.insert("1.0", sample)
        if not self.patterns_text.get("1.0", END).strip():
            self.patterns_text.insert("1.0", "# Примеры:\n# 18ss\n# 1P*X\n")
        self._update_groups_count()

        # grid default for Windows if possible
        if _is_windows() and not self.grid.get().strip():
            cc = detect_compute_cap()
            exe = find_windows_vanity_exe(cc.strip() == "6.1")
            if exe:
                self.grid.set(default_grid_for_current_gpu_windows(exe))
        self._on_backend_changed()

    def _on_backend_changed(self) -> None:
        is_gpu = self.backend.get().strip().lower() == "gpu"
        # На macOS GPU-режим обычно недоступен — не запрещаем жёстко, но предупреждаем при старте.
        st = "normal" if is_gpu else "disabled"
        try:
            self._gpuid_entry.configure(state=st)
            self._grid_entry.configure(state=st)
            # CCAP нужен только для posix GPU build (make gpu=1 ...)
            ccap_state = "normal" if (is_gpu and not _is_windows()) else "disabled"
            self._ccap_entry.configure(state=ccap_state)
        except Exception:
            pass

    # ---------- actions ----------
    def kill_all(self) -> None:
        self.log("[STOP ALL] ...\n")
        stop_all_processes()
        with self._proc_lock:
            for _k, p in list(self._procs.items()):
                try:
                    if p.poll() is None:
                        p.terminate()
                except Exception:
                    pass
            self._procs.clear()
        self.log("[STOP ALL] OK\n")

    def rebuild(self) -> None:
        if self._rebuild_thread and self._rebuild_thread.is_alive():
            self.log("[BUILD] уже выполняется\n")
            return
        self._stop_rebuild.clear()
        self.log("[BUILD] старт...\n")

        def worker():
            rc = rebuild(self._ui_log, self._stop_rebuild, backend=self.backend.get(), ccap=self.ccap.get())
            self._ui_log(f"\n[BUILD] exitcode={rc}\n")
            self.root.after(0, self._init_defaults)

        self._rebuild_thread = threading.Thread(target=worker, daemon=True)
        self._rebuild_thread.start()

    def start_search(self) -> None:
        binp = self.resolve_binary()
        if not binp or not binp.exists():
            self.log("[START] Бинарник VanitySearch не найден. Укажите Binary override или нажмите BUILD/REBUILD.\n")
            return

        patterns = self.collect_patterns()
        if not patterns:
            self.log("[START] Паттерны не заданы.\n")
            return

        groups = self.split_segments_into_groups()
        if not groups:
            self.log("[START] Нет сегментов.\n")
            return

        is_gpu = self.backend.get().strip().lower() == "gpu"
        if is_gpu and not _is_windows():
            self.log("[START] Предупреждение: GPU-режим выбран не на Windows. Если бинарник собран без GPU/CUDA, запуск может упасть.\n")

        bits = int(self.bits.get())
        t = int(self.cpu_threads.get())
        m = int(self.maxfound.get())
        autosave = int(self.autosave.get())
        gpuid = self.gpuid.get().strip() or "0"
        grid = self.grid.get().strip() or ("64,128" if not _is_windows() else self.grid.get().strip() or "64,128")

        self.log(f"[START] groups={len(groups)} backend={'GPU' if is_gpu else 'CPU'} workdir={self.workdir()}\n")
        multi = len(groups) > 1

        started = 0
        failed = 0
        for group_num, group_lines in enumerate(groups, start=1):
            df = self.derived_files(group_num=(group_num if multi else None), groups_total=len(groups))
            seg_content = "\n".join(group_lines).strip() + "\n"
            df.seg_file.write_text(seg_content, encoding="utf-8")

            resume_flag: list[str] = []
            if self.auto_resume.get() and df.progress_file.exists():
                resume_flag = ["-resume"]

            if len(patterns) == 1:
                pattern_args = [patterns[0]]
            else:
                df.patterns_file.write_text("\n".join(patterns) + "\n", encoding="utf-8")
                pattern_args = ["-i", str(df.patterns_file)]

            args = [
                str(binp),
                "-seg",
                str(df.seg_file),
                "-bits",
                str(bits),
            ]
            if is_gpu:
                args.extend(["-gpu", "-gpuId", gpuid, "-g", grid])
            args.extend(
                [
                    "-t",
                    str(t),
                    "-m",
                    str(m),
                    "-progress",
                    str(df.progress_file),
                    "-autosave",
                    str(autosave),
                    "-o",
                    str(df.out_file),
                    *resume_flag,
                    *pattern_args,
                ]
            )

            self.log(f"\n[START Group {group_num}] seg={df.seg_file.name} progress={df.progress_file.name} out={df.out_file.name} log={df.log_file.name}\n")
            self.log(f"[START Group {group_num}] cmd: {_format_cmd_for_display(args)}\n")

            df.log_file.parent.mkdir(parents=True, exist_ok=True)
            logf = df.log_file.open("ab")
            popen_kwargs = {
                "cwd": str(binp.parent if _is_windows() else REPO_ROOT),
                "stdout": logf,
                "stderr": subprocess.STDOUT,
            }
            if not _is_windows():
                popen_kwargs["start_new_session"] = True  # type: ignore[assignment]

            with self._proc_lock:
                existing = self._procs.get(df.base)
                if existing and existing.poll() is None:
                    self.log(f"[START Group {group_num}] уже запущено для base '{df.base}', пропускаю.\n")
                    logf.close()
                    continue
                try:
                    p = subprocess.Popen(args, **popen_kwargs)  # type: ignore[arg-type]
                except Exception as e:
                    logf.close()
                    self.log(f"[START Group {group_num}] ошибка запуска: {e}\n")
                    failed += 1
                    continue
                self._procs[df.base] = p
                try:
                    df.pid_file.write_text(str(p.pid), encoding="utf-8")
                except Exception:
                    pass
            self.log(f"[START Group {group_num}] PID={p.pid}\n")
            started += 1

        self.log(f"\n[START] Summary: {started} started, {failed} failed\n")

    def stop_search(self) -> None:
        base_prefix = (self.base_name.get().strip() or "run").replace(" ", "_")
        groups = self.split_segments_into_groups()
        if not groups:
            groups = [[]]
        self.log(f"[STOP] stopping all groups for base '{base_prefix}'...\n")

        stopped = 0
        multi = len(groups) > 1
        for group_num in range(1, len(groups) + 1):
            df = self.derived_files(group_num=(group_num if multi else None), groups_total=len(groups))
            pid = None
            if df.pid_file.exists():
                try:
                    pid = int(df.pid_file.read_text(encoding="utf-8").strip())
                except Exception:
                    pid = None

            if pid:
                try:
                    stop_pid(pid)
                    stopped += 1
                except Exception:
                    pass

            # fallback pkill by artifacts (posix)
            if not _is_windows():
                subprocess.run(["pkill", "-f", f"VanitySearch.*{df.seg_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-f", f"VanitySearch.*{df.progress_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            with self._proc_lock:
                p = self._procs.get(df.base)
                if p and p.poll() is None:
                    try:
                        p.terminate()
                        stopped += 1
                    except Exception:
                        pass
                self._procs.pop(df.base, None)

        self.log(f"[STOP] done ({stopped} processes stopped)\n")

    def show_tail(self) -> None:
        groups = self.split_segments_into_groups()
        n = int(self.tail_n.get())
        if not groups:
            self.log("\n[TAIL] No groups found\n")
            return
        multi = len(groups) > 1
        self.log(f"\n[TAIL] Showing last {n} lines from all groups:\n")
        self.log("=" * 80 + "\n")
        for group_num in range(1, len(groups) + 1):
            df = self.derived_files(group_num=(group_num if multi else None), groups_total=len(groups))
            self.log(f"\n--- Group {group_num} ({df.log_file.name}) ---\n")
            if df.log_file.exists():
                self.log(tail_lines(df.log_file, n) + "\n")
            else:
                self.log("[LOG FILE NOT FOUND]\n")
        self.log("=" * 80 + "\n")

    def show_found(self) -> None:
        groups = self.split_segments_into_groups()
        n = int(self.tail_n.get())
        if not groups:
            self.log("\n[FOUND] No groups found\n")
            return
        multi = len(groups) > 1
        self.log(f"\n[FOUND] Showing last {n} lines from out files for all groups:\n")
        self.log("=" * 80 + "\n")
        for group_num in range(1, len(groups) + 1):
            df = self.derived_files(group_num=(group_num if multi else None), groups_total=len(groups))
            self.log(f"\n--- Group {group_num} ({df.out_file.name}) ---\n")
            if df.out_file.exists():
                self.log(tail_lines(df.out_file, n) + "\n")
            else:
                self.log("[OUT FILE NOT FOUND]\n")
        self.log("=" * 80 + "\n")

    def show_progress(self) -> None:
        groups = self.split_segments_into_groups()
        if not SHOW_PROGRESS_PY.exists():
            self.log(f"[PROGRESS] не найден {SHOW_PROGRESS_PY}\n")
            return
        if not groups:
            self.log("\n[PROGRESS] No groups found\n")
            return
        py = sys.executable
        self.log(f"\n[PROGRESS] Showing progress for all {len(groups)} group(s):\n")
        self.log("=" * 120 + "\n")

        multi = len(groups) > 1
        for group_num in range(1, len(groups) + 1):
            df = self.derived_files(group_num=(group_num if multi else None), groups_total=len(groups))
            if not df.seg_file.exists():
                self.log(f"\n--- Group {group_num} ---\n")
                self.log(f"[PROGRESS] seg файл не найден: {df.seg_file}\n")
                continue
            if not df.progress_file.exists():
                self.log(f"\n--- Group {group_num} ---\n")
                self.log(f"[PROGRESS] progress файл не найден: {df.progress_file}\n")
                continue

            env = os.environ.copy()
            env.setdefault("PYTHONUTF8", "1")
            rc, out = run_capture([py, str(SHOW_PROGRESS_PY), str(df.seg_file), str(df.progress_file), str(df.out_file)], cwd=REPO_ROOT, env=env)
            self.log(f"\n{'=' * 120}\n")
            self.log(f"GROUP {group_num} ({df.base}) | rc={rc}\n")
            self.log(f"{'=' * 120}\n")
            self.log(out + "\n")
        self.log("=" * 120 + "\n")

    def load_seg_file(self) -> None:
        p = filedialog.askopenfilename(title="Select seg file", initialdir=str(REPO_ROOT))
        if not p:
            return
        try:
            txt = Path(p).read_text(encoding="utf-8")
        except Exception:
            txt = Path(p).read_text(errors="ignore")
        self.segments_text.delete("1.0", END)
        self.segments_text.insert("1.0", txt)
        self._update_groups_count()
        self.log(f"[SEG] loaded: {p}\n")

    def save_seg_file_as(self) -> None:
        p = filedialog.asksaveasfilename(title="Save seg file as", initialdir=str(REPO_ROOT), defaultextension=".txt")
        if not p:
            return
        txt = self.segments_text.get("1.0", END).strip() + "\n"
        Path(p).write_text(txt, encoding="utf-8")
        self.log(f"[SEG] saved: {p}\n")

    def open_runs_folder(self) -> None:
        wd = self.workdir()
        try:
            open_folder(wd)
            self.log(f"[OPEN] {wd}\n")
        except Exception as e:
            self.log(f"[OPEN] failed: {e}\n")

    def _schedule_refresh(self) -> None:
        def tick():
            try:
                if self._auto_refresh.get():
                    groups = self.split_segments_into_groups()
                    if groups:
                        n = int(self.tail_n.get())
                        with self._proc_lock:
                            running_bases = [b for b, p in self._procs.items() if p and p.poll() is None]
                        if running_bases:
                            blocks: list[str] = []
                            multi = len(groups) > 1
                            for group_num in range(1, len(groups) + 1):
                                df = self.derived_files(group_num=(group_num if multi else None), groups_total=len(groups))
                                if df.log_file.exists():
                                    blocks.append(f"--- Group {group_num} ({df.log_file.name}) ---\n{tail_lines(df.log_file, n)}\n")
                                else:
                                    blocks.append(f"--- Group {group_num} ({df.log_file.name}) ---\n[LOG FILE NOT FOUND]\n")
                            tail = "\n".join(blocks).rstrip() + "\n"
                            self._render_status(tail, running_bases)
            finally:
                self.root.after(1500, tick)

        self.root.after(1500, tick)

    def _render_status(self, tail: str, running_bases: list[str]) -> None:
        marker = "\n=== AUTO-TAIL ===\n"
        try:
            prev_state = str(self.output.cget("state"))
        except Exception:
            prev_state = "normal"
        if prev_state != "normal":
            try:
                self.output.configure(state="normal")
            except Exception:
                pass
        content = self.output.get("1.0", END)
        if marker in content:
            head = content.split(marker, 1)[0].rstrip() + "\n"
            self.output.delete("1.0", END)
            self.output.insert(END, head)
        self.output.insert(END, marker)
        self.output.insert(END, f"running: {', '.join(running_bases)} | workdir: {self.workdir()}\n")
        self.output.insert(END, tail + "\n")
        self.output.see(END)
        if prev_state != "normal":
            try:
                self.output.configure(state=prev_state)
            except Exception:
                pass

    # ----- Analyzer -----
    def run_analysis(self) -> None:
        if not HAS_ANALYZER:
            self.log(f"[ANALYZE] analyzer module not available: {ANALYZER_IMPORT_ERROR}\n")
            return
        base_prefix = (self.base_name.get().strip() or "run").replace(" ", "_")
        base_dir = self.workdir()
        glob_s = f"out_{base_prefix}*.txt"
        prefix_s = self._strip_wildcards_prefix(self.prefix.get())
        target_s = (self.target.get() or "").strip()
        search_patterns = self.collect_patterns()
        seg_groups = self.split_segments_into_groups()

        def worker() -> None:
            try:
                report = vs_analyzer.generate_report(
                    base_dir=base_dir,
                    glob_pattern=glob_s,
                    target_address=target_s,
                    target_prefix=prefix_s,
                    puzzle_bits=int(self.bits.get()),
                    suggest_patterns=24,
                    search_patterns=search_patterns,
                    seg_groups=seg_groups,
                    verify_crypto=10,
                )
            except Exception as e:  # noqa: BLE001
                report = f"[ANALYZE] failed: {e}\n"
            self._ui_queue.put(("report", report))

        self.log("[ANALYZE] running...\n")
        threading.Thread(target=worker, daemon=True).start()

    def run(self) -> None:
        self.root.mainloop()


def _cli_show_hint_for_tk() -> None:
    print("\n[INFO] tkinter недоступен, запускаю CLI-режим (без GUI).")
    print(f"Причина: {TK_IMPORT_ERROR}\n")  # type: ignore[name-defined]
    print("Если хочешь именно GUI-окно:")
    print("- Поставь Python с tkinter (обычно installer с python.org), либо conda/miniforge с пакетом tk.")
    print("- Важно: tkinter нельзя поставить через pip; он должен быть в сборке Python.\n")


def cli_main() -> int:
    _cli_show_hint_for_tk()
    workdir = (REPO_ROOT / "runs").resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"[WORKDIR] {workdir}\n")

    cc = detect_compute_cap()
    prefer_sm61 = cc.strip() == "6.1"
    binp = find_vanity_binary(prefer_sm61)
    if not binp:
        print("[ERROR] VanitySearch binary not found. Build it first (make/MSBuild).")
        return 1
    print(f"[BIN] {binp}\n")

    base = "run"
    bits = "71"
    threads = str(max(1, (os.cpu_count() or 2) - 1))
    autosave = "120"
    maxfound = "1000000"
    pattern = "1PWo3JeB"
    seg_src = ""
    backend = "gpu" if _is_windows() else "cpu"

    def df_for(base_name: str) -> DerivedFiles:
        bn = (base_name.strip() or "run").replace(" ", "_")
        return DerivedFiles(
            base=bn,
            workdir=workdir,
            seg_file=workdir / f"seg_{bn}.txt",
            progress_file=workdir / f"progress_{bn}.dat",
            out_file=workdir / f"out_{bn}.txt",
            log_file=workdir / f"log_{bn}.log",
            patterns_file=workdir / f"patterns_{bn}.txt",
            pid_file=workdir / f"pid_{bn}.txt",
        )

    def prompt(p: str, d: str) -> str:
        v = input(f"{p} [{d}]: ").strip()
        return v or d

    def do_build():
        print("[BUILD] ...")
        stop_ev = threading.Event()

        def out_cb(s: str):
            print(s, end="" if s.endswith("\n") else "\n")

        rc = rebuild(out_cb, stop_ev, backend=backend)
        print(f"[BUILD] done rc={rc}")

    def do_start():
        nonlocal base, bits, threads, autosave, maxfound, pattern, seg_src, backend
        base = prompt("Base name", base)
        seg_src = prompt("Path to seg file (source)", seg_src)
        bits = prompt("bits", bits)
        threads = prompt("threads (-t)", threads)
        autosave = prompt("autosave (sec)", autosave)
        maxfound = prompt("maxFound (-m)", maxfound)
        backend = prompt("backend (cpu/gpu)", backend)
        pattern = prompt("pattern (single)", pattern)

        df = df_for(base)
        if not seg_src or not Path(seg_src).exists():
            print(f"[START] seg source not found: {seg_src}")
            return

        df.seg_file.write_text(Path(seg_src).read_text(encoding="utf-8", errors="ignore").strip() + "\n", encoding="utf-8")
        resume_flag = []
        if df.progress_file.exists():
            yn = prompt("Resume from existing progress? (y/n)", "y")
            if yn.lower().startswith("y"):
                resume_flag = ["-resume"]

        args = [str(binp), "-seg", str(df.seg_file), "-bits", str(bits)]
        if backend.strip().lower() == "gpu":
            gpuid = prompt("gpuId", "0")
            grid = prompt("grid (-g)", "64,128")
            args.extend(["-gpu", "-gpuId", gpuid, "-g", grid])
        args.extend(
            [
                "-t",
                str(threads),
                "-m",
                str(maxfound),
                "-progress",
                str(df.progress_file),
                "-autosave",
                str(autosave),
                "-o",
                str(df.out_file),
                *resume_flag,
                str(pattern),
            ]
        )

        df.log_file.parent.mkdir(parents=True, exist_ok=True)
        logf = df.log_file.open("ab")
        kwargs = {"cwd": str(binp.parent if _is_windows() else REPO_ROOT), "stdout": logf, "stderr": subprocess.STDOUT}
        if not _is_windows():
            kwargs["start_new_session"] = True  # type: ignore[assignment]
        try:
            p = subprocess.Popen(args, **kwargs)  # type: ignore[arg-type]
            df.pid_file.write_text(str(p.pid), encoding="utf-8")
            print(f"[START] PID={p.pid}")
            print(f"[CMD] {_format_cmd_for_display(args)}")
        except Exception as e:
            logf.close()
            print(f"[START] failed: {e}")

    def do_stop():
        df = df_for(base)
        pid = None
        if df.pid_file.exists():
            try:
                pid = int(df.pid_file.read_text(encoding="utf-8").strip())
            except Exception:
                pid = None
        if pid:
            stop_pid(pid)
        if not _is_windows():
            subprocess.run(["pkill", "-f", f"VanitySearch.*{df.seg_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", f"VanitySearch.*{df.progress_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[STOP] done")

    def do_tail():
        df = df_for(base)
        n = int(prompt("tail N", "40"))
        print(tail_lines(df.log_file, n))

    def do_progress():
        df = df_for(base)
        if not SHOW_PROGRESS_PY.exists():
            print(f"[PROGRESS] not found: {SHOW_PROGRESS_PY}")
            return
        if not df.seg_file.exists() or not df.progress_file.exists():
            print("[PROGRESS] seg/progress files not found yet (start search first).")
            return
        py = sys.executable
        rc, out = run_capture([py, str(SHOW_PROGRESS_PY), str(df.seg_file), str(df.progress_file), str(df.out_file)], cwd=REPO_ROOT)
        print(out)
        print(f"[PROGRESS] rc={rc}")

    menu = {
        "1": ("BUILD", do_build),
        "2": ("START", do_start),
        "3": ("STOP", do_stop),
        "4": ("TAIL log", do_tail),
        "5": ("PROGRESS", do_progress),
        "0": ("QUIT", None),
    }
    while True:
        print("\n=== VanitySearch Launcher (CLI) ===")
        print(f"base={base} seg_src={seg_src or '(not set)'} pattern={pattern} bits={bits} t={threads} backend={backend}")
        for k in ("1", "2", "3", "4", "5", "0"):
            print(f"{k}) {menu[k][0]}")
        choice = input("> ").strip()
        if choice == "0":
            return 0
        if choice in menu and menu[choice][1]:
            try:
                menu[choice][1]()  # type: ignore[misc]
            except KeyboardInterrupt:
                print("\n[INTERRUPTED]")
            except Exception as e:
                print(f"[ERROR] {e}")
        else:
            print("Unknown choice.")


def main(*, default_backend: str | None = None, default_workdir: str | None = None) -> int:
    if HAS_TK:
        app = VanityUnifiedGUI(default_backend=default_backend, default_workdir=default_workdir)
        app.run()
        return 0
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())


