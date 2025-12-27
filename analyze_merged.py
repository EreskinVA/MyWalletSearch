#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор объединённого файла результатов VanitySearch.

Назначение:
- Анализировать объединённый файл результатов VanitySearch (где блоки начинаются с 'PubAddress:')
- Делать инженерно-исследовательский отчёт: статистика, "близость" к target, энтропия по позициям
- Генерировать максимально информативные паттерны для следующего запуска (-i patterns.txt)

Важно:
- Этот скрипт работает с одним объединённым файлом (созданным merge_out_files.py)
- Все остальные функции идентичны analyze_seg_74_5_76.py
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_N = len(BASE58_ALPHABET)

# Segment names in out files may contain suffix like "name (#5)". Normalize to match GUI segment names.
_SEG_SUFFIX_RE = re.compile(r"\s*\(#\d+\)\s*$")

# --- secp256k1 (для крипто-проверки соответствия Priv/PuzzleKeyAbs -> PubAddress) ---
SECP_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP_GX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
SECP_GY = 32670510020758816978083085130507043184471273380659243275938904335757337482424
# Endomorphism constants from Vanity.cpp (secp256k1)
SECP_LAMBDA = 0x5363AD4CC05C30E0A5261C028812645A122E22EA20816678DF02967C1B23BD72
SECP_LAMBDA2 = 0xAC9C52B33FA3CF1F5AD9E3FD77ED9BA4A880B9FC8EC739C2E0CFC810B51283CE


@dataclass(frozen=True)
class AnalyzerConfig:
    input_file: Path
    target_address: str = ""
    target_prefix: str = ""
    puzzle_bits: Optional[int] = 71
    max_records: Optional[int] = None
    suggest_patterns: int = 24
    entropy_positions: int = 34  # typical P2PKH length
    # Контекст (опционально) — полезен для отчёта при запуске из GUI
    search_patterns: Tuple[str, ...] = ()
    seg_groups: Tuple[Tuple[str, ...], ...] = ()
    # Крипто-проверка: 0=выкл, N=проверить первые N записей, -1=все
    verify_crypto: int = 0


def _parse_seg_line_name(line: str) -> str:
    """
    Мини-парсер строки seg.
    Формат в GUI:
      abs <start_dec> <end_dec> <up|down> <name> [priority]
      key <start_hex> <end_hex> <up|down> <name> [priority]
    """
    s = (line or "").strip()
    if not s or s.startswith("#"):
        return ""
    parts = s.split()
    if len(parts) < 5:
        return ""
    if parts[0] not in ("abs", "dec", "key"):
        return ""
    return parts[4].strip()


def _parse_seg_line(line: str) -> Optional[dict[str, Any]]:
    """
    Парсит строку сегмента из GUI и возвращает:
      {mode, start_int, end_int, direction, name, priority}
    direction: 'up'|'down'
    """
    s = (line or "").strip()
    if not s or s.startswith("#"):
        return None
    parts = s.split()
    if len(parts) < 5:
        return None
    mode = parts[0].lower()
    if mode not in ("abs", "dec", "key"):
        return None
    dir_s = parts[3].lower()
    if dir_s not in ("up", "down"):
        return None
    name = parts[4].strip()
    priority: Optional[int] = None
    if len(parts) >= 6:
        try:
            priority = int(parts[5])
        except Exception:
            priority = None

    try:
        if mode == "key":
            a = parts[1].replace("0x", "").replace("0X", "")
            b = parts[2].replace("0x", "").replace("0X", "")
            start_int = int(a, 16)
            end_int = int(b, 16)
        else:
            start_int = int(parts[1])
            end_int = int(parts[2])
    except Exception:
        return None

    return {
        "mode": mode,
        "start": start_int,
        "end": end_int,
        "direction": dir_s,
        "name": name,
        "priority": priority,
        "raw": line.rstrip("\n"),
    }


def _safe_int(x: str) -> Optional[int]:
    try:
        return int(str(x).strip())
    except Exception:
        return None


def _entropy_from_counts(counts: Counter) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    e = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            e -= p * math.log2(p)
    return e


def _kl_to_uniform_base58(counts: Counter) -> float:
    """
    KL(P || U) для распределения P по символам (сupport может быть подмножеством Base58),
    где U — равномерное по BASE58_ALPHABET.
    """
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    q = 1.0 / BASE58_N
    kl = 0.0
    for ch, c in counts.items():
        if c <= 0:
            continue
        p = c / total
        # если ch не base58, для KL считаем, что это отдельный "символ" (штрафуем)
        if ch not in BASE58_ALPHABET:
            # условно сравним с очень маленькой вероятностью
            kl += p * math.log2(p / 1e-12)
        else:
            kl += p * math.log2(p / q)
    return max(0.0, kl)


