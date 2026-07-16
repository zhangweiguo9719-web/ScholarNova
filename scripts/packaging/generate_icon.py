"""Generate ScholarNova Windows icon assets without external dependencies."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "desktop" / "assets"
SIZE = 256


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * max(0.0, min(1.0, t)))


def blend(dst: tuple[int, int, int, int], src: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    sr, sg, sb, sa = src
    dr, dg, db, da = dst
    alpha = sa / 255
    out_a = int(sa + da * (1 - alpha))
    if out_a == 0:
        return 0, 0, 0, 0
    return (
        int(sr * alpha + dr * (1 - alpha)),
        int(sg * alpha + dg * (1 - alpha)),
        int(sb * alpha + db * (1 - alpha)),
        out_a,
    )


def inside_round_rect(x: int, y: int, x0: int, y0: int, x1: int, y1: int, radius: int) -> bool:
    if x0 + radius <= x <= x1 - radius and y0 <= y <= y1:
        return True
    if x0 <= x <= x1 and y0 + radius <= y <= y1 - radius:
        return True
    for cx, cy in (
        (x0 + radius, y0 + radius),
        (x1 - radius, y0 + radius),
        (x0 + radius, y1 - radius),
        (x1 - radius, y1 - radius),
    ):
        if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
            return True
    return False


def draw_line(img: list[list[tuple[int, int, int, int]]], p0, p1, color, width=4):
    x0, y0 = p0
    x1, y1 = p1
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    radius = width / 2
    for i in range(steps + 1):
        t = i / steps
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t
        for y in range(max(0, int(cy - radius - 1)), min(SIZE, int(cy + radius + 2))):
            for x in range(max(0, int(cx - radius - 1)), min(SIZE, int(cx + radius + 2))):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                    img[y][x] = blend(img[y][x], color)


def create_rgba() -> bytes:
    img = [[(0, 0, 0, 0) for _ in range(SIZE)] for _ in range(SIZE)]

    for y in range(SIZE):
        for x in range(SIZE):
            if inside_round_rect(x, y, 0, 0, SIZE - 1, SIZE - 1, 58):
                base = (8, 17, 31, 255)
                dx, dy = x - 176, y - 72
                glow = max(0.0, 1.0 - (dx * dx + dy * dy) ** 0.5 / 155)
                r = lerp(base[0], 219, glow * 0.72)
                g = lerp(base[1], 138, glow * 0.72)
                b = lerp(base[2], 43, glow * 0.55)
                img[y][x] = (r, g, b, 255)

    # Orbit lines.
    for x in range(45, 211):
        y = int(75 - 30 * ((x - 45) / 166) + 20 * (((x - 128) / 100) ** 2))
        draw_line(img, (x, y), (x + 1, y), (241, 181, 77, 190), 5)
    for x in range(50, 209):
        y = int(177 + 19 * (((x - 128) / 85) ** 2))
        draw_line(img, (x, y), (x + 1, y), (86, 214, 214, 110), 4)

    # Book/page shape.
    for y in range(58, 205):
        for x in range(65, 151):
            if 0 <= x < SIZE and 0 <= y < SIZE:
                if x < 77 and y < 70:
                    continue
                t = (y - 58) / 147
                color = (lerp(247, 191, t), lerp(251, 215, t), lerp(255, 244, t), 255)
                img[y][x] = blend(img[y][x], color)

    # Page notch.
    for y in range(170, 207):
        for x in range(95, 151):
            if abs((x - 112) - (206 - y) * 0.95) < 6:
                img[y][x] = blend(img[y][x], (18, 47, 82, 145))

    # Book outline and text lines.
    draw_line(img, (66, 58), (110, 58), (236, 246, 255, 255), 6)
    draw_line(img, (147, 94), (147, 199), (236, 246, 255, 255), 6)
    draw_line(img, (77, 69), (77, 199), (236, 246, 255, 255), 6)
    draw_line(img, (112, 85), (166, 85), (29, 63, 104, 235), 9)
    draw_line(img, (112, 112), (180, 112), (29, 63, 104, 235), 9)
    draw_line(img, (112, 139), (164, 139), (29, 63, 104, 235), 9)

    # Stars.
    for cx, cy, radius, color in [
        (188, 74, 7, (255, 243, 191, 255)),
        (209, 112, 5, (255, 224, 163, 235)),
        (161, 45, 4, (167, 243, 255, 220)),
    ]:
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if 0 <= x < SIZE and 0 <= y < SIZE and (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                    img[y][x] = blend(img[y][x], color)

    return b"".join(bytes(pixel) for row in img for pixel in row)


def png_chunk(tag: bytes, data: bytes) -> bytes:
    payload = tag + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)


def write_png(path: Path, rgba: bytes) -> None:
    rows = []
    stride = SIZE * 4
    for y in range(SIZE):
        rows.append(b"\x00" + rgba[y * stride : (y + 1) * stride])
    raw = b"".join(rows)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def write_ico(path: Path, png_data: bytes) -> None:
    header = struct.pack("<HHH", 0, 1, 1)
    directory = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png_data), 6 + 16)
    path.write_bytes(header + directory + png_data)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    rgba = create_rgba()
    png_path = ASSET_DIR / "icon.png"
    ico_path = ASSET_DIR / "icon.ico"
    write_png(png_path, rgba)
    write_ico(ico_path, png_path.read_bytes())


if __name__ == "__main__":
    main()
