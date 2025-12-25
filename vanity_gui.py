#!/usr/bin/env python3
"""
Мини-GUI для запуска VanitySearch на Windows.

Требования пользователя:
- одно поле "базовое имя" для файлов, а реальные имена получаются добавлением суффиксов
- многострочное поле для сегментов (содержимое seg-файла)
- удобный ввод паттернов:
  - быстрый вариант: prefix (+ опционально suffix -> prefix*suffix)
  - расширенный вариант: несколько паттернов (по одному на строку) => запуск через `-i patterns.txt`
- поле "сколько строк лога показывать" + большое окно вывода
- кнопки: Stop (убить процессы), Start (запуск поиска), Rebuild (пересборка под текущий ПК/GPU)
- просмотр tail -n N логов и прогресса через show_segment_progress.py

Без внешних зависимостей: используется только tkinter + стандартная библиотека.
"""

from __future__ import annotations

import os
import re
import sys
import time
import threading
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tkinter import Tk, ttk, StringVar, IntVar, BooleanVar, Text, END, BOTH, LEFT, RIGHT, X, Y, VERTICAL, HORIZONTAL, Menu, TclError


REPO_ROOT = Path(__file__).resolve().parent
SHOW_PROGRESS_PY = REPO_ROOT / "show_segment_progress.py"


@dataclass
class DerivedFiles:
    workdir: Path
    seg_file: Path
    progress_file: Path
    out_file: Path
    log_file: Path
    patterns_file: Path


def _normalize_pattern_line(line: str) -> str:
    """
    Нормализует строку паттерна:
    - обрезает пробелы
    - игнорирует пустые строки и комментарии (#...)
    - снимает внешние кавычки "..." или '...' (частая ошибка при копипасте из команд)
    """
    s = (line or "").strip()
    if not s:
        return ""
    if s.startswith("#"):
        return ""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s


def _format_cmd_for_display(args: list[str]) -> str:
    """
    Форматирует команду для вывода в лог так, чтобы её можно было копипастить в shell.
    Важно: GUI запускает процесс через subprocess(args, shell=False), поэтому кавычки для запуска НЕ нужны,
    но для копипаста в PowerShell/cmd они полезны при наличии *, ?, пробелов.
    """
    def q(a: str) -> str:
        if a is None:
            return ""
        need = (" " in a) or ("\t" in a) or ("*" in a) or ("?" in a)
        if not need:
            return a
        # простая защита: экранируем двойные кавычки
        a2 = a.replace('"', r'\"')
        return f"\"{a2}\""

    return " ".join(q(a) for a in args)


def _safe_decode(b: bytes) -> str:
    # На Windows при выводе в PIPE Python чаще пишет в системной ANSI-кодировке (обычно cp1251),
    # а не в консольной (cp866). Поэтому пробуем cp1251 раньше cp866, чтобы не получать "кракозябры".
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
    # простой tail для небольших файлов: читаем с конца блоками
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
        return 127, f"Команда не найдена: {args[0]}"
    except Exception as e:
        return 1, f"Ошибка запуска {args}: {e}"


def find_vanity_exe(prefer_sm61: bool) -> Path | None:
    # Для GTX 10xx / sm_61 у нас есть отдельная конфигурация ReleaseSM61
    candidates = []
    if prefer_sm61:
        candidates.append(REPO_ROOT / "x64" / "ReleaseSM61" / "VanitySearch.exe")
    candidates.append(REPO_ROOT / "x64" / "Release" / "VanitySearch.exe")
    candidates.append(REPO_ROOT / "x64" / "ReleaseSM61" / "VanitySearch.exe")
    for c in candidates:
        if c.exists():
            return c
    return None


