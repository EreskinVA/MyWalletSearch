# Интеграция генератора сегментов в GUI

## Шаг 1: Добавить кнопку в GUI

В файле `vanity_gui_unified.py`, найти строку ~630 где создается `seg_hdr` и добавить кнопку:

```python
# Найти эту секцию:
seg_hdr = ttk.Frame(seg_frame)
seg_hdr.pack(fill=X, padx=8, pady=(8, 0))
ttk.Button(seg_hdr, text="Load seg...", command=self.load_seg_file).pack(side=RIGHT)
ttk.Button(seg_hdr, text="Save seg as...", command=self.save_seg_file_as).pack(side=RIGHT, padx=6)

# Добавить ПОСЛЕ этих строк:
ttk.Button(seg_hdr, text="🎲 Сгенерировать сегменты...", command=self.generate_segments_dialog).pack(side=RIGHT, padx=6)
```

## Шаг 2: Добавить метод `generate_segments_dialog` в класс `VanityGUI`

Добавить этот метод в класс (например, после метода `save_seg_file_as`):

```python
def generate_segments_dialog(self) -> None:
    """Открывает диалог для генерации сегментов"""
    import smart_segment_generator as ssg
    
    dialog = Tk()
    dialog.title("Генератор сегментов")
    dialog.geometry("600x500")
    
    # Заголовок
    ttk.Label(dialog, text="🎲 Умный генератор сегментов", font=("TkDefaultFont", 14, "bold")).pack(pady=10)
    
    # Контейнер для полей
    main_frame = ttk.Frame(dialog)
    main_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)
    
    # Поля ввода
    row = 0
    
    # Битность (берём из GUI)
    ttk.Label(main_frame, text="Битность пазла:").grid(row=row, column=0, sticky="w", pady=5)
    bits_var = IntVar(value=self.bits.get())
    bits_entry = ttk.Entry(main_frame, textvariable=bits_var, width=10)
    bits_entry.grid(row=row, column=1, sticky="w", pady=5)
    ttk.Label(main_frame, text="(обычно 71)").grid(row=row, column=2, sticky="w", padx=10)
    row += 1
    
    # Начальный процент
    ttk.Label(main_frame, text="Начальный процент:").grid(row=row, column=0, sticky="w", pady=5)
    start_percent_var = StringVar(value="67.5")
    start_percent_entry = ttk.Entry(main_frame, textvariable=start_percent_var, width=10)
    start_percent_entry.grid(row=row, column=1, sticky="w", pady=5)
    ttk.Label(main_frame, text="(например 67.5)").grid(row=row, column=2, sticky="w", padx=10)
    row += 1
    
    # Конечный процент
    ttk.Label(main_frame, text="Конечный процент:").grid(row=row, column=0, sticky="w", pady=5)
    end_percent_var = StringVar(value="68.9")
    end_percent_entry = ttk.Entry(main_frame, textvariable=end_percent_var, width=10)
    end_percent_entry.grid(row=row, column=1, sticky="w", pady=5)
    ttk.Label(main_frame, text="(например 68.9)").grid(row=row, column=2, sticky="w", padx=10)
    row += 1
    
    # Разделитель
    ttk.Separator(main_frame, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
    row += 1
    
    # Сегментов в группе
    ttk.Label(main_frame, text="Сегментов в группе:").grid(row=row, column=0, sticky="w", pady=5)
    segs_per_group_var = IntVar(value=6)
    segs_per_group_entry = ttk.Entry(main_frame, textvariable=segs_per_group_var, width=10)
    segs_per_group_entry.grid(row=row, column=1, sticky="w", pady=5)
    ttk.Label(main_frame, text="(рекомендуется 6-12)").grid(row=row, column=2, sticky="w", padx=10)
    row += 1
    
    # Количество групп
    ttk.Label(main_frame, text="Количество групп:").grid(row=row, column=0, sticky="w", pady=5)
    num_groups_var = IntVar(value=3)
    num_groups_entry = ttk.Entry(main_frame, textvariable=num_groups_var, width=10)
    num_groups_entry.grid(row=row, column=1, sticky="w", pady=5)
    ttk.Label(main_frame, text="(обычно 1-5)").grid(row=row, column=2, sticky="w", padx=10)
    row += 1
    
    # Разделитель
    ttk.Separator(main_frame, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
    row += 1
    
    # Стратегия
    ttk.Label(main_frame, text="Стратегия:").grid(row=row, column=0, sticky="w", pady=5)
    strategy_var = StringVar(value="smart_mixed")
    strategy_combo = ttk.Combobox(main_frame, textvariable=strategy_var, width=20, state="readonly")
    strategy_combo['values'] = ["smart_mixed", "golden_ratio", "center_heavy", "edges_focus", "random_scatter"]
    strategy_combo.grid(row=row, column=1, sticky="w", pady=5, columnspan=2)
    row += 1
    
    # Описание стратегий
    strategy_desc = ttk.Label(main_frame, text="", wraplength=500, justify="left", foreground="gray")
    strategy_desc.grid(row=row, column=0, columnspan=3, sticky="w", pady=5)
    row += 1
    
    # Функция обновления описания
    def update_strategy_desc(*args):
        descriptions = {
            "smart_mixed": "🎯 Смешанная: центр (высокий приоритет) + края (зеркальные) + случайные точки",
            "golden_ratio": "✨ Золотое сечение: распределение по φ (0.618), элегантное покрытие",
            "center_heavy": "🔵 Акцент на центре: 60% в центре, 40% на краях",
            "edges_focus": "🔷 Акцент на краях: 70% на краях, 30% в центре",
            "random_scatter": "🎲 Случайный разброс: равномерное случайное распределение без перекрытий"
        }
        strategy_desc.config(text=descriptions.get(strategy_var.get(), ""))
    
    strategy_var.trace_add("write", update_strategy_desc)
    update_strategy_desc()
    
    # Минимальный размер сегмента
    ttk.Label(main_frame, text="Мин. размер сегмента:").grid(row=row, column=0, sticky="w", pady=5)
    min_size_var = IntVar(value=1000000)
    min_size_entry = ttk.Entry(main_frame, textvariable=min_size_var, width=15)
    min_size_entry.grid(row=row, column=1, sticky="w", pady=5)
    ttk.Label(main_frame, text="(ключей)").grid(row=row, column=2, sticky="w", padx=10)
    row += 1
    
    # Формат вывода
    ttk.Label(main_frame, text="Формат:").grid(row=row, column=0, sticky="w", pady=5)
    mode_var = StringVar(value="key")
    mode_frame = ttk.Frame(main_frame)
    mode_frame.grid(row=row, column=1, columnspan=2, sticky="w", pady=5)
    ttk.Radiobutton(mode_frame, text="key (hex)", variable=mode_var, value="key").pack(side="left")
    ttk.Radiobutton(mode_frame, text="abs (decimal)", variable=mode_var, value="abs").pack(side="left", padx=10)
    row += 1
    
    # Кнопки
    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill=X, padx=20, pady=10)
    
    result_text = {"segments": None}
    
    def generate():
        try:
            bits = bits_var.get()
            start_percent = float(start_percent_var.get())
            end_percent = float(end_percent_var.get())
            segs_per_group = segs_per_group_var.get()
            num_groups = num_groups_var.get()
            strategy = strategy_var.get()
            min_size = min_size_var.get()
            mode = mode_var.get()
            
            # Валидация
            if start_percent >= end_percent:
                self.log("[ГЕНЕРАТОР] ❌ Начальный процент должен быть меньше конечного\n")
                return
            if start_percent < 0 or end_percent > 100:
                self.log("[ГЕНЕРАТОР] ❌ Проценты должны быть в диапазоне 0-100\n")
                return
            if segs_per_group < 1 or num_groups < 1:
                self.log("[ГЕНЕРАТОР] ❌ Количество должно быть >= 1\n")
                return
            
            # Генерируем
            self.log(f"[ГЕНЕРАТОР] 🎲 Генерация: {start_percent}%-{end_percent}%, {segs_per_group}x{num_groups}, стратегия={strategy}\n")
            
            gen = ssg.SmartSegmentGenerator(bits=bits)
            groups = gen.generate_segments(
                start_percent=start_percent,
                end_percent=end_percent,
                segments_per_group=segs_per_group,
                num_groups=num_groups,
                strategy=strategy,
                min_segment_size=min_size
            )
            
            output_text = gen.format_segments(groups, mode=mode)
            result_text["segments"] = output_text
            
            # Статистика в лог
            total_segs = sum(len(g) for g in groups)
            self.log(f"[ГЕНЕРАТОР] ✅ Сгенерировано: {num_groups} групп, {total_segs} сегментов\n")
            
            # Закрываем диалог
            dialog.destroy()
            
            # Вставляем в GUI
            self.segments_text.delete("1.0", END)
            self.segments_text.insert("1.0", output_text)
            self._update_groups_count()
            
            self.log("[ГЕНЕРАТОР] ✅ Сегменты вставлены в поле. Нажмите START для запуска поиска.\n")
            
        except Exception as e:
            self.log(f"[ГЕНЕРАТОР] ❌ Ошибка: {e}\n")
            import traceback
            self.log(traceback.format_exc())
    
    def cancel():
        dialog.destroy()
    
    ttk.Button(button_frame, text="✅ Сгенерировать и вставить", command=generate).pack(side="left", padx=5)
    ttk.Button(button_frame, text="❌ Отмена", command=cancel).pack(side="left", padx=5)
    
    # Центрируем окно
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    dialog.focus()
    dialog.grab_set()
```

