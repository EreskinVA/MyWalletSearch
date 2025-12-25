#!/usr/bin/env python3
"""
VanitySearch GUI (macOS / CPU)

Отдельный GUI-лаунчер для macOS/CPU (чтобы не смешивать с Windows GUI).
Без внешних зависимостей: tkinter + стандартная библиотека.

Умеет:
- make clean && make -j"$(sysctl -n hw.ncpu)"
- запуск VanitySearch (CPU) в фоне (detached) с логом/прогрессом/результатами
- остановка по PID (и fallback pkill по базовому имени)
- показать tail лога
- показать прогресс по сегментам через show_segment_progress.py (+ out-файл => "Найдено")
"""

from __future__ import annotations

import os
import sys
import time
import threading
import subprocess
from dataclasses import dataclass
from pathlib import Path
HAS_TK = True
try:
    # tkinter зависит от _tkinter (Tk). В некоторых сборках Python (часто Homebrew/pyenv без tcl-tk)
    # модуль _tkinter отсутствует.
    from tkinter import (
        Tk, ttk, StringVar, IntVar, BooleanVar, Text, END, X, Y, BOTH, LEFT, RIGHT,
        VERTICAL, HORIZONTAL, Menu, TclError,
    )
    from tkinter import filedialog
except Exception as e:  # noqa: BLE001
    HAS_TK = False
    TK_IMPORT_ERROR = e


REPO_ROOT = Path(__file__).resolve().parent
VANITY_BIN = REPO_ROOT / "VanitySearch"
SHOW_PROGRESS_PY = REPO_ROOT / "show_segment_progress.py"
WORKDIR = REPO_ROOT / "runs_cpu_gui"


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


def _safe_decode(b: bytes) -> str:
    for enc in ("utf-8", "cp1251", "cp866"):
        try:
            return b.decode(enc)
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
        size = f.tell()
        pos = size
        while pos > 0 and data.count(b"\n") <= n + 2:
            read = min(block, pos)
            pos -= read
            f.seek(pos)
            data = f.read(read) + data
    text = _safe_decode(data)
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def run_capture(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            shell=False,
        )
        return p.returncode, _safe_decode(p.stdout or b"")
    except FileNotFoundError:
        return 127, f"Команда не найдена: {args[0]}\n"
    except Exception as e:
        return 1, f"Ошибка запуска {args}: {e}\n"


def sysctl_ncpu() -> int:
    rc, out = run_capture(["sysctl", "-n", "hw.ncpu"])
    if rc == 0:
        try:
            return int(out.strip())
        except Exception:
            pass
    return os.cpu_count() or 1


