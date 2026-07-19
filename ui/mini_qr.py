# coding: utf-8
"""
Минимальный QR (Model 2, byte mode, ECC-M) + рендер в RGB-массив.

Достаточно для коротких URL вроде https://worldvaluessurveybot.info.
Без зависимости от пакета qrcode — только Pillow/numpy на вызывающей стороне.
"""

from __future__ import annotations

# ── GF(256) / Reed–Solomon ──────────────────────────────────────────────────

_EXP = [0] * 512
_LOG = [0] * 256


def _init_gf() -> None:
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_init_gf()


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_generator(ec_len: int) -> list[int]:
    g = [1]
    for i in range(ec_len):
        g = _poly_mul(g, [1, _EXP[i]])
    return g


def _poly_mul(p: list[int], q: list[int]) -> list[int]:
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] ^= _gf_mul(a, b)
    return r


def _rs_encode(data: list[int], ec_len: int) -> list[int]:
    gen = _rs_generator(ec_len)
    msg = data + [0] * ec_len
    for i in range(len(data)):
        coef = msg[i]
        if coef:
            for j, g in enumerate(gen):
                msg[i + j] ^= _gf_mul(g, coef)
    return msg[-ec_len:]


# (ec_per_block, group1_blocks, group1_data, group2_blocks, group2_data)
_ECC_M_BLOCKS = {
    1: (10, 1, 16, 0, 0),
    2: (16, 1, 28, 0, 0),
    3: (26, 1, 44, 0, 0),
    4: (18, 2, 32, 0, 0),
    5: (24, 2, 43, 0, 0),
    6: (16, 4, 27, 0, 0),
    7: (18, 4, 31, 0, 0),
    8: (22, 2, 38, 2, 39),
    9: (22, 3, 36, 2, 37),
    10: (26, 4, 43, 1, 44),
}

_ALIGN_POS = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
    7: [6, 22, 38],
    8: [6, 24, 42],
    9: [6, 26, 46],
    10: [6, 28, 50],
}


def _choose_version(payload_len: int) -> int:
    for ver in range(1, 11):
        _ec_n, g1b, g1d, g2b, g2d = _ECC_M_BLOCKS[ver]
        data_cw_count = g1b * g1d + g2b * g2d
        length_bits = 8 if ver <= 9 else 16
        # mode + length + payload + terminator (до 4 бит)
        bits_needed = 4 + length_bits + 8 * payload_len + 4
        if (bits_needed + 7) // 8 <= data_cw_count:
            return ver
    raise ValueError("Текст слишком длинный для QR v1–10 (ECC-M)")


def _bit_buffer() -> list[int]:
    return []


def _append_bits(buf: list[int], value: int, length: int) -> None:
    for i in range(length - 1, -1, -1):
        buf.append((value >> i) & 1)


def _bits_to_codewords(bits: list[int], data_cw: int) -> list[int]:
    # pad with 0000 terminator already in bits; then pad bits to byte, then pad bytes
    while len(bits) % 8:
        bits.append(0)
    codewords = []
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | b
        codewords.append(byte)
    pad = 0xEC
    while len(codewords) < data_cw:
        codewords.append(pad)
        pad = 0x11 if pad == 0xEC else 0xEC
    return codewords[:data_cw]


def _interleave(version: int, data_cw: list[int]) -> list[int]:
    ec_n, g1b, g1d, g2b, g2d = _ECC_M_BLOCKS[version]
    blocks: list[list[int]] = []
    ec_blocks: list[list[int]] = []
    offset = 0
    for _ in range(g1b):
        block = data_cw[offset : offset + g1d]
        offset += g1d
        blocks.append(block)
        ec_blocks.append(_rs_encode(block, ec_n))
    for _ in range(g2b):
        block = data_cw[offset : offset + g2d]
        offset += g2d
        blocks.append(block)
        ec_blocks.append(_rs_encode(block, ec_n))

    result: list[int] = []
    max_data = max(len(b) for b in blocks)
    for i in range(max_data):
        for b in blocks:
            if i < len(b):
                result.append(b[i])
    for i in range(ec_n):
        for b in ec_blocks:
            result.append(b[i])
    return result


