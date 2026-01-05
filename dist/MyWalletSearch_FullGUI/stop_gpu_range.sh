#!/bin/bash
set -euo pipefail

# Остановить именно GPU-запуск под seg_gpu_range.txt

echo "=== Stop GPU range search ==="
pgrep -fl "./VanitySearch -seg seg_gpu_range.txt" || true
pkill -f "./VanitySearch -seg seg_gpu_range.txt" || true

sleep 1
echo "Remaining VanitySearch:"
pgrep -fl VanitySearch || true