## Шаг 3: Импортировать модуль в начале файла

В начале файла `vanity_gui_unified.py` (после остальных импортов) добавить:

```python
# Добавить в секцию импортов (примерно строка 55-60)
try:
    import smart_segment_generator as ssg
    HAS_SEGMENT_GENERATOR = True
except Exception as e:
    HAS_SEGMENT_GENERATOR = False
    SEGMENT_GENERATOR_IMPORT_ERROR = e
```

## Шаг 4: Защита от отсутствия модуля

В методе `generate_segments_dialog`, в самом начале добавить проверку:

```python
def generate_segments_dialog(self) -> None:
    """Открывает диалог для генерации сегментов"""
    if not HAS_SEGMENT_GENERATOR:
        self.log(f"[ГЕНЕРАТОР] ❌ Модуль smart_segment_generator не найден: {SEGMENT_GENERATOR_IMPORT_ERROR}\n")
        return
    
    # ... остальной код ...
```

---

## Пример использования:

1. Запустить GUI: `python3 vanity_gui_unified.py`
2. Нажать кнопку **"🎲 Сгенерировать сегменты..."**
3. Задать параметры:
   - Битность: 71
   - Начальный %: 67.5
   - Конечный %: 68.9
   - Сегментов в группе: 6
   - Групп: 3
   - Стратегия: smart_mixed