def _module_count(version: int) -> int:
    return 21 + 4 * (version - 1)


def _place_finder(modules: list[list[int | None]], x: int, y: int) -> None:
    for dy in range(-1, 8):
        for dx in range(-1, 8):
            xx, yy = x + dx, y + dy
            if 0 <= xx < len(modules) and 0 <= yy < len(modules):
                if dx == -1 or dy == -1 or dx == 7 or dy == 7:
                    modules[yy][xx] = 0
                elif 0 <= dx <= 6 and 0 <= dy <= 6:
                    modules[yy][xx] = 1 if (dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4)) else 0


def _place_alignment(modules: list[list[int | None]], cx: int, cy: int) -> None:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            modules[cy + dy][cx + dx] = 1 if max(abs(dx), abs(dy)) in (0, 2) else 0


def _finder_overlap(n: int, cx: int, cy: int) -> bool:
    """Не ставим alignment поверх finder (углы 0 и n-7)."""
    for fx, fy in ((0, 0), (n - 7, 0), (0, n - 7)):
        if abs(cx - (fx + 3)) <= 4 and abs(cy - (fy + 3)) <= 4:
            return True
    return False


def _build_matrix(version: int, codewords: list[int], mask: int) -> list[list[int]]:
    n = _module_count(version)
    modules: list[list[int | None]] = [[None] * n for _ in range(n)]

    _place_finder(modules, 0, 0)
    _place_finder(modules, n - 7, 0)
    _place_finder(modules, 0, n - 7)

    # timing
    for i in range(8, n - 8):
        if modules[6][i] is None:
            modules[6][i] = 1 if i % 2 == 0 else 0
        if modules[i][6] is None:
            modules[i][6] = 1 if i % 2 == 0 else 0

    # alignment (перезаписывает timing при необходимости)
    positions = _ALIGN_POS[version]
    for r in positions:
        for c in positions:
            if _finder_overlap(n, c, r):
                continue
            _place_alignment(modules, c, r)

    # reserve format info (и ячейку dark module — вернём после)
    for i in range(9):
        if i != 6:
            if modules[8][i] is None:
                modules[8][i] = 0
            if modules[i][8] is None:
                modules[i][8] = 0
    for i in range(8):
        if modules[8][n - 1 - i] is None:
            modules[8][n - 1 - i] = 0
        if modules[n - 1 - i][8] is None:
            modules[n - 1 - i][8] = 0

    # reserve version info for v>=7
    if version >= 7:
        for a in range(6):
            for b in range(3):
                modules[a][n - 11 + b] = 0
                modules[n - 11 + b][a] = 0

    # data bits
    bits: list[int] = []
    for cw in codewords:
        for i in range(7, -1, -1):
            bits.append((cw >> i) & 1)

    directions = -1
    bit_i = 0
    x = n - 1
    while x > 0:
        if x == 6:
            x -= 1
        y_range = range(n - 1, -1, -1) if directions < 0 else range(n)
        for y in y_range:
            for dx in (0, -1):
                xx = x + dx
                if modules[y][xx] is not None:
                    continue
                bit = bits[bit_i] if bit_i < len(bits) else 0
                bit_i += 1
                if _mask_applies(mask, xx, y):
                    bit ^= 1
                modules[y][xx] = bit
        directions *= -1
        x -= 2

    grid = [[int(v or 0) for v in row] for row in modules]
    _draw_format(grid, mask)
    if version >= 7:
        _draw_version(grid, version)
    # dark module (всегда чёрный; не часть format)
    grid[4 * version + 9][8] = 1
    return grid