def detect_compute_cap() -> str:
    # пробуем получить compute_cap напрямую
    rc, out = run_capture(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"])
    if rc == 0:
        cc = (out.strip().splitlines()[:1] or [""])[0].strip()
        if re.match(r"^\d+(\.\d+)?$", cc):
            return cc
    return ""


def detect_sm_count(vanity_exe: Path) -> int:
    # парсим вывод VanitySearch.exe -l: "GPU #0 ... (6x128 cores) ..."
    rc, out = run_capture([str(vanity_exe), "-l"], cwd=vanity_exe.parent)
    if rc != 0 and not out:
        return 0
    m = re.search(r"\((\d+)x\d+\s+cores\)", out)
    if m:
        return int(m.group(1))
    return 0


def default_grid_for_current_gpu(vanity_exe: Path) -> str:
    sm = detect_sm_count(vanity_exe)
    if sm > 0:
        return f"{sm * 8},128"
    # fallback: разумный дефолт
    return "64,128"


def msbuild_path() -> Path | None:
    # стандартный путь для VS 2022 Community
    p = Path(r"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe")
    if p.exists():
        return p
    return None


def rebuild_for_current_machine(output_cb, stop_event: threading.Event) -> int:
    msb = msbuild_path()
    if not msb:
        output_cb("MSBuild.exe не найден. Установите Visual Studio Build Tools/VS.\n")
        return 1

    cc = detect_compute_cap()
    prefer_sm61 = (cc.strip() == "6.1")
    config = "ReleaseSM61" if prefer_sm61 else "Release"
    output_cb(f"GPU compute_cap={cc or 'N/A'} -> rebuild {config}|x64\n")

    args = [str(msb), "VanitySearch.sln", "/t:Rebuild", f"/p:Configuration={config}", "/p:Platform=x64", "/m", "/v:m"]
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


def attach_context_menu(widget, *, allow_edit: bool) -> None:
    """
    Добавляет контекстное меню по ПКМ: Copy/Cut/Paste/Select All.
    Работает для Text и Entry.
    """
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
        except TclError:
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

    # Windows: ПКМ = Button-3. На тачпаде иногда Button-2.
    widget.bind("<Button-3>", popup, add=True)
    widget.bind("<Button-2>", popup, add=True)

    # Ctrl+A для удобного выделения
    def ctrl_a(_event):
        do_select_all()
        return "break"

    widget.bind("<Control-a>", ctrl_a, add=True)
    widget.bind("<Control-A>", ctrl_a, add=True)


class VanityGUI:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("VanitySearch GUI (Windows)")
        self.root.geometry("1050x760")

        self.base_name = StringVar(value="puzzle71_69_72")
        self.prefix = StringVar(value="1PWo3JeB")
        self.suffix = StringVar(value="")
        self.bits = IntVar(value=71)
        self.gpuid = StringVar(value="0")
        self.grid = StringVar(value="")
        self.cpu_threads = IntVar(value=2)
        self.maxfound = IntVar(value=1_000_000)
        self.autosave = IntVar(value=120)
        self.auto_resume = BooleanVar(value=True)
        self.tail_n = IntVar(value=30)

        self._proc_lock = threading.Lock()
        self._search_proc: subprocess.Popen | None = None
        self._rebuild_thread: threading.Thread | None = None
        self._stop_rebuild = threading.Event()
        self._auto_refresh = BooleanVar(value=True)

        self._build_ui()
        self._init_defaults()
        self._schedule_refresh()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill=X, padx=10, pady=8)

        # buttons (moved to top as requested)
        btn_row = ttk.Frame(top)
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text="STOP: убить все VanitySearch процессы", command=self.kill_all).pack(side=LEFT)
        ttk.Button(btn_row, text="START: запуск поиска", command=self.start_search).pack(side=LEFT, padx=10)
        ttk.Button(btn_row, text="REBUILD: пересобрать под этот ПК", command=self.rebuild).pack(side=LEFT)
        ttk.Button(btn_row, text="Очистить вывод", command=self.clear_output).pack(side=RIGHT)

        # row 1: base name + derived
        row1 = ttk.Frame(top)
        row1.pack(fill=X, pady=(8, 0))
        ttk.Label(row1, text="Базовое имя файлов:").pack(side=LEFT)
        e_base = ttk.Entry(row1, textvariable=self.base_name, width=28)
        e_base.pack(side=LEFT, padx=6)
        attach_context_menu(e_base, allow_edit=True)
        ttk.Button(row1, text="Показать лог (tail)", command=self.show_tail).pack(side=LEFT, padx=6)
        ttk.Button(row1, text="Показать найденные", command=self.show_found).pack(side=LEFT, padx=6)
        ttk.Button(row1, text="Показать прогресс", command=self.show_progress).pack(side=LEFT, padx=6)

        # row 2: pattern + bits
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

        # row 2b: multi-patterns (-i)
        row2b = ttk.Frame(top)
        row2b.pack(fill=X, pady=(6, 0))
        ttk.Label(row2b, text="Паттерны (-i, по одному в строке; пустые/#+комментарии игнорируются):").pack(side=LEFT)

        # patterns text (compact)
        pat_frame = ttk.Frame(top)
        pat_frame.pack(fill=X, pady=(4, 0))
        self.patterns_text = Text(pat_frame, height=4, wrap="none")
        self.patterns_text.pack(fill=X, expand=False, padx=0, pady=0)
        attach_context_menu(self.patterns_text, allow_edit=True)

        # row 3: gpu/grid/threads/maxfound/autosave/tail
        row3 = ttk.Frame(top)
        row3.pack(fill=X, pady=(6, 0))
        ttk.Label(row3, text="gpuId").pack(side=LEFT)
        e_gpuid = ttk.Entry(row3, textvariable=self.gpuid, width=6)
        e_gpuid.pack(side=LEFT, padx=6)
        attach_context_menu(e_gpuid, allow_edit=True)
        ttk.Label(row3, text="grid (-g)").pack(side=LEFT)
        e_grid = ttk.Entry(row3, textvariable=self.grid, width=10)
        e_grid.pack(side=LEFT, padx=6)
        attach_context_menu(e_grid, allow_edit=True)
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
        ttk.Checkbutton(row3, text="автообновление", variable=self._auto_refresh).pack(side=LEFT, padx=8)

        # segments text
        mid = ttk.PanedWindow(self.root, orient=VERTICAL)
        mid.pack(fill=BOTH, expand=True, padx=10, pady=8)

        seg_frame = ttk.Labelframe(mid, text="Сегменты (вставьте текст seg-файла)")
        mid.add(seg_frame, weight=1)

        self.segments_text = Text(seg_frame, height=14, wrap="none")
        self.segments_text.pack(fill=BOTH, expand=True, padx=8, pady=8)
        attach_context_menu(self.segments_text, allow_edit=True)

        # output
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
        # read-only, но можно выделять/копировать
        attach_context_menu(self.output, allow_edit=False)

    # ---------- Helpers ----------
    def log(self, s: str) -> None:
        try:
            prev_state = str(self.output.cget("state"))
        except Exception:
            prev_state = "normal"
        # Делаем output "read-only": пишем через временное включение normal.
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

    def derived_files(self) -> DerivedFiles:
        base = self.base_name.get().strip() or "run"
        workdir = REPO_ROOT / "runs"
        workdir.mkdir(parents=True, exist_ok=True)
        return DerivedFiles(
            workdir=workdir,
            # Именование совместимо с *.sh и show_segment_progress.py:
            #   seg_<base>.txt, progress_<base>.dat, out_<base>.txt, log_<base>.log, patterns_<base>.txt
            seg_file=workdir / f"seg_{base}.txt",
            progress_file=workdir / f"progress_{base}.dat",
            out_file=workdir / f"out_{base}.txt",
            log_file=workdir / f"log_{base}.log",
            patterns_file=workdir / f"patterns_{base}.txt",
        )

    def current_pattern(self) -> str:
        p = self.prefix.get().strip()
        s = self.suffix.get().strip()
        if not p and not s:
            return ""
        if "*" in p:
            # пользователь мог уже задать raw-паттерн
            return p
        if s:
            return f"{p}*{s}"
        return p

    def patterns_from_textbox(self) -> list[str]:
        if not hasattr(self, "patterns_text") or self.patterns_text is None:
            return []
        raw = self.patterns_text.get("1.0", END).splitlines()
        out: list[str] = []
        for line in raw:
            p = _normalize_pattern_line(line)
            if p:
                out.append(p)
        return out

    def collect_patterns(self) -> list[str]:
        """
        Собирает список паттернов из:
        - быстрого поля prefix/suffix
        - многострочного списка паттернов
        Пустые значения игнорируются.
        """
        patterns: list[str] = []
        p0 = self.current_pattern()
        if p0:
            patterns.append(_normalize_pattern_line(p0) or p0)
        patterns.extend(self.patterns_from_textbox())
        # дедуп по порядку (чтобы случайно не искать одно и то же дважды)
        seen = set()
        uniq: list[str] = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        return uniq

    def _init_defaults(self) -> None:
        cc = detect_compute_cap()
        prefer_sm61 = (cc.strip() == "6.1")
        exe = find_vanity_exe(prefer_sm61)
        if exe:
            if not self.grid.get().strip():
                self.grid.set(default_grid_for_current_gpu(exe))
        # подставим пример сегментов, если поле пустое
        if not self.segments_text.get("1.0", END).strip():
            sample = (
                "# Пример (как в run_puzzle71_69_72.sh):\n"
                "# Формат: abs <start_dec> <end_dec> <up|down> <name> [priority]\n"
                "abs 0 1000 up seg1 1\n"
                "abs 1000 0 down seg2 1\n"
            )
            self.segments_text.insert("1.0", sample)
        # подставим пример паттернов (как в RUNBOOK 4.1.1), если поле пустое
        if hasattr(self, "patterns_text") and not self.patterns_text.get("1.0", END).strip():
            self.patterns_text.insert("1.0", "# Примеры (по одному в строке, без кавычек):\n# 18ss\n# 1P*X\n")

    # ---------- Actions ----------
    def kill_all(self) -> None:
        self.log("[STOP] taskkill VanitySearch.exe ...\n")
        # убиваем и те, что запущены GUI, и любые другие
        for img in ("VanitySearch.exe",):
            subprocess.run(["taskkill", "/F", "/T", "/IM", img], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with self._proc_lock:
            if self._search_proc and self._search_proc.poll() is None:
                try:
                    self._search_proc.terminate()
                except Exception:
                    pass
            self._search_proc = None
        self.log("[STOP] OK\n")

    def rebuild(self) -> None:
        if self._rebuild_thread and self._rebuild_thread.is_alive():
            self.log("[REBUILD] уже выполняется\n")
            return
        self._stop_rebuild.clear()
        self.log("[REBUILD] старт...\n")

        def worker():
            rc = rebuild_for_current_machine(self.log, self._stop_rebuild)
            self.log(f"\n[REBUILD] exitcode={rc}\n")
            # после rebuild обновим grid по текущему exe
            self._init_defaults()

        self._rebuild_thread = threading.Thread(target=worker, daemon=True)
        self._rebuild_thread.start()

    def _write_segments_file(self, df: DerivedFiles) -> None:
        txt = self.segments_text.get("1.0", END).strip() + "\n"
        df.seg_file.write_text(txt, encoding="utf-8")

    def start_search(self) -> None:
        df = self.derived_files()
        self._write_segments_file(df)

        cc = detect_compute_cap()
        prefer_sm61 = (cc.strip() == "6.1")
        exe = find_vanity_exe(prefer_sm61)
        if not exe:
            self.log("VanitySearch.exe не найден. Нажмите REBUILD.\n")
            return

        patterns = self.collect_patterns()
        if not patterns:
            self.log("Паттерны не заданы — заполните prefix (и опционально suffix) и/или добавьте строки в поле 'Паттерны (-i)'.\n")
            return

        grid = self.grid.get().strip() or default_grid_for_current_gpu(exe)
        bits = int(self.bits.get())
        gpuid = self.gpuid.get().strip() or "0"
        t = int(self.cpu_threads.get())
        m = int(self.maxfound.get())
        autosave = int(self.autosave.get())

        resume_flag = []
        if self.auto_resume.get() and df.progress_file.exists():
            resume_flag = ["-resume"]

        # Если паттерн один — передаём как последний аргумент.
        # Если паттернов несколько — пишем patterns_<base>.txt и запускаем через -i (см. RUNBOOK 4.1.1).
        pattern_args: list[str] = []
        if len(patterns) == 1:
            pattern_args = [patterns[0]]
        else:
            df.patterns_file.write_text("\n".join(patterns) + "\n", encoding="utf-8")
            pattern_args = ["-i", str(df.patterns_file)]

        args = [
            str(exe),
            "-seg", str(df.seg_file),
            "-bits", str(bits),
            "-gpu", "-gpuId", gpuid,
            "-g", grid,
            "-t", str(t),
            "-m", str(m),
            "-progress", str(df.progress_file),
            "-autosave", str(autosave),
            "-o", str(df.out_file),
            *resume_flag,
            *pattern_args,
        ]

        self.log(f"[START] cwd={exe.parent}\n")
        self.log(f"[START] seg={df.seg_file.name} progress={df.progress_file.name} out={df.out_file.name} log={df.log_file.name}\n")
        if len(patterns) > 1:
            self.log(f"[START] patterns: {len(patterns)} (через -i {df.patterns_file.name})\n")
        self.log(f"[START] cmd: {_format_cmd_for_display(args)}\n")

        # запускаем в фоне, stdout/stderr -> log
        df.log_file.parent.mkdir(parents=True, exist_ok=True)
        logf = df.log_file.open("ab")

        with self._proc_lock:
            if self._search_proc and self._search_proc.poll() is None:
                self.log("[START] уже есть запущенный процесс — остановите его кнопкой STOP.\n")
                logf.close()
                return
            try:
                p = subprocess.Popen(args, cwd=str(exe.parent), stdout=logf, stderr=subprocess.STDOUT)
            except Exception as e:
                logf.close()
                self.log(f"[START] ошибка запуска: {e}\n")
                return
            self._search_proc = p

        self.log(f"[START] PID={p.pid}\n")

    def show_tail(self) -> None:
        df = self.derived_files()
        n = int(self.tail_n.get())
        self.log(f"\n[TAIL] {df.log_file} (последние {n} строк)\n")
        self.log(tail_lines(df.log_file, n) + "\n")

    def show_found(self) -> None:
        df = self.derived_files()
        n = int(self.tail_n.get())
        if not df.out_file.exists():
            self.log(f"\n[FOUND] файл не найден: {df.out_file}\n")
            return
        self.log(f"\n[FOUND] {df.out_file} (последние {n} строк)\n")
        self.log(tail_lines(df.out_file, n) + "\n")

    def show_progress(self) -> None:
        df = self.derived_files()
        if not SHOW_PROGRESS_PY.exists():
            self.log(f"[PROGRESS] не найден {SHOW_PROGRESS_PY}\n")
            return
        if not df.seg_file.exists():
            self.log(f"[PROGRESS] seg файл не найден: {df.seg_file}\n")
            return
        if not df.progress_file.exists():
            self.log(f"[PROGRESS] progress файл не найден: {df.progress_file}\n")
            return

        py = sys.executable
        # Страховка на Windows: принудительно UTF-8 для подпроцесса (но мы всё равно декодируем гибко).
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        try:
            p = subprocess.run(
                [py, str(SHOW_PROGRESS_PY), str(df.seg_file), str(df.progress_file)],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                env=env,
                shell=False,
            )
            rc, out = p.returncode, _safe_decode(p.stdout or b"")
        except Exception as e:
            rc, out = 1, f"Ошибка запуска show_segment_progress.py: {e}"
        self.log(f"\n[PROGRESS] rc={rc}\n")
        self.log(out + "\n")

    def _schedule_refresh(self) -> None:
        # автообновление: показываем tail лога в окне вывода
        def tick():
            try:
                if self._auto_refresh.get():
                    df = self.derived_files()
                    if df.log_file.exists():
                        n = int(self.tail_n.get())
                        # перерисовываем только tail-блок, чтобы не бесконечно раздувать output
                        # простой подход: если процесс запущен — показываем последние N строк внизу.
                        with self._proc_lock:
                            running = self._search_proc is not None and self._search_proc.poll() is None
                        if running:
                            tail = tail_lines(df.log_file, n)
                            self._render_status(tail, df)
            finally:
                self.root.after(1500, tick)
        self.root.after(1500, tick)

    def _render_status(self, tail: str, df: DerivedFiles) -> None:
        # Не ломаем основной вывод пользователя: добавляем внизу компактный блок.
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
        self.output.insert(END, f"log: {df.log_file.name} | progress: {df.progress_file.name} | out: {df.out_file.name}\n")
        self.output.insert(END, tail + "\n")
        self.output.see(END)

        if prev_state != "normal":
            try:
                self.output.configure(state=prev_state)
            except Exception:
                pass

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    app = VanityGUI()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