4. Нажать **"✅ Сгенерировать и вставить"**
5. Сегменты будут вставлены в поле "Сегменты"
6. Нажать **START** для запуска поиска

---

## Стратегии генерации:

| Стратегия | Описание | Лучше для |
|-----------|----------|-----------|
| **smart_mixed** | Центр (высокий приоритет) + края (зеркальные) + случайные | Универсальный поиск |
| **golden_ratio** | Распределение по золотому сечению (φ = 0.618) | Элегантное покрытие |
| **center_heavy** | 60% сегментов в центре, 40% на краях | Если ключ вероятно в центре |
| **edges_focus** | 70% сегментов на краях, 30% в центре | Если ключ вероятно на краях |
| **random_scatter** | Равномерное случайное распределение без перекрытий | Исследование диапазона |

---

## Скриншот ожидаемого интерфейса:

```
╔═══════════════════════════════════════════════╗
║     🎲 Умный генератор сегментов             ║
╠═══════════════════════════════════════════════╣
║ Битность пазла:        [71        ] (обычно 71)
║ Начальный процент:     [67.5      ] (например 67.5)
║ Конечный процент:      [68.9      ] (например 68.9)
║ ─────────────────────────────────────────────
║ Сегментов в группе:    [6         ] (рекомендуется 6-12)
║ Количество групп:      [3         ] (обычно 1-5)
║ ─────────────────────────────────────────────
║ Стратегия:             [smart_mixed ▼]
║ 🎯 Смешанная: центр (высокий приоритет) + края...
║ Мин. размер сегмента:  [1000000   ] (ключей)
║ Формат:                ⦿ key (hex)  ○ abs (decimal)
║ ─────────────────────────────────────────────
║   [✅ Сгенерировать и вставить]  [❌ Отмена]
╚═══════════════════════════════════════════════╝
```

---

**Готово!** Теперь GUI имеет мощный инструмент для генерации сегментов! 🎉

