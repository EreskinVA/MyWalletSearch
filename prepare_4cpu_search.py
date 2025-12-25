#!/usr/bin/env python3
"""
Скрипт для разбиения диапазона на 4 части, каждую на 8 сегментов,
и подготовки команд для запуска на 4 CPU процессорах.
"""

start = 2128350382728406075874
end = 2128351282728406075898
prefix = "1PWo3JeB9jr"

total_range = end - start
print(f"Общий диапазон: {total_range:,}")
print(f"Размер одной части (на 4): {total_range // 4:,}")
print(f"Размер одного сегмента (на 8 в части): {(total_range // 4) // 8:,}")
print()

# Разбиваем на 4 части
part_size = total_range // 4
parts = []
for i in range(4):
    part_start = start + i * part_size
    part_end = start + (i + 1) * part_size if i < 3 else end
    parts.append((part_start, part_end))

# Для каждой части создаем 8 сегментов
segment_files = []
commands = []

for part_idx, (part_start, part_end) in enumerate(parts):
    part_num = part_idx + 1
    seg_file = f"seg_part{part_num}.txt"
    segment_files.append(seg_file)
    
    # Разбиваем часть на 8 сегментов
    seg_size = (part_end - part_start) // 8
    segments = []
    
    with open(seg_file, 'w') as f:
        f.write(f"# Сегменты для части {part_num}\n")
        f.write(f"# Диапазон: {part_start} -> {part_end}\n")
        f.write(f"# Размер сегмента: ~{seg_size:,}\n\n")
        
        for seg_idx in range(8):
            seg_start = part_start + seg_idx * seg_size
            seg_end = part_start + (seg_idx + 1) * seg_size if seg_idx < 7 else part_end
            seg_name = f"seg{part_num}_{seg_idx + 1}"
            
            # Используем явный префикс 'abs' для абсолютных диапазонов
            f.write(f"abs {seg_start} {seg_end} up {seg_name} 1\n")
            segments.append((seg_start, seg_end, seg_name))
    
    # Формируем команду для запуска
    output_file = f"out_part{part_num}.txt"
    log_file = f"log_part{part_num}.log"
    
    cmd = f"./VanitySearch -seg {seg_file} -bits 71 -t 1 -m 1000000 -o {output_file} \"{prefix}\" > {log_file} 2>&1"
    commands.append(cmd)
    
    print(f"=== Часть {part_num} ===")
    print(f"Файл сегментов: {seg_file}")
    print(f"Диапазон: {part_start} -> {part_end}")
    print(f"Сегментов: 8")
    print(f"Команда: {cmd}")
    print()

# Сохраняем команды в файл
with open("run_4cpu.sh", "w") as f:
    f.write("#!/bin/bash\n")
    f.write("# Команды для запуска на 4 CPU процессорах\n")
    f.write("# Запускать в разных терминалах или через nohup/background\n\n")
    
    for i, cmd in enumerate(commands, 1):
        f.write(f"# Процессор {i}\n")
        f.write(f"# {cmd}\n")
        f.write(f"nohup bash -c '{cmd}' &\n")
        f.write(f"echo \"Запущен процесс {i}, PID: $!\"\n\n")
    
    f.write("# Для просмотра статуса:\n")
    f.write("# ps aux | grep VanitySearch\n")
    f.write("# tail -f log_part*.log\n\n")

# Команда для подсчета найденных кошельков
count_cmd = "grep -h '^' out_part*.txt 2>/dev/null | wc -l"
count_cmd_detailed = """echo "=== Найдено кошельков ===" && \
for f in out_part*.txt; do \
  if [ -f "$f" ]; then \
    count=$(wc -l < "$f" 2>/dev/null || echo 0); \
    echo "$f: $count"; \
  fi; \
done && \
total=$(grep -h '^' out_part*.txt 2>/dev/null | wc -l); \
echo "Всего: $total\""""

with open("count_found.sh", "w") as f:
    f.write("#!/bin/bash\n")
    f.write("# Подсчет найденных кошельков из всех 4 экземпляров\n\n")
    f.write(count_cmd_detailed)
    f.write("\n")

# Делаем скрипты исполняемыми
import os
os.chmod("run_4cpu.sh", 0o755)
os.chmod("count_found.sh", 0o755)

print("=" * 80)
print("Созданы файлы:")
print(f"  - seg_part1.txt, seg_part2.txt, seg_part3.txt, seg_part4.txt")
print(f"  - run_4cpu.sh (скрипт для запуска всех 4 процессов)")
print(f"  - count_found.sh (скрипт для подсчета найденных кошельков)")
print()
print("=" * 80)
print("КОМАНДЫ ДЛЯ ЗАПУСКА (в отдельных терминалах или через nohup):")
print("=" * 80)
for i, cmd in enumerate(commands, 1):
    print(f"\n# Процессор {i}:")
    print(cmd)
print()
print("=" * 80)
print("КОМАНДА ДЛЯ ПОДСЧЕТА НАЙДЕННЫХ КОШЕЛЬКОВ:")
print("=" * 80)
print(f"./count_found.sh")
print("или")
print(count_cmd_detailed)
print()

