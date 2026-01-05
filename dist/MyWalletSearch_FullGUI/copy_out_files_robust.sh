#!/bin/bash
# Надёжное копирование out файлов с таймаутами и обработкой ошибок

SERVER="root@38.117.87.47"
PORT="44236"
LOCAL_DIR="./server_results"

# Список файлов для копирования (из найденных ранее)
FILES=(
    "/root/MyWalletSearch/runs/out_1.txt"
    "/root/MyWalletSearch/runs/out_puzzle71_2.txt"
    "/root/MyWalletSearch/runs/out_puzzle71_3.txt"
    "/root/MyWalletSearch/out_mask.txt"
    "/root/MyWalletSearch/x64/ReleaseSM61/out_seg_prefix_suffix.txt"
    "/root/MyWalletSearch/x64/ReleaseSM61/out_seg_prefix_suffix_bits26.txt"
    "/root/MyWalletSearch/out_pref.txt"
    "/root/MyWalletSearch/out_cpu_p2.txt"
    "/root/MyWalletSearch/out_pref_suf.txt"
    "/root/MyWalletSearch/out_cpu_p3.txt"
    "/root/MyWalletSearch/out_gpu_range.txt"
    "/root/MyWalletSearch/old_results/out_gpu_b9_wide.txt"
    "/root/MyWalletSearch/out_cpu_71.5_72.5_24.txt"
    "/root/MyWalletSearch/out_cpu_p1.txt"
    "/root/MyWalletSearch/out_puzzle71_69_72.txt"
    "/root/MyWalletSearch/out_gpu_b9_wide.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_1.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_2.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_3.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_4.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_5.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_6.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_7.txt"
    "/root/MyWalletSearch/runs_cpu_gui/out_hex_87_89_8.txt"
    "/root/MyWalletSearch/out_optimal_120_74_3_74_6.txt"
    "/root/MyWalletSearch/out_optimal_120_winAvg_87_698_88_298.txt"
    "/root/MyWalletSearch/out_optimal_420_scatter_71_87.txt"
    "/root/MyWalletSearch/nohup.out"
)

mkdir -p "$LOCAL_DIR"

COPIED=0
FAILED=0
SKIPPED=0

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  📥 НАДЁЖНОЕ КОПИРОВАНИЕ OUT ФАЙЛОВ                                       ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Всего файлов: ${#FILES[@]}"
echo ""

for file in "${FILES[@]}"; do
    filename=$(basename "$file")
    
    # Пропускаем, если уже скопирован
    if [ -f "$LOCAL_DIR/$filename" ]; then
        size=$(ls -lh "$LOCAL_DIR/$filename" | awk '{print $5}')
        echo "⏭️  Пропущен (уже есть): $filename ($size)"
        ((SKIPPED++))
        continue
    fi
    
    echo -n "📥 Копирую: $filename ... "
    
    # Копируем с таймаутом и подавляем приветствие
    if timeout 600 scp -o ConnectTimeout=10 -o ServerAliveInterval=30 -P "$PORT" "$SERVER:$file" "$LOCAL_DIR/$filename" 2>&1 | grep -vE "(Welcome to vast|Have fun!)" > /dev/null 2>&1; then
        if [ -f "$LOCAL_DIR/$filename" ]; then
            size=$(ls -lh "$LOCAL_DIR/$filename" | awk '{print $5}')
            echo "✅ ($size)"
            ((COPIED++))
        else
            echo "❌ (файл не создан)"
            ((FAILED++))
        fi
    else
        # Проверяем ещё раз на случай успешного копирования несмотря на ошибку
        if [ -f "$LOCAL_DIR/$filename" ]; then
            size=$(ls -lh "$LOCAL_DIR/$filename" | awk '{print $5}')
            echo "✅ ($size)"
            ((COPIED++))
        else
            echo "❌ (ошибка/таймаут)"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  📊 РЕЗУЛЬТАТЫ                                                             ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Успешно скопировано: $COPIED"
echo "⏭️  Пропущено (уже есть): $SKIPPED"
echo "❌ Ошибок: $FAILED"
echo ""
echo "📁 Файлы в: $LOCAL_DIR"
echo ""
if [ "$COPIED" -gt 0 ] || [ "$SKIPPED" -gt 0 ]; then
    echo "📋 Скопированные файлы:"
    ls -lh "$LOCAL_DIR" | tail -n +2 | awk '{printf "   %-50s %8s\n", $9, $5}'
fi

