#!/bin/bash
# Команды для запуска на 4 CPU процессорах
# Запускать в разных терминалах или через nohup/background

# Подготовка файлов (чтобы count_found.sh сразу работал и логи были чистые)
: > out_part1.txt
: > out_part2.txt
: > out_part3.txt
: > out_part4.txt
: > log_part1.log
: > log_part2.log
: > log_part3.log
: > log_part4.log

# Процессор 1
nohup bash -c './VanitySearch -seg seg_part1.txt -bits 71 -t 1 -m 1000000 -o out_part1.txt "1PWo3JeB9jr" > log_part1.log 2>&1' &
PID1=$!
echo "Запущен процесс 1, PID: $PID1"

# Процессор 2
nohup bash -c './VanitySearch -seg seg_part2.txt -bits 71 -t 1 -m 1000000 -o out_part2.txt "1PWo3JeB9jr" > log_part2.log 2>&1' &
PID2=$!
echo "Запущен процесс 2, PID: $PID2"

# Процессор 3
nohup bash -c './VanitySearch -seg seg_part3.txt -bits 71 -t 1 -m 1000000 -o out_part3.txt "1PWo3JeB9jr" > log_part3.log 2>&1' &
PID3=$!
echo "Запущен процесс 3, PID: $PID3"

# Процессор 4
nohup bash -c './VanitySearch -seg seg_part4.txt -bits 71 -t 1 -m 1000000 -o out_part4.txt "1PWo3JeB9jr" > log_part4.log 2>&1' &
PID4=$!
echo "Запущен процесс 4, PID: $PID4"

echo ""
echo "Все 4 процесса запущены!"
echo "Для просмотра статуса: ps aux | grep VanitySearch"
echo "Для просмотра логов: tail -f log_part*.log"
echo "Для подсчета результатов: ./count_found.sh"

