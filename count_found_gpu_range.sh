#!/bin/bash
set -euo pipefail

OUT_FILE="out_gpu_range.txt"

echo "=== Найдено кошельков (GPU range) ==="
if [ -f "$OUT_FILE" ]; then
  wc -l < "$OUT_FILE"
else
  echo "0 (файл $OUT_FILE не найден)"
fi