def _mask_applies(mask: int, x: int, y: int) -> bool:
    if mask == 0:
        return (x + y) % 2 == 0
    if mask == 1:
        return y % 2 == 0
    if mask == 2:
        return x % 3 == 0
    if mask == 3:
        return (x + y) % 3 == 0
    if mask == 4:
        return (y // 2 + x // 3) % 2 == 0
    if mask == 5:
        return (x * y) % 2 + (x * y) % 3 == 0
    if mask == 6:
        return ((x * y) % 2 + (x * y) % 3) % 2 == 0
    return ((x + y) % 2 + (x * y) % 3) % 2 == 0


_FORMAT_MASK = 0b101010000010010


def _draw_format(grid: list[list[int]], mask: int) -> None:
    # ECC-M = 00
    data = (0b00 << 3) | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ (0x537 if rem & 0x400 else 0)
    bits = (data << 10 | rem) ^ _FORMAT_MASK
    n = len(grid)
    # (col, row) — как в qrcode/ISO, биты MSB→LSB
    coords_a = [
        (0, 8), (1, 8), (2, 8), (3, 8), (4, 8), (5, 8), (7, 8), (8, 8),
        (8, 7), (8, 5), (8, 4), (8, 3), (8, 2), (8, 1), (8, 0),
    ]
    coords_b = [
        (n - 1, 8), (n - 2, 8), (n - 3, 8), (n - 4, 8), (n - 5, 8), (n - 6, 8), (n - 7, 8), (n - 8, 8),
        (8, n - 7), (8, n - 6), (8, n - 5), (8, n - 4), (8, n - 3), (8, n - 2), (8, n - 1),
    ]
    for i, (x, y) in enumerate(coords_a):
        grid[y][x] = (bits >> (14 - i)) & 1
    for i, (x, y) in enumerate(coords_b):
        grid[y][x] = (bits >> (14 - i)) & 1


def _draw_version(grid: list[list[int]], version: int) -> None:
    rem = version
    for _ in range(12):
        rem = (rem << 1) ^ (0x1F25 if rem & 0x800 else 0)
    bits = version << 12 | rem
    n = len(grid)
    for i in range(18):
        bit = (bits >> i) & 1
        a, b = i // 3, i % 3
        grid[a][n - 11 + b] = bit
        grid[n - 11 + b][a] = bit


def _penalty(grid: list[list[int]]) -> int:
    n = len(grid)
    score = 0
    # N1
    for y in range(n):
        run = 1
        for x in range(1, n):
            if grid[y][x] == grid[y][x - 1]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)
    for x in range(n):
        run = 1
        for y in range(1, n):
            if grid[y][x] == grid[y - 1][x]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)
    # N2
    for y in range(n - 1):
        for x in range(n - 1):
            if grid[y][x] == grid[y][x + 1] == grid[y + 1][x] == grid[y + 1][x + 1]:
                score += 3
    # N3 simplified + N4
    dark = sum(sum(row) for row in grid)
    k = abs(100 * dark // (n * n) - 50) // 5
    score += k * 10
    return score


def encode_qr_matrix(text: str) -> list[list[int]]:
    """Возвращает матрицу модулей (1=чёрный, 0=белый) для UTF-8 текста."""
    payload = text.encode("utf-8")
    version = _choose_version(len(payload))
    length_bits = 8 if version <= 9 else 16
    ec_n, g1b, g1d, g2b, g2d = _ECC_M_BLOCKS[version]
    data_cw_count = g1b * g1d + g2b * g2d

    bits = _bit_buffer()
    _append_bits(bits, 0b0100, 4)  # byte mode
    _append_bits(bits, len(payload), length_bits)
    for b in payload:
        _append_bits(bits, b, 8)
    # terminator
    remaining = data_cw_count * 8 - len(bits)
    _append_bits(bits, 0, min(4, remaining))

    data_cw = _bits_to_codewords(bits, data_cw_count)
    interleaved = _interleave(version, data_cw)

    best = None
    best_score = None
    for mask in range(8):
        grid = _build_matrix(version, interleaved, mask)
        score = _penalty(grid)
        if best_score is None or score < best_score:
            best_score = score
            best = grid
    assert best is not None
    return best


def qr_to_rgb(text: str, *, box_size: int = 6, border: int = 2) -> "object":
    """RGB uint8 array (H, W, 3) для matplotlib.imshow."""
    import numpy as np

    matrix = encode_qr_matrix(text)
    n = len(matrix)
    size = (n + border * 2) * box_size
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    for y, row in enumerate(matrix):
        for x, val in enumerate(row):
            if not val:
                continue
            y0 = (y + border) * box_size
            x0 = (x + border) * box_size
            img[y0 : y0 + box_size, x0 : x0 + box_size] = 0
    return img