def attach_context_menu(widget, *, allow_edit: bool) -> None:
    menu = Menu(widget, tearoff=0)

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
            if isinstance(widget, Text):
                widget.tag_add("sel", "1.0", "end")
            else:
                widget.select_range(0, "end")
        except Exception:
            pass

    menu.add_command(label="Copy", command=do_copy)
    menu.add_command(label="Cut", command=do_cut)
    menu.add_command(label="Paste", command=do_paste)
    menu.add_separator()
    menu.add_command(label="Select All", command=do_select_all)

    def popup(ev):
        try:
            menu.tk_popup(ev.x_root, ev.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", popup)  # macOS right click


def _cli_prompt(prompt: str, default: str | None = None) -> str:
    if default is None:
        return input(prompt).strip()
    v = input(f"{prompt} [{default}]: ").strip()
    return v or default


def _cli_show_hint_for_tk() -> None:
    print("\n[INFO] tkinter недоступен, запускаю CLI-режим (без GUI).")
    print(f"Причина: {TK_IMPORT_ERROR}\n")
    print("Если хочешь именно GUI-окно:")
    print("- Поставь Python с tkinter (обычно installer с python.org 3.12/3.13), либо conda/miniforge с пакетом tk.")
    print("- Важно: tkinter нельзя поставить через pip; он должен быть в сборке Python.\n")


def cli_main() -> int:
    _cli_show_hint_for_tk()
    WORKDIR.mkdir(parents=True, exist_ok=True)
    print(f"[WORKDIR] {WORKDIR}\n")

    # defaults
    ncpu = sysctl_ncpu()
    base = "cpu_run"
    bits = "71"
    threads = str(max(1, ncpu - 1))
    autosave = "120"
    maxfound = "1000000"
    pattern = "1PWo3JeB"
    seg_src = str(REPO_ROOT / "seg_cpu_part1.txt") if (REPO_ROOT / "seg_cpu_part1.txt").exists() else ""

    def df_for(base_name: str) -> DerivedFiles:
        bn = (base_name.strip() or "run").replace(" ", "_")
        return DerivedFiles(
            base=bn,
            workdir=WORKDIR,
            seg_file=WORKDIR / f"seg_{bn}.txt",
            progress_file=WORKDIR / f"prog_{bn}.dat",
            out_file=WORKDIR / f"out_{bn}.txt",
            log_file=WORKDIR / f"log_{bn}.log",
            patterns_file=WORKDIR / f"patterns_{bn}.txt",
            pid_file=WORKDIR / f"pid_{bn}.txt",
        )

    def do_build():
        print("[BUILD] make clean")
        rc, out = run_capture(["make", "clean"], cwd=REPO_ROOT)
        print(out, end="" if out.endswith("\n") else "\n")
        if rc != 0:
            print(f"[BUILD] failed rc={rc}")
            return
        n = sysctl_ncpu()
        print(f"[BUILD] make -j{n}")
        rc2, out2 = run_capture(["make", f"-j{n}"], cwd=REPO_ROOT)
        print(out2, end="" if out2.endswith("\n") else "\n")
        print(f"[BUILD] done rc={rc2}")

    def do_start():
        nonlocal base, bits, threads, autosave, maxfound, pattern, seg_src
        base = _cli_prompt("Base name", base)
        seg_src = _cli_prompt("Path to seg file (source)", seg_src)
        bits = _cli_prompt("bits", bits)
        threads = _cli_prompt("threads (-t)", threads)
        autosave = _cli_prompt("autosave (sec)", autosave)
        maxfound = _cli_prompt("maxFound (-m)", maxfound)
        pattern = _cli_prompt("pattern (single)", pattern)

        df = df_for(base)
        if not VANITY_BIN.exists():
            print(f"[START] Binary not found: {VANITY_BIN}. Run BUILD first.")
            return
        if not seg_src or not Path(seg_src).exists():
            print(f"[START] seg source not found: {seg_src}")
            return
        df.seg_file.write_text(Path(seg_src).read_text(encoding="utf-8", errors="ignore").strip() + "\n", encoding="utf-8")

        resume_flag = []
        if df.progress_file.exists():
            yn = _cli_prompt("Resume from existing progress? (y/n)", "y")
            if yn.lower().startswith("y"):
                resume_flag = ["-resume"]

        args = [
            str(VANITY_BIN),
            "-seg", str(df.seg_file),
            "-bits", str(bits),
            "-t", str(threads),
            "-m", str(maxfound),
            "-progress", str(df.progress_file),
            "-autosave", str(autosave),
            "-o", str(df.out_file),
            *resume_flag,
            str(pattern),
        ]
        df.log_file.parent.mkdir(parents=True, exist_ok=True)
        logf = df.log_file.open("ab")
        try:
            p = subprocess.Popen(args, cwd=str(REPO_ROOT), stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
            df.pid_file.write_text(str(p.pid), encoding="utf-8")
            print(f"[START] PID={p.pid}")
            print(f"[FILES] seg={df.seg_file.name} prog={df.progress_file.name} out={df.out_file.name} log={df.log_file.name}")
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
            try:
                os.kill(pid, 15)
                time.sleep(0.3)
            except Exception:
                pass
        subprocess.run(["pkill", "-f", f"VanitySearch.*{df.seg_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", f"VanitySearch.*{df.progress_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[STOP] done")

    def do_tail():
        df = df_for(base)
        n = int(_cli_prompt("tail N", "40"))
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

    def do_open():
        try:
            subprocess.run(["open", str(WORKDIR)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[OPEN] {WORKDIR}")
        except Exception as e:
            print(f"[OPEN] failed: {e}")

    menu = {
        "1": ("BUILD (make clean && make)", do_build),
        "2": ("START (CPU)", do_start),
        "3": ("STOP", do_stop),
        "4": ("TAIL log", do_tail),
        "5": ("PROGRESS (segments + found)", do_progress),
        "6": ("OPEN runs folder", do_open),
        "0": ("QUIT", None),
    }

    while True:
        print("\n=== VanitySearch CPU Launcher (CLI) ===")
        print(f"base={base} seg_src={seg_src or '(not set)'} pattern={pattern} bits={bits} t={threads}")
        for k in ("1", "2", "3", "4", "5", "6", "0"):
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


class VanityMacGUI:
    def __init__(self) -> None:
        if not HAS_TK:
            raise RuntimeError("tkinter is not available")
        self.root = Tk()
        self.root.title("VanitySearch GUI (macOS / CPU)")
        self.root.geometry("1100x780")

        self.base_name = StringVar(value="cpu_run")
        self.bits = IntVar(value=71)
        # По умолчанию: hw.ncpu - 1 (чтобы оставить системе "дыхание"), минимум 1.
        ncpu = sysctl_ncpu()
        self.threads = IntVar(value=max(1, ncpu - 1))
        self.maxfound = IntVar(value=1000000)
        self.autosave = IntVar(value=120)
        self.auto_resume = BooleanVar(value=True)
        self.tail_n = IntVar(value=40)

        self.prefix = StringVar(value="1PWo3JeB")
        self.suffix = StringVar(value="")

        self._proc_lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._rebuild_thread: threading.Thread | None = None
        self._stop_rebuild = threading.Event()

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=BOTH, expand=True)

        btn_row = ttk.Frame(top)
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text="BUILD (make clean && make)", command=self.rebuild).pack(side=LEFT)
        ttk.Button(btn_row, text="START (CPU)", command=self.start_search).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="STOP", command=self.stop_search).pack(side=LEFT)
        ttk.Button(btn_row, text="Tail log", command=self.show_tail).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="Progress", command=self.show_progress).pack(side=LEFT)
        ttk.Button(btn_row, text="Open runs folder", command=self.open_runs_folder).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="Clear output", command=self.clear_output).pack(side=RIGHT)

        row1 = ttk.Frame(top)
        row1.pack(fill=X, pady=(10, 0))
        ttk.Label(row1, text="Base name:").pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.base_name, width=24).pack(side=LEFT, padx=6)
        ttk.Label(row1, text="bits:").pack(side=LEFT, padx=(18, 0))
        ttk.Entry(row1, textvariable=self.bits, width=6).pack(side=LEFT, padx=6)
        ttk.Label(row1, text="threads (-t):").pack(side=LEFT, padx=(18, 0))
        ttk.Entry(row1, textvariable=self.threads, width=6).pack(side=LEFT, padx=6)
        ttk.Label(row1, text="autosave:").pack(side=LEFT, padx=(18, 0))
        ttk.Entry(row1, textvariable=self.autosave, width=6).pack(side=LEFT, padx=6)
        ttk.Checkbutton(row1, text="auto -resume", variable=self.auto_resume).pack(side=LEFT, padx=(18, 0))

        row2 = ttk.Frame(top)
        row2.pack(fill=X, pady=(8, 0))
        ttk.Label(row2, text="Prefix:").pack(side=LEFT)
        ttk.Entry(row2, textvariable=self.prefix, width=26).pack(side=LEFT, padx=6)
        ttk.Label(row2, text="Suffix (optional):").pack(side=LEFT, padx=(18, 0))
        ttk.Entry(row2, textvariable=self.suffix, width=18).pack(side=LEFT, padx=6)
        ttk.Label(row2, text="(prefix*suffix)").pack(side=LEFT)

        mid = ttk.Panedwindow(top, orient=HORIZONTAL)
        mid.pack(fill=BOTH, expand=True, pady=(10, 0))

        left = ttk.Frame(mid)
        right = ttk.Frame(mid)
        mid.add(left, weight=2)
        mid.add(right, weight=3)

        # Segments editor
        seg_hdr = ttk.Frame(left)
        seg_hdr.pack(fill=X)
        ttk.Label(seg_hdr, text="Segments (seg-file content):").pack(side=LEFT)
        ttk.Button(seg_hdr, text="Load seg...", command=self.load_seg_file).pack(side=RIGHT)
        ttk.Button(seg_hdr, text="Save seg as...", command=self.save_seg_file_as).pack(side=RIGHT, padx=6)

        self.segments_text = Text(left, height=18, wrap="none")
        self.segments_text.pack(fill=BOTH, expand=True)
        attach_context_menu(self.segments_text, allow_edit=True)
        self.segments_text.insert(
            "1.0",
            "# Format: abs <start_dec> <end_dec> <up|down> <name> [priority]\n"
            "# Example:\n"
            "# abs 2024714629530360385372 2025206542705659306749 up cpu1 1\n"
        )

        # Patterns editor (optional)
        pat_hdr = ttk.Frame(left)
        pat_hdr.pack(fill=X, pady=(10, 0))
        ttk.Label(pat_hdr, text="Extra patterns (-i), one per line (optional):").pack(side=LEFT)
        ttk.Button(pat_hdr, text="Clear", command=self.clear_patterns).pack(side=RIGHT)

        self.patterns_text = Text(left, height=8, wrap="none")
        self.patterns_text.pack(fill=BOTH, expand=False)
        attach_context_menu(self.patterns_text, allow_edit=True)
        self.patterns_text.insert("1.0", "# Example:\n# 1PWo3J????\n# 1ABC*XYZ\n")

        # Output console
        out_hdr = ttk.Frame(right)
        out_hdr.pack(fill=X)
        ttk.Label(out_hdr, text="Output:").pack(side=LEFT)
        ttk.Label(out_hdr, text="tail N:").pack(side=RIGHT)
        ttk.Entry(out_hdr, textvariable=self.tail_n, width=6).pack(side=RIGHT, padx=6)

        self.output = Text(right, wrap="none")
        self.output.pack(fill=BOTH, expand=True)
        attach_context_menu(self.output, allow_edit=False)

        self.log(f"WORKDIR: {WORKDIR}\n")
        self.log(f"Binary:  {VANITY_BIN}\n")
        self.log(f"Default threads: {self.threads.get()} (hw.ncpu={ncpu})\n")

    # ----- helpers -----
    def log(self, s: str) -> None:
        self.output.insert(END, s)
        self.output.see(END)

    def clear_output(self) -> None:
        self.output.delete("1.0", END)

    def clear_patterns(self) -> None:
        self.patterns_text.delete("1.0", END)

    def derived_files(self) -> DerivedFiles:
        base = (self.base_name.get().strip() or "run").replace(" ", "_")
        WORKDIR.mkdir(parents=True, exist_ok=True)
        return DerivedFiles(
            base=base,
            workdir=WORKDIR,
            seg_file=WORKDIR / f"seg_{base}.txt",
            progress_file=WORKDIR / f"prog_{base}.dat",
            out_file=WORKDIR / f"out_{base}.txt",
            log_file=WORKDIR / f"log_{base}.log",
            patterns_file=WORKDIR / f"patterns_{base}.txt",
            pid_file=WORKDIR / f"pid_{base}.txt",
        )

    def collect_patterns(self) -> list[str]:
        patterns: list[str] = []
        p = self.prefix.get().strip()
        s = self.suffix.get().strip()
        if p:
            if "*" in p or "?" in p:
                patterns.append(p)
            elif s:
                patterns.append(f"{p}*{s}")
            else:
                patterns.append(p)
        # extra patterns
        for line in self.patterns_text.get("1.0", END).splitlines():
            line = (line or "").strip()
            if not line or line.startswith("#"):
                continue
            if len(line) >= 2 and line[0] == line[-1] and line[0] in ("'", '"'):
                line = line[1:-1].strip()
            patterns.append(line)
        # dedup keep order
        seen = set()
        uniq: list[str] = []
        for x in patterns:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        return uniq

    def _write_seg(self, df: DerivedFiles) -> None:
        txt = self.segments_text.get("1.0", END).strip() + "\n"
        df.seg_file.write_text(txt, encoding="utf-8")

    # ----- actions -----
    def rebuild(self) -> None:
        if self._rebuild_thread and self._rebuild_thread.is_alive():
            self.log("[BUILD] already running\n")
            return
        self._stop_rebuild.clear()
        self.log("[BUILD] make clean && make ...\n")

        def worker():
            # make clean
            rc1, out1 = run_capture(["make", "clean"], cwd=REPO_ROOT)
            self.log(out1)
            if rc1 != 0:
                self.log(f"[BUILD] make clean failed rc={rc1}\n")
                return
            # make -jN
            n = sysctl_ncpu()
            rc2, out2 = run_capture(["make", f"-j{n}"], cwd=REPO_ROOT)
            self.log(out2)
            self.log(f"[BUILD] done rc={rc2}\n")

        self._rebuild_thread = threading.Thread(target=worker, daemon=True)
        self._rebuild_thread.start()

    def start_search(self) -> None:
        df = self.derived_files()
        self._write_seg(df)

        if not VANITY_BIN.exists():
            self.log(f"[START] Binary not found: {VANITY_BIN}. Run BUILD first.\n")
            return

        patterns = self.collect_patterns()
        if not patterns:
            self.log("[START] No patterns provided.\n")
            return

        bits = int(self.bits.get())
        t = int(self.threads.get())
        autosave = int(self.autosave.get())
        m = int(self.maxfound.get())

        resume_flag: list[str] = []
        if self.auto_resume.get() and df.progress_file.exists():
            resume_flag = ["-resume"]

        pattern_args: list[str]
        if len(patterns) == 1:
            pattern_args = [patterns[0]]
        else:
            df.patterns_file.write_text("\n".join(patterns) + "\n", encoding="utf-8")
            pattern_args = ["-i", str(df.patterns_file)]

        args = [
            str(VANITY_BIN),
            "-seg", str(df.seg_file),
            "-bits", str(bits),
            "-t", str(t),
            "-m", str(m),
            "-progress", str(df.progress_file),
            "-autosave", str(autosave),
            "-o", str(df.out_file),
            *resume_flag,
            *pattern_args,
        ]

        self.log(f"[START] seg={df.seg_file.name} progress={df.progress_file.name} out={df.out_file.name} log={df.log_file.name}\n")
        self.log("[START] cmd:\n  " + " ".join(args) + "\n")

        df.log_file.parent.mkdir(parents=True, exist_ok=True)
        logf = df.log_file.open("ab")
        try:
            with self._proc_lock:
                if self._proc and self._proc.poll() is None:
                    self.log("[START] already running. Use STOP.\n")
                    logf.close()
                    return
                # detach like nohup: start_new_session=True
                p = subprocess.Popen(args, cwd=str(REPO_ROOT), stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
                self._proc = p
                df.pid_file.write_text(str(p.pid), encoding="utf-8")
            self.log(f"[START] PID={p.pid}\n")
        except Exception as e:
            logf.close()
            self.log(f"[START] failed: {e}\n")

    def stop_search(self) -> None:
        df = self.derived_files()
        pid = None
        if df.pid_file.exists():
            try:
                pid = int(df.pid_file.read_text(encoding="utf-8").strip())
            except Exception:
                pid = None

        self.log("[STOP] stopping...\n")
        # 1) try kill pid
        if pid:
            try:
                os.kill(pid, 15)
                time.sleep(0.5)
            except Exception:
                pass

        # 2) fallback: pkill by our base name artifacts
        # (matches commands containing seg/prog/out names)
        subprocess.run(["pkill", "-f", f"VanitySearch.*{df.seg_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", f"VanitySearch.*{df.progress_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with self._proc_lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
            self._proc = None
        self.log("[STOP] done\n")

    def show_tail(self) -> None:
        df = self.derived_files()
        n = int(self.tail_n.get())
        self.log(f"\n[TAIL] {df.log_file.name} (last {n})\n")
        self.log(tail_lines(df.log_file, n) + "\n")

    def show_progress(self) -> None:
        df = self.derived_files()
        if not SHOW_PROGRESS_PY.exists():
            self.log(f"[PROGRESS] not found: {SHOW_PROGRESS_PY}\n")
            return
        if not df.seg_file.exists():
            self.log(f"[PROGRESS] seg not found: {df.seg_file}\n")
            return
        if not df.progress_file.exists():
            self.log(f"[PROGRESS] progress not found: {df.progress_file}\n")
            return

        py = sys.executable
        rc, out = run_capture([py, str(SHOW_PROGRESS_PY), str(df.seg_file), str(df.progress_file), str(df.out_file)], cwd=REPO_ROOT)
        self.log(f"\n[PROGRESS] rc={rc}\n")
        self.log(out + "\n")

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
        self.log(f"[SEG] loaded: {p}\n")

    def save_seg_file_as(self) -> None:
        p = filedialog.asksaveasfilename(title="Save seg file as", initialdir=str(REPO_ROOT), defaultextension=".txt")
        if not p:
            return
        txt = self.segments_text.get("1.0", END).strip() + "\n"
        Path(p).write_text(txt, encoding="utf-8")
        self.log(f"[SEG] saved: {p}\n")

    def open_runs_folder(self) -> None:
        WORKDIR.mkdir(parents=True, exist_ok=True)
        # macOS: open folder in Finder
        try:
            subprocess.run(["open", str(WORKDIR)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log(f"[OPEN] {WORKDIR}\n")
        except Exception as e:
            self.log(f"[OPEN] failed: {e}\n")

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    if HAS_TK:
        app = VanityMacGUI()
        app.run()
        return 0
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())