def _lcp(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _matches_by_position(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x == y)


def parse_result_file(filepath: Path) -> list[dict[str, str]]:
    """Парсит out-файл VanitySearch, собирая блоки по 'PubAddress:'."""
    results: list[dict[str, str]] = []
    current: dict[str, str] = {}

    with filepath.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("PubAddress:"):
                if current:
                    results.append(current)
                current = {"file": filepath.name}
                current["address"] = line.split(":", 1)[1].strip()
                continue

            if ":" not in line:
                continue

            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()

            if k == "Priv (HEX)":
                current["priv_hex"] = v
            elif k == "Priv (DEC)":
                current["priv_dec"] = v
            elif k == "Priv (WIF)":
                # Убираем префикс p2pkh: если есть
                wif = v.strip()
                if wif.startswith("p2pkh:"):
                    wif = wif[6:].strip()
                current["priv_wif"] = wif
            elif k == "PuzzlePos0 (DEC)":
                current["puzzle_pos0"] = v
            elif k == "PuzzleBits":
                current["puzzle_bits"] = v
            elif k == "PuzzleStart (DEC)":
                current["puzzle_start_dec"] = v
            elif k == "PuzzleKeyAbs (HEX)":
                current["puzzle_key_abs_hex"] = v
            elif k == "PuzzleKeyAbs (DEC)":
                current["puzzle_key_abs"] = v
            elif k == "SegKey (HEX)":
                current["seg_key_hex"] = v
            elif k == "SegKey (DEC)":
                current["seg_key"] = v
            elif k == "Segment":
                current["segment"] = _SEG_SUFFIX_RE.sub("", v).strip()
            elif k == "SegmentDir":
                current["segment_dir"] = v
            elif k == "SegmentOffset (DEC)":
                current["segment_offset"] = v

    if current:
        results.append(current)
    return results


def load_results(cfg: AnalyzerConfig) -> tuple[list[dict[str, str]], dict[str, int], list[Path]]:
    """Загружает результаты из одного объединённого файла."""
    input_file = cfg.input_file
    if not input_file.exists():
        raise FileNotFoundError(f"Файл не найден: {input_file}")
    
    parsed = parse_result_file(input_file)
    file_stats = {input_file.name: len(parsed)}
    
    all_results = parsed
    if cfg.max_records is not None and len(all_results) > cfg.max_records:
        all_results = all_results[: cfg.max_records]
    
    return all_results, file_stats, [input_file]


def _calc_puzzle_percentage(key_abs_dec: str, puzzle_bits: int) -> Optional[float]:
    """
    Положение ключа в диапазоне [2^(bits-1), 2^bits - 1] в процентах.
    Для bits=71: [2^70 .. 2^71 - 1]
    """
    key = _safe_int(key_abs_dec)
    if key is None:
        return None
    start = 2 ** (puzzle_bits - 1)
    end = 2**puzzle_bits - 1
    rng = end - start + 1
    if rng <= 0:
        return None
    pos = key - start
    return (pos / rng) * 100.0


def _abs_from_puzzle_pct(pct: float, puzzle_bits: int) -> int:
    """
    Инверсия для _calc_puzzle_percentage: pct -> abs key (int).
    pct в [0..100], bits задаёт диапазон [2^(bits-1) .. 2^bits-1].
    """
    start = 2 ** (puzzle_bits - 1)
    end = 2**puzzle_bits - 1
    rng = end - start + 1
    if rng <= 0:
        return start
    # clamp pct
    if pct < 0.0:
        pct = 0.0
    if pct > 100.0:
        pct = 100.0
    return start + int((pct / 100.0) * rng)


def _split_range(lo: int, hi: int, n: int) -> list[tuple[int, int]]:
    """Делит [lo..hi] на n подряд идущих поддиапазонов (почти равных)."""
    if n <= 0:
        return []
    if hi < lo:
        lo, hi = hi, lo
    size = hi - lo + 1
    if size <= 0:
        return []
    step = size // n
    if step <= 0:
        return [(lo, hi)]
    out: list[tuple[int, int]] = []
    cur = lo
    for i in range(n):
        a = cur
        b = hi if i == n - 1 else (cur + step - 1)
        out.append((a, b))
        cur = b + 1
        if cur > hi:
            break
    return out


def _hx(x: int) -> str:
    return "0x" + format(int(x), "x")


def _split_by_bit_boundaries(lo: int, hi: int, bit: int, *, max_segments: int = 128) -> list[tuple[int, int]]:
    """
    Делит диапазон [lo..hi] по границам кратности 2^bit.
    Это даёт континуальные куски, удобные для seg-файла.
    """
    if hi < lo:
        lo, hi = hi, lo
    if bit < 0:
        return [(lo, hi)]
    step = 1 << bit
    if step <= 0:
        return [(lo, hi)]
    out: list[tuple[int, int]] = []
    cur = lo
    # первая граница > lo
    next_boundary = ((cur // step) + 1) * step
    while cur <= hi and len(out) < max_segments:
        end = min(hi, next_boundary - 1)
        out.append((cur, end))
        cur = end + 1
        next_boundary += step
    if cur <= hi and len(out) < max_segments:
        out.append((cur, hi))
    return out


def _pick_bits_for_range(
    lo: int,
    hi: int,
    *,
    global_bits: Sequence[dict[str, Any]],
    want_min: int = 2,
    want_max: int = 16,
    take: int = 2,
) -> list[tuple[int, float, float, int]]:
    """
    Подбирает информативные биты (из global_bits), которые дают разумное число чанков внутри [lo..hi]
    при разрезе по границам 2^bit.
    Возвращает [(bit, H, p1, expected_chunks)].
    """
    if hi < lo:
        lo, hi = hi, lo
    size = hi - lo + 1
    cand: list[tuple[int, float, float, int]] = []
    for r in global_bits:
        try:
            b = int(r.get("bit"))
            H = float(r.get("H"))
            p1 = float(r.get("p1"))
        except Exception:
            continue
        if H <= 0.0:
            continue
        if b < 0 or b > 255:
            continue
        step = 1 << b
        if step <= 0:
            continue
        seg_est = int(size // step) + 1
        if want_min <= seg_est <= want_max:
            cand.append((b, H, p1, seg_est))
    # сильнее сигнал => ниже H, а среди них — меньше кусков
    cand.sort(key=lambda x: (x[1], x[3]))
    return cand[:take]

def _base58_encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out: list[str] = []
    while n > 0:
        n, r = divmod(n, 58)
        out.append(BASE58_ALPHABET[r])
    s = "".join(reversed(out)) if out else ""
    # leading 0x00 bytes -> leading '1'
    pad = 0
    for ch in b:
        if ch == 0:
            pad += 1
        else:
            break
    return ("1" * pad) + (s or "1")


def _base58_decode(s: str) -> bytes:
    s = (s or "").strip()
    if not s:
        return b""
    n = 0
    for ch in s:
        n *= 58
        idx = BASE58_ALPHABET.find(ch)
        if idx < 0:
            raise ValueError("non-base58 char")
        n += idx
    # to bytes (big-endian)
    b = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
    # leading '1' => leading zero bytes
    pad = 0
    for ch in s:
        if ch == "1":
            pad += 1
        else:
            break
    if pad:
        b = (b"\x00" * pad) + (b if b != b"\x00" else b"")
    return b


def _b58check_decode(s: str) -> tuple[bytes, bytes]:
    raw = _base58_decode(s)
    if len(raw) < 4:
        raise ValueError("too short")
    payload, chk = raw[:-4], raw[-4:]
    want = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if chk != want:
        raise ValueError("bad checksum")
    return payload, chk


def _decode_wif(wif: str) -> tuple[int, bool]:
    """
    Возвращает (priv_int, compressed).
    Поддержка mainnet WIF (0x80) только.
    """
    w = (wif or "").strip()
    if not w:
        raise ValueError("empty wif")
    payload, _chk = _b58check_decode(w)
    if payload[0:1] != b"\x80":
        raise ValueError("unsupported version")
    if len(payload) == 33:
        priv = int.from_bytes(payload[1:], "big")
        return priv, False
    if len(payload) == 34 and payload[-1:] == b"\x01":
        priv = int.from_bytes(payload[1:33], "big")
        return priv, True
    raise ValueError("bad wif length")


def _hamming_bits(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        raise ValueError("length mismatch")
    dist = 0
    for x, y in zip(a, b):
        dist += (x ^ y).bit_count()
    return dist


def _addr_hash160_from_p2pkh(addr: str) -> Optional[bytes]:
    """
    Пытается извлечь hash160 из base58check P2PKH адреса.
    Возвращает 20 байт или None.
    """
    try:
        payload, _chk = _b58check_decode(addr)
    except Exception:
        return None
    if len(payload) != 21:
        return None
    ver = payload[0]
    if ver != 0x00:
        return None
    return payload[1:]


def _match_wildcard(pattern: str, text: str) -> bool:
    """
    Простая проверка wildcard как в VanitySearch:
    '?' = любой символ, '*' = любой хвост (включая пустой).
    """
    p = (pattern or "").strip()
    t = text or ""
    if not p:
        return False
    # быстрые случаи
    if p == "*":
        return True
    # DP по символам (короткие строки => ок)
    pi, ti = 0, 0
    star = -1
    star_t = -1
    while ti < len(t):
        if pi < len(p) and (p[pi] == "?" or p[pi] == t[ti]):
            pi += 1
            ti += 1
            continue
        if pi < len(p) and p[pi] == "*":
            star = pi
            pi += 1
            star_t = ti
            continue
        if star != -1:
            pi = star + 1
            star_t += 1
            ti = star_t
            continue
        return False
    while pi < len(p) and p[pi] == "*":
        pi += 1
    return pi == len(p)


def _bit_entropy(p1: float) -> float:
    if p1 <= 0.0 or p1 >= 1.0:
        return 0.0
    return -(p1 * math.log2(p1) + (1.0 - p1) * math.log2(1.0 - p1))


def _hash160(b: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(b).digest()).digest()


def _b58check_p2pkh(pubkey_bytes: bytes) -> str:
    payload = b"\x00" + _hash160(pubkey_bytes)  # version 0x00
    chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _base58_encode(payload + chk)


def _jacobian_double(X1: int, Y1: int, Z1: int) -> tuple[int, int, int]:
    if Z1 == 0 or Y1 == 0:
        return 0, 1, 0
    p = SECP_P
    yy = (Y1 * Y1) % p
    S = (4 * X1 * yy) % p
    M = (3 * X1 * X1) % p
    X3 = (M * M - 2 * S) % p
    yyyy = (yy * yy) % p
    Y3 = (M * (S - X3) - 8 * yyyy) % p
    Z3 = (2 * Y1 * Z1) % p
    return X3 % p, Y3 % p, Z3 % p


def _jacobian_add(X1: int, Y1: int, Z1: int, X2: int, Y2: int, Z2: int) -> tuple[int, int, int]:
    if Z1 == 0:
        return X2, Y2, Z2
    if Z2 == 0:
        return X1, Y1, Z1
    p = SECP_P
    Z1Z1 = (Z1 * Z1) % p
    Z2Z2 = (Z2 * Z2) % p
    U1 = (X1 * Z2Z2) % p
    U2 = (X2 * Z1Z1) % p
    Z1_cub = (Z1Z1 * Z1) % p
    Z2_cub = (Z2Z2 * Z2) % p
    S1 = (Y1 * Z2_cub) % p
    S2 = (Y2 * Z1_cub) % p
    if U1 == U2:
        if S1 != S2:
            return 0, 1, 0
        return _jacobian_double(X1, Y1, Z1)
    H = (U2 - U1) % p
    R = (S2 - S1) % p
    HH = (H * H) % p
    HHH = (HH * H) % p
    U1HH = (U1 * HH) % p
    X3 = (R * R - HHH - 2 * U1HH) % p
    Y3 = (R * (U1HH - X3) - S1 * HHH) % p
    Z3 = (H * Z1 * Z2) % p
    return X3 % p, Y3 % p, Z3 % p


def _jacobian_to_affine(X: int, Y: int, Z: int) -> tuple[int, int]:
    if Z == 0:
        raise ValueError("infinity")
    p = SECP_P
    z2 = (Z * Z) % p
    z3 = (z2 * Z) % p
    inv_z2 = pow(z2, p - 2, p)
    inv_z3 = pow(z3, p - 2, p)
    x = (X * inv_z2) % p
    y = (Y * inv_z3) % p
    return x, y


def _pubkey_from_priv(priv_int: int, *, compressed: bool = True) -> bytes:
    if priv_int <= 0 or priv_int >= SECP_N:
        raise ValueError("priv out of range")
    k = priv_int
    X, Y, Z = 0, 1, 0  # infinity
    GX, GY, GZ = SECP_GX, SECP_GY, 1
    while k > 0:
        if k & 1:
            X, Y, Z = _jacobian_add(X, Y, Z, GX, GY, GZ)
        GX, GY, GZ = _jacobian_double(GX, GY, GZ)
        k >>= 1
    ax, ay = _jacobian_to_affine(X, Y, Z)
    xb = ax.to_bytes(32, "big")
    if not compressed:
        yb = ay.to_bytes(32, "big")
        return b"\x04" + xb + yb
    prefix = b"\x02" if (ay % 2 == 0) else b"\x03"
    return prefix + xb


def _addr_from_priv(priv_int: int, *, compressed: bool = True) -> str:
    return _b58check_p2pkh(_pubkey_from_priv(priv_int, compressed=compressed))


def _mod_n(x: int) -> int:
    return x % SECP_N


def _neg_n(x: int) -> int:
    return (-x) % SECP_N


def _mul_n(x: int, k: int) -> int:
    return (x * k) % SECP_N


def _classify_priv_from_seg(segk: int, priv: int) -> str:
    """
    Пытаемся объяснить, как из segKey получился печатаемый priv (в терминах логики Vanity.cpp):
    - segKey — "скаляр внутри заданного диапазона до endo/sym"
    - final key может быть умножен на lambda/lambda2 (endomorphism=1/2) и/или промодулен по n и/или негация (sym)
    Возвращает строковый класс: id, neg, lam, lam_neg, lam2, lam2_neg, unknown
    """
    s = _mod_n(segk)
    p = _mod_n(priv)
    if p == s:
        return "id"
    if p == _neg_n(s):
        return "neg"
    l1 = _mul_n(s, SECP_LAMBDA)
    if p == l1:
        return "lam"
    if p == _neg_n(l1):
        return "lam_neg"
    l2 = _mul_n(s, SECP_LAMBDA2)
    if p == l2:
        return "lam2"
    if p == _neg_n(l2):
        return "lam2_neg"
    return "unknown"


def _suggest_patterns(
    addresses: list[str],
    *,
    base_prefix: str,
    target_address: str,
    position_chars: dict[int, Counter],
    n: int,
) -> list[str]:
    """
    Паттерны для VanitySearch (-i file):
    - prefix + X* (где X — самый вероятный следующий символ)
    - prefix + target_next* (если задан target)
    - consensus-mask: фиксируем доминирующие позиции, остальные '?', и добавляем '*'
    """
    patterns: list[str] = []
    prefix = (base_prefix or "").strip()

    next_pos = len(prefix)
    if prefix and next_pos in position_chars:
        # больше кандидатов, чем n, чтобы хватило после дедупа
        for ch, _cnt in position_chars[next_pos].most_common(max(12, n)):
            patterns.append(f"{prefix}{ch}*")

    if target_address and prefix and len(target_address) > len(prefix):
        ch = target_address[len(prefix)]
        patterns.insert(0, f"{prefix}{ch}*")
        # если можем — добавим усиление на 2 символа
        if len(target_address) > len(prefix) + 1:
            ch2 = target_address[len(prefix) + 1]
            patterns.insert(0, f"{prefix}{ch}{ch2}*")

    # 2-символьные расширения (XY) сразу после префикса — очень "сильный" разрез.
    if prefix:
        pos1 = len(prefix)
        pos2 = pos1 + 1
        pair_counts: Counter = Counter()
        for a in addresses:
            if not a.startswith(prefix):
                continue
            if len(a) <= pos2:
                continue
            pair_counts[(a[pos1], a[pos2])] += 1
        for (c1, c2), _cnt in pair_counts.most_common(max(16, n)):
            patterns.append(f"{prefix}{c1}{c2}*")

        # 3-символьные расширения (XYZ) — полезно, когда XY уже стабилизировалось.
        pos3 = pos2 + 1
        tri_counts: Counter = Counter()
        for a in addresses:
            if not a.startswith(prefix):
                continue
            if len(a) <= pos3:
                continue
            tri_counts[(a[pos1], a[pos2], a[pos3])] += 1
        for (c1, c2, c3), _cnt in tri_counts.most_common(max(12, n)):
            patterns.append(f"{prefix}{c1}{c2}{c3}*")

    if addresses:
        lens = Counter(len(a) for a in addresses)
        typical_len = lens.most_common(1)[0][0] if lens else 34
        max_len = min(typical_len, max(10, len(prefix) + 10))
        mask_chars: list[str] = []
        for i in range(max_len):
            if i < len(prefix):
                mask_chars.append(prefix[i])
                continue
            c = position_chars.get(i)
            if not c:
                mask_chars.append("?")
                continue
            total = sum(c.values())
            ch, cnt = c.most_common(1)[0]
            dom = cnt / total if total else 0.0
            mask_chars.append(ch if dom >= 0.35 else "?")
        patterns.append("".join(mask_chars) + "*")

    uniq: list[str] = []
    seen = set()
    for p in patterns:
        p = p.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        uniq.append(p)
        if len(uniq) >= max(1, n):
            break
    return uniq


def _surprisal_bits(p: float) -> float:
    if p <= 0.0:
        return float("inf")
    return -math.log2(p)


def _conditional_ngrams(addresses: list[str], prefix: str, n: int) -> Counter:
    """
    Считает n-граммы сразу после фиксированного prefix.
    n=1 => следующий символ; n=2 => пара; n=3 => тройка.
    """
    if not prefix or n <= 0:
        return Counter()
    pos = len(prefix)
    out: Counter = Counter()
    for a in addresses:
        if not a.startswith(prefix):
            continue
        if len(a) < pos + n:
            continue
        gram = a[pos : pos + n]
        out[gram] += 1
    return out


def _dedup_keep_order(xs: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        x = (x or "").strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _build_target_pattern_pack(target: str, *, base_prefix: str = "", max_items: int = 32) -> list[str]:
    """
    Паттерны, которые "давят" в target слева направо:
    - лестница target[:k]*
    - несколько "разветвлений" на 1 символ: target[:k] + ? + *
    """
    t = (target or "").strip()
    if not t:
        return []
    # базовый префикс: если указан base_prefix, начинаем минимум от него (иначе от 7)
    k0 = max(len(base_prefix.strip()), 7)
    k0 = min(k0, len(t))
    pats: list[str] = []
    # лестница (чем длиннее, тем сильнее)
    for k in range(max(7, k0), min(len(t), k0 + 12) + 1):
        pats.append(t[:k] + "*")
    # разветвления на 1 символ после k0..k0+3 (чтобы не переобучиться на единичный символ)
    for k in range(k0, min(len(t) - 1, k0 + 3) + 1):
        pats.append(t[:k] + "?*")
    return _dedup_keep_order(pats)[:max_items]


def _build_signal_pattern_pack(cond_by_prefix: dict[str, dict[str, Any]], *, focus_prefix: str, max_items: int = 64) -> list[str]:
    """
    Паттерны, которые максимизируют "сигнал" по статистике находок:
    - берём top из conditional n=1/n=2/n=3 для focus_prefix
    """
    d = cond_by_prefix.get(focus_prefix) if cond_by_prefix else None
    if not d:
        return []
    pats: list[str] = []
    for key in ("n3", "n2", "n1"):
        dn = d.get(key) or {}
        top = dn.get("top") or []
        for t in top[:12]:
            gram = t.get("gram")
            if not gram:
                continue
            pats.append(focus_prefix + gram + "*")
    return _dedup_keep_order(pats)[:max_items]


def _build_signal_pattern_pack_long_first(
    cond_by_prefix: dict[str, dict[str, Any]], *, focus_prefix: str, max_items: int = 64
) -> list[str]:
    """
    SIGNAL pack в режиме long-grams-first:
    n=3 -> n=2 -> n=1 (для каждого — top candidates).
    """
    return _build_signal_pattern_pack(cond_by_prefix, focus_prefix=focus_prefix, max_items=max_items)


def _build_signal_pattern_pack_high_prob(
    cond_by_prefix: dict[str, dict[str, Any]],
    *,
    focus_prefix: str,
    p_min: float = 0.05,
    max_items: int = 64,
) -> list[str]:
    """
    SIGNAL pack в режиме high-prob:
    берём кандидаты из n=3/n=2/n=1, но только где p >= p_min.
    """
    d = cond_by_prefix.get(focus_prefix) if cond_by_prefix else None
    if not d:
        return []
    pats: list[str] = []
    for key in ("n3", "n2", "n1"):
        dn = d.get(key) or {}
        top = dn.get("top") or []
        for t in top:
            p = float(t.get("p") or 0.0)
            gram = t.get("gram")
            if not gram:
                continue
            if p >= p_min:
                pats.append(focus_prefix + gram + "*")
    return _dedup_keep_order(pats)[:max_items]

def _segment_ranges_overlap_gaps(seg_defs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Анализ перекрытий/дыр между введёнными сегментами (только по abs/dec/key, через нормализацию lo/hi).
    Возвращает сводку + топ перекрытий/дыр.
    """
    ranges: list[dict[str, Any]] = []
    for sd in seg_defs:
        a = int(sd["start"])
        b = int(sd["end"])
        lo = min(a, b)
        hi = max(a, b)
        if hi < lo:
            continue
        ranges.append(
            {
                "name": sd.get("name"),
                "group": sd.get("group"),
                "direction": sd.get("direction"),
                "lo": lo,
                "hi": hi,
                "size": hi - lo + 1,
            }
        )
    ranges.sort(key=lambda x: (x["lo"], x["hi"]))
    if not ranges:
        return {"ranges": 0, "total_size": 0, "union_size": 0, "overlap_total": 0, "gap_total": 0, "overlaps": [], "gaps": []}

    overlaps: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    total_size = sum(r["size"] for r in ranges)
    union_size = 0
    overlap_total = 0
    gap_total = 0

    cur_lo = ranges[0]["lo"]
    cur_hi = ranges[0]["hi"]
    prev = ranges[0]
    for r in ranges[1:]:
        if r["lo"] <= cur_hi:
            # overlap
            ov_lo = r["lo"]
            ov_hi = min(cur_hi, r["hi"])
            ov = max(0, ov_hi - ov_lo + 1)
            overlap_total += ov
            overlaps.append(
                {
                    "size": ov,
                    "a": prev,
                    "b": r,
                    "ov_lo": ov_lo,
                    "ov_hi": ov_hi,
                }
            )
            # extend union window
            cur_hi = max(cur_hi, r["hi"])
        else:
            # gap
            union_size += (cur_hi - cur_lo + 1)
            gap_lo = cur_hi + 1
            gap_hi = r["lo"] - 1
            gp = max(0, gap_hi - gap_lo + 1)
            gap_total += gp
            gaps.append({"size": gp, "left": prev, "right": r, "gap_lo": gap_lo, "gap_hi": gap_hi})
            cur_lo = r["lo"]
            cur_hi = r["hi"]
        prev = r
    union_size += (cur_hi - cur_lo + 1)

    overlaps.sort(key=lambda x: x["size"], reverse=True)
    gaps.sort(key=lambda x: x["size"], reverse=True)
    return {
        "ranges": len(ranges),
        "total_size": total_size,
        "union_size": union_size,
        "overlap_total": overlap_total,
        "gap_total": gap_total,
        "overlaps": overlaps[:10],
        "gaps": gaps[:10],
    }


def analyze_results(cfg: AnalyzerConfig) -> dict[str, Any]:
    all_results, file_stats, files = load_results(cfg)
    addresses = [r.get("address", "") for r in all_results if r.get("address")]

    # Puzzle range helpers (если включён puzzle_bits)
    puzzle_start_rng: Optional[int] = None
    puzzle_end_rng: Optional[int] = None
    if isinstance(cfg.puzzle_bits, int) and cfg.puzzle_bits > 0:
        puzzle_start_rng = 2 ** (cfg.puzzle_bits - 1)
        puzzle_end_rng = 2**cfg.puzzle_bits - 1

    # Дубликаты по файлам (чтобы понять, это "реальные повторы" или повторная запись/пересечения сегментов)
    addr_files: dict[str, set[str]] = defaultdict(set)
    for r in all_results:
        a = r.get("address")
        fn = r.get("file")
        if a and fn:
            addr_files[a].add(fn)

    uniq_addresses = set(addresses)
    dup_count = len(addresses) - len(uniq_addresses)
    dup_top = [a for a, c in Counter(addresses).most_common(10) if c > 1]

    invalid_chars: Counter = Counter()
    length_dist: Counter = Counter()
    leading_ones: Counter = Counter()
    for a in addresses:
        length_dist[len(a)] += 1
        n1 = 0
        for ch in a:
            if ch == "1":
                n1 += 1
            else:
                break
        leading_ones[n1] += 1
        for ch in a:
            if ch not in BASE58_ALPHABET:
                invalid_chars[ch] += 1

    position_chars: dict[int, Counter] = defaultdict(Counter)
    for a in addresses:
        for i, ch in enumerate(a):
            position_chars[i][ch] += 1

    target = (cfg.target_address or "").strip()
    closest: list[tuple[str, int, int]] = []
    if target:
        for a in addresses:
            closest.append((a, _lcp(a, target), _matches_by_position(a, target)))
        closest.sort(key=lambda x: (x[1], x[2]), reverse=True)

    prefix = (cfg.target_prefix or "").strip()
    if not prefix and target:
        prefix = target[:7]
    prefix_matches = [a for a in addresses if prefix and a.startswith(prefix)]

    # Hash160 distance to target (для P2PKH)
    target_h160 = _addr_hash160_from_p2pkh(target) if target else None
    h160_stats: dict[str, Any] = {
        "target_ok": bool(target_h160),
        "checked": 0,
        "ok": 0,
        "avg_hamming": None,
        "best": [],
        "per_byte": [],
    }
    addr_hamming: dict[str, int] = {}
    if target_h160 is not None:
        dists: list[tuple[str, int]] = []
        per_byte_ones: list[int] = [0] * 20
        per_byte_total = 0
        for a in addresses:
            ah = _addr_hash160_from_p2pkh(a)
            h160_stats["checked"] += 1
            if ah is None:
                continue
            per_byte_total += 1
            h160_stats["ok"] += 1
            dist = _hamming_bits(ah, target_h160)
            addr_hamming[a] = dist
            dists.append((a, dist))
            for i in range(20):
                per_byte_ones[i] += (ah[i] ^ target_h160[i]).bit_count()
        if dists:
            dists.sort(key=lambda x: x[1])
            h160_stats["best"] = dists[:10]
            h160_stats["avg_hamming"] = sum(d for _a, d in dists) / len(dists)
        if per_byte_total > 0:
            # среднее число отличающихся бит на байт (0..8)
            h160_stats["per_byte"] = [x / per_byte_total for x in per_byte_ones]

    entropies: list[tuple[int, float, str]] = []
    for i in range(max(0, cfg.entropy_positions)):
        c = position_chars.get(i)
        if not c:
            continue
        entropies.append((i, _entropy_from_counts(c), c.most_common(1)[0][0]))

    # Информативность позиций: KL(P||U) относительно равномерного Base58
    kl_positions: list[tuple[int, float, str, float]] = []
    for i in range(max(0, cfg.entropy_positions)):
        c = position_chars.get(i)
        if not c:
            continue
        total = sum(c.values())
        top_ch, top_cnt = c.most_common(1)[0]
        top_p = (top_cnt / total) if total else 0.0
        kl_positions.append((i, _kl_to_uniform_base58(c), top_ch, top_p))
    kl_positions.sort(key=lambda x: x[1], reverse=True)

    # Условные энтропии/выигрыш для паттернов X/XY/XYZ
    # Считаем для нескольких "разумных" префиксов:
    # - текущий prefix (из GUI)
    # - базовый target[:7] (если target задан) — обычно даёт гораздо больше статистики
    cond_by_prefix: dict[str, dict[str, Any]] = {}
    prefixes_to_eval: list[str] = []
    if prefix:
        prefixes_to_eval.append(prefix)
    if target:
        for k in (7, 8, 9):
            if len(target) >= k:
                prefixes_to_eval.append(target[:k])
    # unique keep order
    seenp = set()
    prefixes_to_eval2: list[str] = []
    for pfx in prefixes_to_eval:
        pfx = (pfx or "").strip()
        if not pfx or pfx in seenp:
            continue
        seenp.add(pfx)
        prefixes_to_eval2.append(pfx)

    for pfx in prefixes_to_eval2:
        d: dict[str, Any] = {"prefix": pfx}
        for n in (1, 2, 3):
            c = _conditional_ngrams(addresses, pfx, n)
            total = sum(c.values())
            if total <= 0:
                d[f"n{n}"] = {"n": n, "total": 0, "H": 0.0, "eff": 0.0, "top": []}
                continue
            H = _entropy_from_counts(c)
            eff = 2**H
            top: list[dict[str, Any]] = []
            for gram, cnt in c.most_common(12):
                p = cnt / total
                top.append({"gram": gram, "cnt": cnt, "p": p, "bits": _surprisal_bits(p)})
            d[f"n{n}"] = {"n": n, "total": total, "H": H, "eff": eff, "top": top}
        cond_by_prefix[pfx] = d

    pct_list: list[tuple[str, float, str]] = []
    puzzle_integrity: dict[str, Any] = {
        "checked": 0,
        "ok_in_range": 0,
        "ok_start_pos0_abs": 0,
        "ok_hex_dec": 0,
        "bad_samples": [],
    }
    if cfg.puzzle_bits is not None:
        for r in all_results:
            ka = r.get("puzzle_key_abs")
            if not ka:
                continue
            # фильтруем выбросы вне диапазона (они бывают из-за boundary effects в сегментном переборе)
            if puzzle_start_rng is not None and puzzle_end_rng is not None:
                ka_i = _safe_int(ka)
                if ka_i is None or not (puzzle_start_rng <= ka_i <= puzzle_end_rng):
                    continue
            pct = _calc_puzzle_percentage(ka, cfg.puzzle_bits)
            if pct is None:
                continue
            pct_list.append((r.get("address", ""), pct, r.get("segment", "N/A")))
        pct_list.sort(key=lambda x: x[1])

        # Математические инварианты из самого out-файла:
        # - abs в диапазоне [2^(bits-1) .. 2^bits-1]
        # - PuzzleStart + PuzzlePos0 == PuzzleKeyAbs
        # - PuzzleKeyAbs(HEX) == PuzzleKeyAbs(DEC)
        start_rng = 2 ** (cfg.puzzle_bits - 1)
        end_rng = 2**cfg.puzzle_bits - 1
        for r in all_results:
            ka_dec_s = r.get("puzzle_key_abs")
            if not ka_dec_s:
                continue
            ka_dec = _safe_int(ka_dec_s)
            if ka_dec is None:
                continue
            puzzle_integrity["checked"] += 1
            in_range = (start_rng <= ka_dec <= end_rng)
            if in_range:
                puzzle_integrity["ok_in_range"] += 1
            ps = _safe_int(r.get("puzzle_start_dec", ""))
            p0 = _safe_int(r.get("puzzle_pos0", ""))
            ok_sum = (ps is not None and p0 is not None and (ps + p0 == ka_dec))
            if ok_sum:
                puzzle_integrity["ok_start_pos0_abs"] += 1
            hx = (r.get("puzzle_key_abs_hex") or "").strip()
            ok_hex = False
            if hx:
                try:
                    hxv = int(hx.lower().replace("0x", ""), 16)
                    if hxv == ka_dec:
                        puzzle_integrity["ok_hex_dec"] += 1
                        ok_hex = True
                except Exception:
                    pass
            # record anomalies (first few)
            if (not in_range) or (not ok_sum) or (hx and not ok_hex):
                if len(puzzle_integrity["bad_samples"]) < 8:
                    puzzle_integrity["bad_samples"].append(
                        {
                            "file": r.get("file"),
                            "addr": r.get("address"),
                            "seg": r.get("segment"),
                            "ka_dec": ka_dec_s,
                            "ka_hex": r.get("puzzle_key_abs_hex"),
                            "pbits": r.get("puzzle_bits"),
                            "pstart": r.get("puzzle_start_dec"),
                            "pos0": r.get("puzzle_pos0"),
                        }
                    )

    # Крипто-проверка: какой именно scalar соответствует PubAddress
    crypto_verify: dict[str, Any] = {"checked": 0, "match_priv": 0, "match_puzzle": 0, "match_seg": 0, "mismatch": 0, "samples": []}
    if cfg.verify_crypto != 0:
        recs = [r for r in all_results if r.get("address")]
        if cfg.verify_crypto > 0:
            recs = recs[: cfg.verify_crypto]

        for r in recs:
            addr = r.get("address", "")
            # По умолчанию считаем compressed (в out часто WIF начинается с K/L).
            compressed = True
            wif = (r.get("priv_wif") or "").split(":", 1)[-1].strip()
            if wif and wif[0] == "5":
                compressed = False

            def _try_int(val: Optional[int]) -> bool:
                if val is None:
                    return False
                try:
                    return _addr_from_priv(val, compressed=compressed) == addr
                except Exception:
                    return False

            priv_int: Optional[int] = None
            if r.get("priv_hex"):
                try:
                    priv_int = int(r["priv_hex"].lower().replace("0x", ""), 16)
                except Exception:
                    priv_int = None

            puzzle_int: Optional[int] = None
            if r.get("puzzle_key_abs"):
                puzzle_int = _safe_int(r.get("puzzle_key_abs", ""))
            if puzzle_int is None and r.get("puzzle_key_abs_hex"):
                try:
                    puzzle_int = int(r["puzzle_key_abs_hex"].lower().replace("0x", ""), 16)
                except Exception:
                    puzzle_int = None

            seg_int: Optional[int] = None
            if r.get("seg_key"):
                seg_int = _safe_int(r.get("seg_key", ""))

            m_priv = _try_int(priv_int)
            m_puz = _try_int(puzzle_int)
            m_seg = _try_int(seg_int)

            crypto_verify["checked"] += 1
            if m_priv:
                crypto_verify["match_priv"] += 1
            if m_puz:
                crypto_verify["match_puzzle"] += 1
            if m_seg:
                crypto_verify["match_seg"] += 1
            if not (m_priv or m_puz or m_seg):
                crypto_verify["mismatch"] += 1
                if len(crypto_verify["samples"]) < 8:
                    crypto_verify["samples"].append(
                        {
                            "addr": addr,
                            "priv_hex": r.get("priv_hex"),
                            "puzzle_hex": r.get("puzzle_key_abs_hex"),
                            "puzzle_dec": r.get("puzzle_key_abs"),
                            "seg_dec": r.get("seg_key"),
                        }
                    )

    # WIF integrity: decode WIF and verify matches priv_hex and compression
    # Битовый анализ по segKey (и по классам происхождения priv)
    # Источник segKey: seg_key (DEC) -> fallback puzzle_key_abs (DEC)
    segkeys: list[int] = []
    segkey_by_addr: dict[str, int] = {}
    segkey_class_rows: list[tuple[int, str]] = []  # (segk, class)
    for r in all_results:
        seg_int = _safe_int(r.get("seg_key", "")) if r.get("seg_key") else None
        if seg_int is None and r.get("puzzle_key_abs"):
            seg_int = _safe_int(r.get("puzzle_key_abs", ""))
        if seg_int is None:
            continue
        # если задан puzzle_bits, ограничиваем bit-аналитику тем же диапазоном (иначе 1 выброс ломает окно/биты)
        if puzzle_start_rng is not None and puzzle_end_rng is not None:
            if not (puzzle_start_rng <= seg_int <= puzzle_end_rng):
                continue
        segkeys.append(seg_int)
        if r.get("address"):
            segkey_by_addr[r["address"]] = seg_int
        # class: reuse provenance classifier when priv_hex exists, else unknown
        cls = "unknown"
        if r.get("priv_hex"):
            try:
                priv_int = int(r["priv_hex"].lower().replace("0x", ""), 16)
                cls = _classify_priv_from_seg(seg_int, priv_int)
            except Exception:
                cls = "unknown"
        segkey_class_rows.append((seg_int, cls))

    bit_stats: dict[str, Any] = {"count": len(segkeys), "bits": 0, "global": [], "by_class": {}}
    if segkeys:
        maxbits = max(1, max(x.bit_length() for x in segkeys))
        maxbits = min(maxbits, 256)
        bit_stats["bits"] = maxbits
        # global
        rows = []
        for b in range(maxbits):
            ones = sum((k >> b) & 1 for k in segkeys)
            p1 = ones / len(segkeys)
            H = _bit_entropy(p1)
            rows.append({"bit": b, "p1": p1, "H": H})
        # sort by most "useful for narrowing": low entropy but not fully fixed
        rows_sorted = sorted(rows, key=lambda x: x["H"])
        bit_stats["global"] = rows_sorted[:24]

        # by class
        byc: dict[str, list[int]] = defaultdict(list)
        for k, cls in segkey_class_rows:
            byc[cls].append(k)
        for cls, ks in byc.items():
            if len(ks) < 5:
                continue
            rr = []
            mb = min(maxbits, max(x.bit_length() for x in ks))
            for b in range(mb):
                ones = sum((k >> b) & 1 for k in ks)
                p1 = ones / len(ks)
                rr.append({"bit": b, "p1": p1, "H": _bit_entropy(p1)})
            bit_stats["by_class"][cls] = sorted(rr, key=lambda x: x["H"])[:12]

    # ΔsegKey анализ (stride / gcd / hotspots)
    delta_stats: dict[str, Any] = {"count": 0, "gcd": None, "top_deltas": []}
    uniq_seg = sorted(set(segkeys))
    if len(uniq_seg) >= 3:
        deltas = [uniq_seg[i + 1] - uniq_seg[i] for i in range(len(uniq_seg) - 1)]
        # gcd
        g = 0
        for d in deltas:
            g = math.gcd(g, d)
        delta_stats["count"] = len(deltas)
        delta_stats["gcd"] = g
        delta_stats["top_deltas"] = Counter(deltas).most_common(10)

    # "Bandit" оценка паттернов: reward по LCP и hash160 distance
    pattern_bandit: dict[str, Any] = {"evaluated": 0, "top": []}
    cand_patterns: list[str] = []
    # используем те, что уже сформированы
    cand_patterns.extend(_build_target_pattern_pack(target, base_prefix=prefix, max_items=32))
    # signal packs (из cond_by_prefix)
    focus_prefix = "1PWo3JeB"
    cand_patterns.extend(_build_signal_pattern_pack_high_prob(cond_by_prefix, focus_prefix=focus_prefix, p_min=0.05, max_items=32))
    cand_patterns.extend(_build_signal_pattern_pack_long_first(cond_by_prefix, focus_prefix=focus_prefix, max_items=32))
    cand_patterns = _dedup_keep_order(cand_patterns)

    uniq_addrs = sorted(set(addresses))
    scored = []
    for pat in cand_patterns:
        matched = [a for a in uniq_addrs if _match_wildcard(pat, a)]
        if not matched:
            continue
        cov = len(matched) / len(uniq_addrs) if uniq_addrs else 0.0
        best_lcp = max(_lcp(a, target) for a in matched) if target else 0
        # avg hamming if possible
        if addr_hamming:
            dvals = [addr_hamming.get(a) for a in matched if a in addr_hamming]
            avg_h = (sum(dvals) / len(dvals)) if dvals else None
        else:
            avg_h = None
        # score: prefer higher LCP, lower avg_h, and not too wide coverage
        score = float(best_lcp)
        if avg_h is not None:
            score += (160.0 - avg_h) / 160.0 * 4.0
        # penalize too wide patterns
        score -= cov * 2.0
        scored.append({"pattern": pat, "cov": cov, "best_lcp": best_lcp, "avg_hamming": avg_h, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    pattern_bandit["evaluated"] = len(scored)
    pattern_bandit["top"] = scored[:20]
    wif_integrity: dict[str, Any] = {
        "checked": 0,
        "ok_decode": 0,
        "ok_priv_match": 0,
        "ok_compression_flag": 0,
        "bad": 0,
        "compressed": 0,
        "uncompressed": 0,
    }
    for r in all_results:
        wif_full = (r.get("priv_wif") or "").strip()
        if not wif_full:
            continue
        wif = wif_full.split(":", 1)[-1].strip()
        if not wif:
            continue
        wif_integrity["checked"] += 1
        try:
            w_priv, w_comp = _decode_wif(wif)
            wif_integrity["ok_decode"] += 1
        except Exception:
            wif_integrity["bad"] += 1
            continue
        # compare to priv_hex if present
        if r.get("priv_hex"):
            try:
                p = int(r["priv_hex"].lower().replace("0x", ""), 16)
                if _mod_n(p) == _mod_n(w_priv):
                    wif_integrity["ok_priv_match"] += 1
            except Exception:
                pass
        # heuristic: if WIF says compressed, address should be compressed too; we already infer in crypto checks,
        # but here we just count consistency within WIF itself.
        if w_comp in (True, False):
            wif_integrity["ok_compression_flag"] += 1
            if w_comp:
                wif_integrity["compressed"] += 1
            else:
                wif_integrity["uncompressed"] += 1

    # Исследовательский анализ преобразований ключа (без эллиптики): segKey -> printed priv
    # Это помогает понять, какой endomorphism/negation реально использовался.
    key_provenance: dict[str, Any] = {"total": 0, "by_class": Counter(), "examples": []}
    for r in all_results:
        if not r.get("priv_hex"):
            continue
        try:
            priv_int = int(r["priv_hex"].lower().replace("0x", ""), 16)
        except Exception:
            continue
        seg_int = _safe_int(r.get("seg_key", "")) if r.get("seg_key") else None
        # fallback: если seg_key отсутствует, берём puzzle_key_abs (это тот же "abs" в puzzle-диапазоне)
        if seg_int is None and r.get("puzzle_key_abs"):
            seg_int = _safe_int(r.get("puzzle_key_abs", ""))
        if seg_int is None:
            continue
        cls = _classify_priv_from_seg(seg_int, priv_int)
        key_provenance["total"] += 1
        key_provenance["by_class"][cls] += 1
        if cls != "unknown" and len(key_provenance["examples"]) < 8:
            key_provenance["examples"].append(
                {
                    "class": cls,
                    "addr": r.get("address", ""),
                    "seg_dec": seg_int,
                    "priv_hex": r.get("priv_hex"),
                    "priv_mod_n_hex": _hx(_mod_n(priv_int)),
                }
            )

    # Доп. "hacker" тесты на ошибочную интерпретацию (endianness / bit-mirror) — только в рамках crypto_verify sample set
    crypto_weird: dict[str, Any] = {"checked": 0, "match_priv_le": 0, "match_priv_revbits": 0}
    if cfg.verify_crypto != 0:
        recs = [r for r in all_results if r.get("address") and r.get("priv_hex")]
        if cfg.verify_crypto > 0:
            recs = recs[: cfg.verify_crypto]
        for r in recs:
            try:
                priv_int = int(r["priv_hex"].lower().replace("0x", ""), 16)
            except Exception:
                continue
            addr = r.get("address", "")
            wif = (r.get("priv_wif") or "").split(":", 1)[-1].strip()
            compressed = not (wif and wif[0] == "5")
            crypto_weird["checked"] += 1
            # little-endian reinterpretation (bytes reversed)
            try:
                b = priv_int.to_bytes((priv_int.bit_length() + 7) // 8 or 1, "big")
                priv_le = int.from_bytes(b[::-1], "big")
                if _addr_from_priv(priv_le % SECP_N, compressed=compressed) == addr:
                    crypto_weird["match_priv_le"] += 1
            except Exception:
                pass
            # bit-reversal in fixed 256-bit lane (редкая ошибка, но проверяем)
            try:
                b256 = priv_int.to_bytes(32, "big")
                bits = int.from_bytes(b256, "big")
                rb = int("{:0256b}".format(bits)[::-1], 2)
                if _addr_from_priv(rb % SECP_N, compressed=compressed) == addr:
                    crypto_weird["match_priv_revbits"] += 1
            except Exception:
                pass

    segment_stats = Counter(r.get("segment", "N/A") for r in all_results if r.get("segment"))
    segment_dir_stats = Counter(r.get("segment_dir", "N/A") for r in all_results if r.get("segment_dir"))

    # Контекст: сегменты, разбитые на группы в GUI
    segment_to_group: dict[str, int] = {}
    group_sizes: list[int] = []
    seg_defs: list[dict[str, Any]] = []
    if cfg.seg_groups:
        for gi, grp in enumerate(cfg.seg_groups, start=1):
            group_sizes.append(len(grp))
            for line in grp:
                parsed = _parse_seg_line(line)
                if not parsed:
                    continue
                parsed["group"] = gi
                seg_defs.append(parsed)
                segment_to_group[parsed["name"]] = gi

    # Статистика находок "внутри сегмента"
    seg_found_total: Counter = Counter()
    seg_found_unique: dict[str, set[str]] = defaultdict(set)
    seg_best_lcp: dict[str, int] = defaultdict(int)
    seg_best_matches: dict[str, int] = defaultdict(int)
    seg_pcts: dict[str, list[float]] = defaultdict(list)
    for r in all_results:
        seg = r.get("segment")
        addr = r.get("address")
        if not seg or not addr:
            continue
        seg_found_total[seg] += 1
        seg_found_unique[seg].add(addr)
        if target:
            l = _lcp(addr, target)
            m = _matches_by_position(addr, target)
            if l > seg_best_lcp.get(seg, 0):
                seg_best_lcp[seg] = l
            if m > seg_best_matches.get(seg, 0):
                seg_best_matches[seg] = m
        if cfg.puzzle_bits is not None and r.get("puzzle_key_abs"):
            pct = _calc_puzzle_percentage(r["puzzle_key_abs"], cfg.puzzle_bits)
            if pct is not None:
                seg_pcts[seg].append(pct)

    # Рекомендации по сегментам: скоринг по плотности (unique / size) + "сигнал" близости к target
    seg_reco: list[dict[str, Any]] = []
    for sd in seg_defs:
        name = sd["name"]
        a = int(sd["start"])
        b = int(sd["end"])
        size = abs(b - a) + 1
        uniq = len(seg_found_unique.get(name, set()))
        total = int(seg_found_total.get(name, 0))
        density = uniq / size if size > 0 else 0.0
        lcpv = seg_best_lcp.get(name, 0)
        matchv = seg_best_matches.get(name, 0)
        pcts = seg_pcts.get(name, [])
        # score: плотность * (1 + бонус за близость к target)
        bonus = 1.0
        if target:
            bonus += 0.20 * float(lcpv) + 0.05 * float(matchv)
        score = density * bonus
        seg_reco.append(
            {
                "name": name,
                "group": sd.get("group"),
                "mode": sd.get("mode"),
                "direction": sd.get("direction"),
                "start": a,
                "end": b,
                "size": size,
                "found_total": total,
                "found_unique": uniq,
                "density": density,
                "score": score,
                "best_lcp": lcpv,
                "best_matches": matchv,
                "pct_min": min(pcts) if pcts else None,
                "pct_max": max(pcts) if pcts else None,
                "pct_avg": (sum(pcts) / len(pcts)) if pcts else None,
            }
        )

    # Сортировка: сначала плотность, затем найденные, затем (если target задан) lcp/matches
    seg_reco.sort(
        key=lambda x: (
            x["score"],
            x["density"],
            x["found_unique"],
            x["found_total"],
            x["best_lcp"],
            x["best_matches"],
        ),
        reverse=True,
    )

    seg_overlap = _segment_ranges_overlap_gaps(seg_defs)

    suggestions = _suggest_patterns(
        addresses,
        base_prefix=prefix,
        target_address=target,
        position_chars=position_chars,
        n=cfg.suggest_patterns,
    )

    return {
        "cfg": cfg,
        "files": files,
        "file_stats": file_stats,
        "total_records": len(all_results),
        "total_addresses": len(addresses),
        "unique_addresses": len(uniq_addresses),
        "dup_count": dup_count,
        "dup_top": dup_top,
        "addr_files": addr_files,
        "invalid_chars": invalid_chars,
        "length_dist": length_dist,
        "leading_ones": leading_ones,
        "prefix": prefix,
        "prefix_matches": prefix_matches,
        "position_chars": position_chars,
        "entropies": entropies,
        "kl_positions": kl_positions,
        "cond_by_prefix": cond_by_prefix,
        "target": target,
        "closest": closest[:10] if closest else [],
        "pct_list": pct_list,
        "puzzle_integrity": puzzle_integrity,
        "crypto_verify": crypto_verify,
        "wif_integrity": wif_integrity,
        "key_provenance": key_provenance,
        "crypto_weird": crypto_weird,
        "h160_stats": h160_stats,
        "bit_stats": bit_stats,
        "delta_stats": delta_stats,
        "pattern_bandit": pattern_bandit,
        "segment_stats": segment_stats,
        "segment_dir_stats": segment_dir_stats,
        "segment_to_group": segment_to_group,
        "seg_group_sizes": group_sizes,
        "seg_defs": seg_defs,
        "seg_reco": seg_reco,
        "seg_overlap": seg_overlap,
        "suggestions": suggestions,
    }


def render_report(analysis: dict[str, Any]) -> str:
    cfg: AnalyzerConfig = analysis["cfg"]
    lines: list[str] = []

    def hdr(title: str) -> None:
        lines.append("=" * 110)
        lines.append(title)
        lines.append("=" * 110)

    hdr("ANALYZER: Объединённый файл VanitySearch")
    lines.append(f"Input file: {cfg.input_file}")
    lines.append(f"Target:     {analysis['target'] or '(не задан)'}")
    lines.append(f"Prefix:     {analysis['prefix'] or '(не задан)'}")
    lines.append("")

    # Интегритет PuzzleKeyAbs: математика/конвертация
    pi = analysis.get("puzzle_integrity") or {}
    if pi and pi.get("checked", 0) > 0:
        hdr("PUZZLEKEYABS: ПРОВЕРКА МАТЕМАТИКИ/КОНВЕРСИЙ")
        lines.append(f"checked={pi['checked']}")
        lines.append(f"in_range(bits):         {pi['ok_in_range']}/{pi['checked']}")
        lines.append(f"PuzzleStart+Pos0==Abs:  {pi['ok_start_pos0_abs']}/{pi['checked']}")
        lines.append(f"HEX==DEC:               {pi['ok_hex_dec']}/{pi['checked']}")
        if pi.get("bad_samples"):
            lines.append("Аномалии (первые):")
            for s in pi["bad_samples"]:
                lines.append(f"  - file={s.get('file')} seg={s.get('seg')} addr={s.get('addr')}")
                lines.append(f"    PuzzleBits={s.get('pbits')}  PuzzleStart={s.get('pstart')}  Pos0={s.get('pos0')}")
                lines.append(f"    AbsDec={s.get('ka_dec')}  AbsHex={s.get('ka_hex')}")
        lines.append("")

    cv = analysis.get("crypto_verify") or {}
    if cv and cv.get("checked", 0) > 0:
        hdr("КРИПТО-ПРОВЕРКА: КАКОЙ КЛЮЧ ДАЁТ PubAddress")
        lines.append(f"checked={cv['checked']} (по cfg.verify_crypto)")
        lines.append(f"match_priv_hex:   {cv['match_priv']}/{cv['checked']}")
        lines.append(f"match_puzzle_abs: {cv['match_puzzle']}/{cv['checked']}")
        lines.append(f"match_seg_key:    {cv['match_seg']}/{cv['checked']}")
        lines.append(f"mismatch:         {cv['mismatch']}/{cv['checked']}")
        if cv.get("samples"):
            lines.append("Примеры mismatch (первые):")
            for s in cv["samples"]:
                lines.append(f"  - addr={s.get('addr')}")
                lines.append(f"    priv={s.get('priv_hex')}")
                lines.append(f"    puzzle_hex={s.get('puzzle_hex')} puzzle_dec={s.get('puzzle_dec')}")
                lines.append(f"    seg_dec={s.get('seg_dec')}")
        lines.append("")

    wi = analysis.get("wif_integrity") or {}
    if wi and wi.get("checked", 0) > 0:
        hdr("WIF: ПРОВЕРКА ДЕКОДА/СООТВЕТСТВИЯ priv_hex")
        lines.append(f"checked={wi['checked']}")
        lines.append(f"decode_ok:     {wi['ok_decode']}/{wi['checked']}")
        lines.append(f"priv_match:    {wi['ok_priv_match']}/{wi['checked']} (сравнение по mod n)")
        lines.append(f"flag_present:  {wi['ok_compression_flag']}/{wi['checked']}")
        lines.append(f"bad:           {wi['bad']}/{wi['checked']}")
        if wi.get("compressed", 0) or wi.get("uncompressed", 0):
            lines.append(f"compressed:    {wi.get('compressed',0)}   uncompressed: {wi.get('uncompressed',0)}")
            if wi.get("compressed", 0) > 0 and wi.get("uncompressed", 0) > 0:
                lines.append("⚠ Внимание: смешаны compressed/uncompressed — это может ломать интерпретацию адресов и метрик.")
        lines.append("")

    # 1) Hash160 distance to target
    hs = analysis.get("h160_stats") or {}
    if hs and hs.get("target_ok"):
        hdr("HASH160 DISTANCE (P2PKH): метрика ближе к настоящей цели, чем LCP Base58")
        lines.append(f"decoded_ok: {hs.get('ok',0)}/{hs.get('checked',0)}")
        if hs.get("avg_hamming") is not None:
            lines.append(f"avg_hamming_bits: {hs['avg_hamming']:.2f} / 160")
        if hs.get("best"):
            lines.append("Топ-10 по минимальному Hamming(hash160) до target:")
            for a, d in hs["best"]:
                lines.append(f"  - d={d:3d}  {a}")
        # per-byte heat
        pb = hs.get("per_byte") or []
        if pb:
            hot = sorted([(i, v) for i, v in enumerate(pb)], key=lambda x: x[1], reverse=True)[:6]
            lines.append("Самые проблемные байты (в среднем больше бит отличается): " + ", ".join([f"b{i}={v:.2f}" for i, v in hot]))
        lines.append("Рекомендация: если LCP стоит, оптимизируйте по hash160-distance (выбирайте паттерны/сегменты, где distance падает).")
        lines.append("")

    # 2) Битовая статистика segKey
    bs = analysis.get("bit_stats") or {}
    if bs and bs.get("count", 0) > 0:
        hdr("BIT-ANALYSIS (segKey): энтропия битов и 'куда режем сегменты'")
        lines.append(f"segKey samples: {bs['count']}  bits_analyzed: {bs.get('bits',0)}")
        lines.append("Топ битов с минимальной энтропией (сильный сигнал концентрации):")
        for r in (bs.get('global') or [])[:12]:
            lines.append(f"  - bit={r['bit']:3d}  p1={r['p1']*100:6.2f}%  H={r['H']:.3f}")
        byc = bs.get("by_class") or {}
        if byc:
            lines.append("По классам (endomorphism/negation):")
            for cls, rows in byc.items():
                lines.append(f"  {cls}:")
                for r in rows[:5]:
                    lines.append(f"    - bit={r['bit']:3d} p1={r['p1']*100:6.2f}% H={r['H']:.3f}")
        lines.append("Рекомендация: дробите 'горячие' сегменты пополам/на 4 по тем битам, где p1 сильно смещён от 50%.")
        lines.append("")

    # 3) ΔsegKey / stride
    ds = analysis.get("delta_stats") or {}
    if ds and ds.get("count", 0) > 0:
        hdr("ΔsegKey (stride/gcd): поиск скрытого шага/сетки")
        lines.append(f"deltas={ds['count']}  gcd={ds.get('gcd')}")
        lines.append("Топ-10 самых частых Δ:")
        for d, cnt in ds.get("top_deltas") or []:
            lines.append(f"  - Δ={d}  count={cnt}")
        lines.append("Рекомендация: если gcd >> 1, проверяйте neighbor-сегменты вокруг лучших segKey с шагом gcd (±k*gcd).")
        lines.append("")

    # 4) Bandit ranking for patterns
    pb = analysis.get("pattern_bandit") or {}
    if pb and pb.get("evaluated", 0) > 0:
        hdr("PATTERN-BANDIT: ранжирование паттернов по награде (LCP + hash160 - штраф за ширину)")
        lines.append(f"evaluated={pb['evaluated']} (top-20 ниже)")
        for r in (pb.get("top") or [])[:12]:
            ah = r["avg_hamming"]
            ahs = f"{ah:.1f}" if ah is not None else "N/A"
            lines.append(f"  - score={r['score']:.2f}  cov={r['cov']*100:5.1f}%  bestLCP={r['best_lcp']:2d}  avgHam={ahs}  {r['pattern']}")
        lines.append("Рекомендация: стартуйте с top-3, затем обновляйте по новым out (bandit-подход).")
        lines.append("")

    kp = analysis.get("key_provenance") or {}
    if kp and kp.get("total", 0) > 0:
        hdr("ПРОИСХОЖДЕНИЕ ПРИВАТНИКА (segKey -> Priv): endomorphism/negation inference")
        lines.append("Классы: id, neg, lam, lam_neg, lam2, lam2_neg, unknown (сравнение по mod n).")
        by = kp.get("by_class") or {}
        total = kp.get("total", 0)
        # печатаем в стабильном порядке
        order = ["id", "neg", "lam", "lam_neg", "lam2", "lam2_neg", "unknown"]
        for k in order:
            if k in by:
                lines.append(f"  - {k}: {by[k]}/{total}")
        if kp.get("examples"):
            lines.append("Примеры (первые):")
            for e in kp["examples"]:
                lines.append(f"  - {e['class']}: addr={e['addr']}")
                lines.append(f"    seg_dec={e['seg_dec']}")
                lines.append(f"    priv_hex={e['priv_hex']}  priv_mod_n={e['priv_mod_n_hex']}")
        lines.append("")

    cw = analysis.get("crypto_weird") or {}
    if cw and cw.get("checked", 0) > 0:
        hdr("HACKER-TESTS: ENDIANNESS / BIT-MIRROR (sanity)")
        lines.append(f"checked={cw['checked']}")
        lines.append(f"match_priv_le(byteswap): {cw['match_priv_le']}/{cw['checked']}")
        lines.append(f"match_priv_revbits(256): {cw['match_priv_revbits']}/{cw['checked']}")
        lines.append("Ожидаемо должно быть 0. Если не 0 — значит где-то путаница endian/bit-order.")
        lines.append("")

    # Контекст запуска (GUI): паттерны и сегменты-группы
    if cfg.search_patterns or cfg.seg_groups:
        hdr("КОНТЕКСТ ЗАПУСКА (из текущих полей GUI)")
        if cfg.search_patterns:
            lines.append("Паттерны (prefix/suffix + extra -i):")
            for p in cfg.search_patterns[:50]:
                lines.append(f"  - {p}")
            if len(cfg.search_patterns) > 50:
                lines.append(f"  ... и ещё {len(cfg.search_patterns) - 50}")
        else:
            lines.append("Паттерны: (не переданы)")
        lines.append("")
        if cfg.seg_groups:
            lines.append(f"Сегменты: групп={len(cfg.seg_groups)}")
            sizes = analysis.get("seg_group_sizes", [])
            if sizes:
                lines.append("Размеры групп (кол-во сегментов): " + ", ".join(str(x) for x in sizes))
            # кратко: первые имена сегментов по группам
            for gi, grp in enumerate(cfg.seg_groups, start=1):
                names: list[str] = []
                for line in grp:
                    nm = _parse_seg_line_name(line)
                    if nm:
                        names.append(nm)
                if names:
                    shown = ", ".join(names[:10])
                    tail = f" (+{len(names) - 10})" if len(names) > 10 else ""
                    lines.append(f"  - Group {gi}: {shown}{tail}")
        else:
            lines.append("Сегменты: (не переданы)")
        lines.append("")

    hdr("ОБЩАЯ СТАТИСТИКА")
    lines.append(f"Записей (блоков):          {analysis['total_records']}")
    lines.append(f"Адресов (из блоков):       {analysis['total_addresses']}")
    lines.append(f"Уникальных адресов:        {analysis['unique_addresses']}")
    lines.append(f"Дубликатов (повторы):      {analysis['dup_count']}")
    if analysis["dup_top"]:
        lines.append("Топ повторяющихся адресов:")
        for a in analysis["dup_top"]:
            lines.append(f"  - {a}")
    lines.append("")

    # Дубликаты: где именно повторяются
    if analysis["dup_count"] > 0:
        hdr("ДУБЛИКАТЫ (по файлам)")
        addr_files = analysis.get("addr_files", {})
        multi = [(a, sorted(list(fs))) for a, fs in addr_files.items() if len(fs) >= 2]
        multi.sort(key=lambda x: len(x[1]), reverse=True)
        if multi:
            lines.append("Адреса, встречающиеся в нескольких out-файлах (топ-15):")
            for a, fs in multi[:15]:
                lines.append(f"  - {a}  files={len(fs)}  ({', '.join(fs[:6])}{'...' if len(fs) > 6 else ''})")
        else:
            lines.append("Дубликаты есть, но в рамках одного файла (перезапись/повторы внутри out).")
        lines.append("")

    lines.append("Статистика по файлам (топ-20):")
    for fn, cnt in sorted(analysis["file_stats"].items())[:20]:
        lines.append(f"  - {fn}: {cnt}")
    if len(analysis["file_stats"]) > 20:
        lines.append(f"  ... и ещё {len(analysis['file_stats']) - 20}")
    lines.append("")

    hdr("ВАЛИДАЦИЯ / САНИТИЧЕКИ")
    inv: Counter = analysis["invalid_chars"]
    if inv:
        lines.append("Обнаружены символы вне Base58 алфавита (подозрительно):")
        for ch, cnt in inv.most_common():
            lines.append(f"  - {repr(ch)}: {cnt}")
    else:
        lines.append("Все адреса состоят из Base58 символов (OK).")
    lines.append("Распределение длин адресов:")
    for ln, cnt in analysis["length_dist"].most_common(10):
        lines.append(f"  - len={ln}: {cnt}")
    lines.append("Распределение ведущих '1' (косвенно отражает leading-zero bytes):")
    for k, cnt in analysis["leading_ones"].most_common(10):
        lines.append(f"  - leading_ones={k}: {cnt}")
    lines.append("")

    hdr("ПРЕФИКС / БЛИЗОСТЬ К ЦЕЛИ")
    prefix = analysis["prefix"]
    pm = analysis["prefix_matches"]
    if prefix:
        lines.append(f"Совпадений по префиксу '{prefix}': {len(pm)}")
        for a in pm[:10]:
            lines.append(f"  - {a}")
        if len(pm) > 10:
            lines.append(f"  ... и ещё {len(pm) - 10}")
    else:
        lines.append("Префикс не задан — префикс-матчи не считались.")
    lines.append("")

    if analysis["target"]:
        lines.append("Топ-10 по близости к target (сначала LCP, затем совпадения по позициям):")
        for a, lcpv, matches in analysis["closest"]:
            lines.append(f"  - LCP={lcpv:2d}, matches={matches:2d}: {a}")
    else:
        lines.append("Target не задан — метрики близости (LCP/matches) не считались.")
    lines.append("")

    hdr("ПОЗИЦИОННЫЙ АНАЛИЗ (ЭНТРОПИЯ)")
    lines.append("Чем ниже энтропия позиции, тем сильнее 'сжалось' пространство находок на этой позиции.")
    for i, e, top in analysis["entropies"][:20]:
        lines.append(f"  - pos={i:2d}: H={e:0.3f} bits, top='{top}'")
    if len(analysis["entropies"]) > 20:
        lines.append(f"  ... всего позиций с данными: {len(analysis['entropies'])}")
    lines.append("")

    hdr("ИНФОРМАТИВНОСТЬ ПОЗИЦИЙ (KL(P||Uniform Base58))")
    lines.append("Высокий KL = позиция сильнее всего отклоняется от равномерного Base58 => хороший кандидат для фиксации/паттерна.")
    for i, kl, top, top_p in analysis.get("kl_positions", [])[:12]:
        lines.append(f"  - pos={i:2d}: KL={kl:0.3f} bits, top='{top}' p={top_p*100:0.2f}%")
    lines.append("")

    # Условные энтропии и ожидаемый выигрыш паттернов X/XY/XYZ
    if prefix:
        hdr("УСЛОВНАЯ ЭНТРОПИЯ И 'ВЫИГРЫШ' ОТ ПАТТЕРНОВ (prefix -> X / XY / XYZ)")
        lines.append("H — энтропия распределения следующих n символов; eff=2^H — эффективное число кандидатов.")
        lines.append("bits=-log2(p) для конкретного кандидата: чем меньше bits, тем чаще встречается этот вариант в находках.")
        cond_by_prefix = analysis.get("cond_by_prefix", {}) or {}
        for pfx, d in cond_by_prefix.items():
            lines.append(f"prefix='{pfx}'")
            for key in ("n1", "n2", "n3"):
                dn = d.get(key) or {}
                n = dn.get("n")
                total = dn.get("total", 0)
                H = dn.get("H", 0.0)
                eff = dn.get("eff", 0.0)
                lines.append(f"  n={n}: total={total}  H={H:0.3f} bits  eff≈{eff:0.2f}")
                for t in dn.get("top", [])[:10]:
                    gram = t["gram"]
                    p = t["p"]
                    bits = t["bits"]
                    lines.append(f"    - {pfx}{gram}*   p={p*100:0.2f}%   bits={bits:0.2f}")
            lines.append("")

    if prefix:
        pos = len(prefix)
        pc = analysis["position_chars"].get(pos)
        if pc:
            lines.append(f"Частоты символов на позиции {pos} (сразу после префикса):")
            total = sum(pc.values())
            for ch, cnt in pc.most_common(12):
                p = (cnt / total * 100.0) if total else 0.0
                lines.append(f"  - '{ch}': {cnt} ({p:0.2f}%)")
            lines.append("")

    hdr("PUZZLE-КООРДИНАТА (если есть PuzzleKeyAbs)")
    pct_list = analysis["pct_list"]
    if pct_list:
        vals = [p for _a, p, _s in pct_list]
        avg = sum(vals) / len(vals)
        lines.append(f"bits={analysis['cfg'].puzzle_bits}")
        lines.append(f"Записей с позицией: {len(vals)}")
        lines.append(f"min={min(vals):0.6f}%  max={max(vals):0.6f}%  avg={avg:0.6f}%")
        lines.append("Топ-5 самых 'нижних' и 'верхних' позиций:")
        for a, p, seg in pct_list[:5]:
            lines.append(f"  - LOW  {p:0.6f}%  seg={seg}  addr={a}")
        for a, p, seg in pct_list[-5:]:
            lines.append(f"  - HIGH {p:0.6f}%  seg={seg}  addr={a}")

        # Конкретные рекомендации по диапазону: окно вокруг avg и окно min..max
        bits = analysis["cfg"].puzzle_bits
        if isinstance(bits, int):
            lines.append("")
            lines.append("Рекомендации по диапазону (готовые abs-границы):")
            lo = min(vals)
            hi = max(vals)
            # окно вокруг среднего (±0.30%)
            w = 0.30
            a1 = avg - w
            b1 = avg + w
            abs_a1 = _abs_from_puzzle_pct(a1, bits)
            abs_b1 = _abs_from_puzzle_pct(b1, bits)
            abs_lo = _abs_from_puzzle_pct(lo, bits)
            abs_hi = _abs_from_puzzle_pct(hi, bits)
            lines.append(f"  - window_avg:  {a1:0.4f}% .. {b1:0.4f}%  => abs {abs_a1} .. {abs_b1}")
            lines.append(f"  - window_data: {lo:0.4f}% .. {hi:0.4f}%  => abs {abs_lo} .. {abs_hi}")
            lines.append("  - быстрый ход: запустить 8 UP + 8 DOWN сегментов в window_avg (как отдельную группу)")
            lines.append("")
            lines.append("Готовые сегменты для window_avg (8 UP + 8 DOWN):")
            bounds = _split_range(min(abs_a1, abs_b1), max(abs_a1, abs_b1), 8)
            lines.append("# --- window_avg UP ---")
            for i, (x1, x2) in enumerate(bounds, start=1):
                lines.append(f"abs {x1} {x2} up winAvg_{i:02d} 5")
            lines.append("# --- window_avg DOWN (mirror) ---")
            for i, (x1, x2) in enumerate(bounds, start=1):
                lines.append(f"abs {x2} {x1} down winAvgD_{i:02d} 5")
            lines.append("")
            lines.append("Те же сегменты в HEX (альтернатива, формат key):")
            lines.append("# --- window_avg UP (HEX) ---")
            for i, (x1, x2) in enumerate(bounds, start=1):
                lines.append(f"key {_hx(x1)} {_hx(x2)} up winAvgH_{i:02d} 5")
            lines.append("# --- window_avg DOWN (HEX mirror) ---")
            for i, (x1, x2) in enumerate(bounds, start=1):
                lines.append(f"key {_hx(x2)} {_hx(x1)} down winAvgHD_{i:02d} 5")

            # Бит-оптимизированные разрезы для window_avg
            bs = analysis.get("bit_stats") or {}
            global_bits = bs.get("global") or []
            w_lo = min(abs_a1, abs_b1)
            w_hi = max(abs_a1, abs_b1)
            w_size = w_hi - w_lo + 1
            cand: list[tuple[int, float, float, int]] = []  # (bit, H, p1, seg_count_est)
            for r in global_bits:
                b = int(r.get("bit"))
                H = float(r.get("H"))
                p1 = float(r.get("p1"))
                if H <= 0.0:
                    continue
                # оценим сколько будет кусков по границам 2^b
                step = 1 << b
                if step <= 0:
                    continue
                seg_est = int(w_size // step) + 1
                # хотим мало сегментов, но не 1
                if 2 <= seg_est <= 24:
                    cand.append((b, H, p1, seg_est))
            # предпочитаем низкую энтропию (сильный перекос) и малое число кусков
            cand.sort(key=lambda x: (x[1], x[3]))
            if cand:
                lines.append("")
                lines.append("BIT-OPTIMIZED SEGMENTS (window_avg): разрез по границам 2^bit для 'информативных' битов segKey")
                lines.append("Формат: HEX key 0x.. (рекомендуется), + DOWN mirror. Эти сегменты удобно запускать отдельной группой.")
                # возьмём до 3 лучших битов
                for (b, H, p1, seg_est) in cand[:3]:
                    lines.append(f"# bit={b}  H={H:.3f}  p1={p1*100:.2f}%  expected_chunks~{seg_est}")
                    chunks = _split_by_bit_boundaries(w_lo, w_hi, b, max_segments=64)
                    # UP
                    for j, (a, z) in enumerate(chunks, start=1):
                        lines.append(f"key {_hx(a)} {_hx(z)} up winBit{b}_{j:02d} 6")
                    # DOWN mirror
                    for j, (a, z) in enumerate(chunks, start=1):
                        lines.append(f"key {_hx(z)} {_hx(a)} down winBit{b}D_{j:02d} 6")
    else:
        lines.append("PuzzleKeyAbs не найден в данных (или puzzle_bits отключён).")
    lines.append("")

    hdr("СЕГМЕНТЫ")
    if analysis["segment_stats"]:
        lines.append("Находки по сегментам (топ-20):")
        seg2g = analysis.get("segment_to_group", {}) or {}
        for seg, cnt in analysis["segment_stats"].most_common(20):
            gi = seg2g.get(seg)
            gtxt = f" (group {gi})" if gi else ""
            lines.append(f"  - {seg}: {cnt}{gtxt}")
    else:
        lines.append("Поле Segment отсутствует в результатах.")
    lines.append("")
    if analysis["segment_dir_stats"]:
        lines.append("Направления сегментов (SegmentDir):")
        for d, cnt in analysis["segment_dir_stats"].most_common():
            lines.append(f"  - {d}: {cnt}")
        lines.append("")

    # Перекрытия/дыры в введённых сегментах
    seg_ov = analysis.get("seg_overlap", {}) or {}
    if seg_ov.get("ranges", 0) > 0:
        hdr("ПЕРЕКРЫТИЯ / ДЫРЫ МЕЖДУ СЕГМЕНТАМИ (по введённому seg)")
        lines.append(
            f"segments={seg_ov['ranges']}  total_size={seg_ov['total_size']}  union_size={seg_ov['union_size']}  "
            f"overlap_total={seg_ov['overlap_total']}  gap_total={seg_ov['gap_total']}"
        )
        if seg_ov.get("overlaps"):
            lines.append("Топ перекрытий:")
            for ov in seg_ov["overlaps"]:
                a = ov["a"]
                b = ov["b"]
                lines.append(
                    f"  - ov={ov['size']}  {a['name']} (g{a.get('group')}) <-> {b['name']} (g{b.get('group')})  "
                    f"[{ov['ov_lo']}..{ov['ov_hi']}]"
                )
        if seg_ov.get("gaps"):
            lines.append("Топ дыр:")
            for gp in seg_ov["gaps"]:
                l = gp["left"]
                r = gp["right"]
                lines.append(
                    f"  - gap={gp['size']}  {l['name']} (g{l.get('group')}) -> {r['name']} (g{r.get('group')})  "
                    f"[{gp['gap_lo']}..{gp['gap_hi']}]"
                )
        lines.append("")

    # Сегментные рекомендации: ранжирование + генерация новых сегментов
    seg_reco = analysis.get("seg_reco", []) or []
    if seg_reco:
        hdr("РЕКОМЕНДАЦИИ ПО СЕГМЕНТАМ (конкретика)")
        lines.append("Скоринг: score=density*(1+0.20*bestLCP+0.05*bestMatches), где density=unique_found/size.")
        lines.append("Топ-10 'самых продуктивных' сегментов из введённых:")
        for s in seg_reco[:10]:
            gi = s.get("group")
            gtxt = f"group {gi}" if gi else "group ?"
            extra = ""
            if s.get("pct_avg") is not None:
                extra = f" pct_avg={s['pct_avg']:.4f}% [{s['pct_min']:.4f}..{s['pct_max']:.4f}]"
            if analysis.get("target"):
                extra += f" bestLCP={s.get('best_lcp',0)} bestMatch={s.get('best_matches',0)}"
            lines.append(
                f"  - {s['name']} ({gtxt}, {s['direction']}) "
                f"uniq={s['found_unique']} total={s['found_total']} size={s['size']} "
                f"score={s['score']:.3e} density={s['density']:.3e}{extra}"
            )
        lines.append("")

        # Генерация: "сузить вокруг наблюдаемой зоны" для лучших сегментов
        # Механика: берем сегмент и делим на 3 под-сегмента, чтобы увеличить плотность/сигнал.
        lines.append("Новые сегменты (вставьте в Segments; отдельной группой):")
        lines.append("# --- Suggested refined segments (AUTO) ---")
        take = seg_reco[:4]
        for s in take:
            name = s["name"]
            a = int(s["start"])
            b = int(s["end"])
            direction = s["direction"]
            lo = min(a, b)
            hi = max(a, b)
            size = hi - lo + 1
            if size < 3:
                continue
            # делим на 3
            one = size // 3
            m1 = lo + one
            m2 = lo + 2 * one
            # Для down оставляем direction=down, но порядок start/end в файле не нормализуем — сохраняем стиль.
            # Сегменты под разрез: low/mid/high
            base = f"{name}_ref"
            if direction == "up":
                lines.append(f"abs {lo} {m1} up {base}1 5")
                lines.append(f"abs {m1+1} {m2} up {base}2 5")
                lines.append(f"abs {m2+1} {hi} up {base}3 5")
            else:
                # down: start > end логичнее, но в abs допускаем любой порядок, VanitySearch читает границы.
                lines.append(f"abs {hi} {m2+1} down {base}1 5")
                lines.append(f"abs {m2} {m1+1} down {base}2 5")
                lines.append(f"abs {m1} {lo} down {base}3 5")
        lines.append("# --- End suggested segments ---")
        lines.append("")

        lines.append("Когда имеет смысл менять диапазон целиком:")
        lines.append("  - если в лучших сегментах bestLCP не растёт между итерациями, а KL по позициям не усиливается — вы 'режете' не там.")
        lines.append("  - если Puzzle-координата (pct_avg) у находок стабильно смещается к краю текущего окна — расширяйте окно в сторону смещения.")
        lines.append("  - если плотность находок примерно одинакова во всех сегментах — вероятно, сегменты слишком широкие: дробите и добавляйте down-зеркало.")
        lines.append("")

        # Бит-оптимизированные сегменты вокруг лучших сегментов (локально, дешевле чем резать весь window_avg)
        bs = analysis.get("bit_stats") or {}
        global_bits = bs.get("global") or []
        if global_bits:
            hdr("BIT-OPTIMIZED SEGMENTS (TOP SEGMENTS): локальное дробление лучших сегментов")
            lines.append("Идея: берём топ сегменты по score и режем их по границам 2^bit (бит выбираем по BIT-ANALYSIS).")
            lines.append("Формат: HEX key 0x.. + DOWN mirror. Вставляйте отдельной группой.")
            lines.append("")
            topN = seg_reco[:3]
            for s in topN:
                name = s["name"]
                lo = min(int(s["start"]), int(s["end"]))
                hi = max(int(s["start"]), int(s["end"]))
                picks = _pick_bits_for_range(lo, hi, global_bits=global_bits, want_min=2, want_max=12, take=2)
                lines.append(f"# Segment={name}  range=[{_hx(lo)}..{_hx(hi)}]  size={hi-lo+1}  score={s['score']:.3e}")
                if not picks:
                    lines.append("# (нет подходящих битов под диапазон: либо слишком широкий, либо слишком узкий)")
                    continue
                for (b, H, p1, seg_est) in picks:
                    lines.append(f"# bit={b}  H={H:.3f}  p1={p1*100:.2f}%  expected_chunks~{seg_est}")
                    chunks = _split_by_bit_boundaries(lo, hi, b, max_segments=64)
                    for j, (a, z) in enumerate(chunks, start=1):
                        lines.append(f"key {_hx(a)} {_hx(z)} up {name}_b{b}_{j:02d} 6")
                    for j, (a, z) in enumerate(chunks, start=1):
                        lines.append(f"key {_hx(z)} {_hx(a)} down {name}_b{b}D_{j:02d} 6")
                lines.append("")

    hdr("ПАТТЕРНЫ ДЛЯ СЛЕДУЮЩЕГО ЗАПУСКА (максимально информативные)")
    sugg = analysis["suggestions"]
    if sugg:
        lines.append("Сгенерированные паттерны (для -i patterns.txt):")
        for p in sugg:
            lines.append(f"  - {p}")
    else:
        lines.append("Не удалось сгенерировать паттерны (нет адресов или нет префикса).")
    lines.append("")

    # Pattern packs: target-pressure + signal-exploration
    hdr("PATTERN PACKS (готовые наборы для -i / Extra patterns)")
    target = analysis.get("target") or ""
    cond_by_prefix = analysis.get("cond_by_prefix") or {}
    base_prefix = analysis.get("prefix") or ""
    focus_prefix = "1PWo3JeB"  # стабильный базовый префикс для статистики (шире, чем 1PWo3JeB9)

    target_pack = _build_target_pattern_pack(target, base_prefix=base_prefix, max_items=32)
    signal_pack_long = _build_signal_pattern_pack_long_first(cond_by_prefix, focus_prefix=focus_prefix, max_items=64)
    signal_pack_hi = _build_signal_pattern_pack_high_prob(cond_by_prefix, focus_prefix=focus_prefix, p_min=0.05, max_items=64)

    if target_pack:
        lines.append("TARGET PACK (давим в точный target слева направо):")
        lines.append("# --- copy/paste begin (TARGET PACK) ---")
        lines.extend(target_pack)
        lines.append("# --- copy/paste end ---")
    else:
        lines.append("TARGET PACK: (target не задан)")
    lines.append("")

    if signal_pack_hi:
        lines.append(f"SIGNAL PACK (HIGH-PROB, p>=5%, focus_prefix='{focus_prefix}'):")
        lines.append("# --- copy/paste begin (SIGNAL PACK HIGH-PROB) ---")
        lines.extend(signal_pack_hi)
        lines.append("# --- copy/paste end ---")
        lines.append("")
    else:
        lines.append(f"SIGNAL PACK (HIGH-PROB): (нет кандидатов с p>=5% для focus_prefix='{focus_prefix}')")
        lines.append("")

    if signal_pack_long:
        lines.append(f"SIGNAL PACK (LONG-GRAMS-FIRST, focus_prefix='{focus_prefix}'):")
        lines.append("# --- copy/paste begin (SIGNAL PACK LONG) ---")
        lines.extend(signal_pack_long)
        lines.append("# --- copy/paste end ---")
        lines.append("")
        lines.append("Режим запуска (рекомендация):")
        lines.append("  - сначала SIGNAL HIGH-PROB на широких сегментах (быстро собрать 'жирный' сигнал)")
        lines.append("  - затем SIGNAL LONG-GRAMS-FIRST (углубить статистику и уточнить ветвления)")
        lines.append("  - затем TARGET PACK на window_avg сегментах (дожимать LCP к target)")
    else:
        lines.append(f"SIGNAL PACK (LONG-GRAMS-FIRST): (недостаточно данных для focus_prefix='{focus_prefix}')")
    lines.append("")

    hdr("РЕКОМЕНДАЦИИ (cryptographer/hacker/researcher)")
    rec: list[str] = []
    if analysis["total_addresses"] == 0:
        rec.append("Нет адресов в out-файлах — проверьте маску glob и папку, а также что VanitySearch пишет out-файл.")
    else:
        if prefix:
            rec.append(
                "Оптимальная стратегия: фиксируйте слева направо. Сначала префикс, затем следующий символ после префикса "
                "(prefix + X*), затем углубляйтесь дальше (prefix + XY*)."
            )
            rec.append(
                "Используйте мультипаттерн через -i: несколько вариантов prefix+X* (по топ-частотам), это даёт лучший "
                "trade-off между шириной и сигналом."
            )
        if analysis["target"]:
            rec.append(
                "Следите за ростом LCP в итерациях. Если LCP не растёт, вы сужаете пространство не тем разрезом: "
                "меняйте сегменты/направление (UP/DOWN) или перестраивайте паттерн."
            )
        kp = analysis.get("key_provenance") or {}
        if kp and kp.get("total", 0) > 0:
            by = kp.get("by_class") or {}
            # если доминирует endomorphism, подсказываем, что segKey — именно то, что надо сегментировать
            lam_total = int(by.get("lam", 0)) + int(by.get("lam_neg", 0)) + int(by.get("lam2", 0)) + int(by.get("lam2_neg", 0))
            if lam_total > 0 and lam_total >= int(by.get("id", 0)):
                rec.append(
                    "По key-provenance видно, что часто используется endomorphism/negation. "
                    "Важно: сегменты формируйте по segKey (ключ ДО endo/sym), а не по печатаемому Priv (HEX). "
                    "Это снимает 'путаницу' и делает сегментацию корректной."
                )
        ent = analysis["entropies"]
        if ent:
            low = sorted(ent, key=lambda x: x[1])[:5]
            rec.append("Самые 'сжатые' позиции (низкая энтропия) — кандидаты для фиксации в маске:")
            rec.extend([f"  - pos={i}: H={e:0.3f} (top='{t}')" for i, e, t in low])
        if analysis["pct_list"]:
            vals = [p for _a, p, _s in analysis["pct_list"]]
            avg = sum(vals) / len(vals)
            rec.append(
                f"Puzzle-координата средняя: {avg:0.4f}%. Уплотняйте сегменты вокруг этого процента и отдельно тестируйте "
                "down-сегменты и зеркальные сегменты."
            )
        if analysis["dup_count"] > 0:
            rec.append(
                "Есть дубликаты адресов в out. Это бывает при пересечении сегментов/резюме, но если доля дубликатов растёт, "
                "сегменты перекрываются слишком сильно."
            )
        if analysis["invalid_chars"]:
            rec.append(
                "Есть не-Base58 символы — красный флаг: возможно, out-файл смешан с логом или парсер цепляет лишние строки."
            )
    lines.extend(rec)
    lines.append("")

    return "\n".join(lines) + "\n"


def generate_report(
    *,
    input_file: Path,
    target_address: str = "",
    target_prefix: str = "",
    puzzle_bits: Optional[int] = 71,
    max_records: Optional[int] = None,
    suggest_patterns: int = 24,
    search_patterns: Optional[Sequence[str]] = None,
    seg_groups: Optional[Sequence[Sequence[str]]] = None,
    verify_crypto: int = 10,
) -> str:
    sp = tuple(search_patterns) if search_patterns else ()
    sg = tuple(tuple(g) for g in seg_groups) if seg_groups else ()
    cfg = AnalyzerConfig(
        input_file=input_file,
        target_address=target_address,
        target_prefix=target_prefix,
        puzzle_bits=puzzle_bits,
        max_records=max_records,
        suggest_patterns=suggest_patterns,
        search_patterns=sp,
        seg_groups=sg,
        verify_crypto=verify_crypto,
    )
    analysis = analyze_results(cfg)
    return render_report(analysis)


def main() -> int:
    parser = argparse.ArgumentParser(description="Анализатор объединённого файла результатов VanitySearch")
    parser.add_argument(
        "--input",
        default="merged_out_all.txt",
        help="Путь к объединённому файлу (по умолчанию: merged_out_all.txt)",
    )
    parser.add_argument("--target", default="", help="Целевой адрес (опционально)")
    parser.add_argument("--prefix", default="", help="Целевой префикс (опционально)")
    parser.add_argument("--puzzle-bits", default="71", help="bits для PuzzleKeyAbs (например 71), или 'off'")
    parser.add_argument("--max-records", default="", help="Ограничить число записей (опционально)")
    parser.add_argument("--suggest", default="24", help="Сколько паттернов предложить")
    parser.add_argument("--verify-crypto", default="0", help="Крипто-проверка: 0=off, N=first N, all=all")
    parser.add_argument("--out", default="", help="Сохранить отчёт в файл (опционально)")
    args = parser.parse_args()
    
    input_file = Path(args.input).expanduser().resolve()
    if not input_file.exists():
        print(f"Ошибка: файл не найден: {input_file}", file=sys.stderr)
        print(f"Сначала запустите merge_out_files.py для создания объединённого файла", file=sys.stderr)
        return 1
    
    puzzle_bits: Optional[int]
    if str(args.puzzle_bits).strip().lower() in ("off", "none", "0", ""):
        puzzle_bits = None
    else:
        puzzle_bits = _safe_int(args.puzzle_bits) or 71
    
    vc_s = str(args.verify_crypto).strip().lower()
    verify_crypto: int
    if vc_s in ("all", "-1"):
        verify_crypto = -1
    else:
        verify_crypto = _safe_int(vc_s) or 0
    
    report = generate_report(
        input_file=input_file,
        target_address=str(args.target or "").strip(),
        target_prefix=str(args.prefix or "").strip(),
        puzzle_bits=puzzle_bits,
        max_records=_safe_int(args.max_records) if str(args.max_records).strip() else None,
        suggest_patterns=_safe_int(args.suggest) or 24,
        verify_crypto=verify_crypto,
    )
    
    if args.out:
        Path(args.out).expanduser().write_text(report, encoding="utf-8")
        return 0
    
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


