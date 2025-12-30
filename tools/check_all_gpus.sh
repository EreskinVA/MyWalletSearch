#!/usr/bin/env bash
set -euo pipefail

# Автоподбор безопасного -g (gridX,128) для каждой GPU по результату "-check".
# Результат:
# - gpu_check_ok.tsv   : строки "gpuId<TAB>gridX<TAB>gridY"
# - gpu_check_fail.tsv : gpuId, которые не прошли check ни на одном gridX
#
# Использование:
#   cd VanitySearch
#   chmod +x tools/check_all_gpus.sh
#   MAXFOUND=4096 ./tools/check_all_gpus.sh
#
# Примечания:
# - MAXFOUND задаёт -m (по умолчанию 4096) — этого достаточно для check и экономит ресурсы.
# - gridY фиксирован 128 (как в примерах проекта).

BIN="${BIN:-./VanitySearch}"
MAXFOUND="${MAXFOUND:-4096}"

# Кандидаты gridX (от большего к меньшему)
CAND_X=(1024 768 512 384 256 192 128 96 64 48 32 16)
Y=128

if [[ ! -x "$BIN" ]]; then
  echo "Не найден бинарник: $BIN"
  echo "Запускай из директории VanitySearch или укажи BIN=путь"
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi не найден"
  exit 1
fi

GPU_COUNT="$(nvidia-smi -L | wc -l | tr -d ' ')"
echo "GPU обнаружено: $GPU_COUNT"
echo "MAXFOUND (-m): $MAXFOUND"
echo

ok_file="gpu_check_ok.tsv"
fail_file="gpu_check_fail.tsv"
: > "$ok_file"
: > "$fail_file"

for ((id=0; id<GPU_COUNT; id++)); do
  echo "=== GPU $id ==="
  nvidia-smi -i "$id" --query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu --format=csv,noheader || true
  echo

  found=""
  for x in "${CAND_X[@]}"; do
    echo "Пробую: -gpuId $id -g ${x},${Y}"

    # tail -200, чтобы быстрее анализировать и не засорять терминал.
    out="$("$BIN" -gpu -gpuId "$id" -g "${x},${Y}" -m "$MAXFOUND" -check 2>&1 | tail -200)"

    if echo "$out" | grep -q "GPU/CPU check OK"; then
      echo "OK на GPU $id: -g ${x},${Y}"
      echo -e "${id}\t${x}\t${Y}" >> "$ok_file"
      found="${x},${Y}"
      break
    fi

    if echo "$out" | grep -qi "out of memory"; then
      echo "OOM на ${x},${Y} -> уменьшаю"
      continue
    fi

    echo "Не OK (без явного OOM) -> уменьшаю"
  done

  if [[ -z "$found" ]]; then
    echo "FAIL: GPU $id не прошла check ни на одном -g"
    echo -e "${id}\tFAIL" >> "$fail_file"
  fi

  echo
done

echo "Готово."
echo "Успешные параметры: $ok_file"
echo "Проблемные GPU:     $fail_file"













