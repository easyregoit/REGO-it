import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFont
from collections import Counter

# Curated dictionary of active, high-availability official brick colors (RGB)
BRICK_PALETTE = {
    (1, "White"): (255, 255, 255),
    (5, "Red"): (201, 26, 9),
    (7, "Blue"): (0, 85, 191),
    (3, "Yellow"): (242, 205, 55),
    (11, "Black"): (5, 19, 29),
    (6, "Green"): (35, 120, 65),
    (2, "Tan"): (228, 205, 158),
    (69, "Dark Tan"): (149, 138, 115),
    (86, "Light Bluish Gray"): (160, 165, 169),
    (85, "Dark Bluish Gray"): (108, 110, 104),
    (88, "Reddish Brown"): (88, 42, 18),
    (4, "Orange"): (254, 138, 24),
    (110, "Bright Light Orange"): (248, 187, 61),
    (105, "Bright Light Blue"): (159, 195, 233),
    (42, "Medium Blue"): (90, 147, 219),
    (63, "Dark Blue"): (10, 52, 99),
    (59, "Dark Red"): (114, 14, 15),
    (34, "Lime"): (187, 233, 11),
    (80, "Dark Green"): (24, 70, 50),
    (48, "Sand Green"): (160, 188, 172),
    (55, "Sand Blue"): (96, 116, 161),
    (90, "Light Nougat"): (246, 215, 179),
    (28, "Nougat"): (208, 145, 104),
    (150, "Medium Nougat"): (170, 125, 85),
    (120, "Dark Brown"): (53, 33, 0),
    (71, "Magenta"): (146, 57, 120),
    (104, "Bright Pink"): (228, 173, 200),
    (89, "Dark Purple"): (63, 54, 145),
    (156, "Medium Azure"): (54, 174, 191),
    (153, "Dark Azure"): (7, 139, 201),
    (36, "Bright Green"): (75, 159, 74),
    (155, "Olive Green"): (155, 154, 90),
}

GRID_PRESETS = {
    "0": ("frame_32",  (32, 32),   "Picture Frame Abstract (32x32 studs - Low Cost ~220 pcs)"),
    "1": ("small_48",  (48, 48),   "1x1 Baseplate (48x48 studs - Icons & Simple Logos)"),
    "2": ("medium_64", (64, 64),   "4x 32x32 Baseplates (64x64 studs - Close-up Portraits)"),
    "3": ("large_96",  (96, 96),   "2x2 Grid of 48x48 Baseplates (96x96 studs - Sharp Portraits)"),
    "4": ("xl_128",    (128, 128), "4x4 Grid of 32x32 Baseplates (128x128 studs - High Detail)"),
    "5": ("ultra_144", (144, 144), "3x3 Grid of 48x48 Baseplates (144x144 studs - Wall Mural)"),
    "6": ("auto",      None,       "Auto-Detect Best Grid Size Based on Image Detail"),
}

# Universal Part IDs (compatible with both BrickLink and BrickOwl XML importers)
PART_CATALOG = {
    # Full-Height Standard Bricks (1 Brick = 3 Plates Tall)
    "brick_2x4":         ("3001",  "Brick 2 x 4 (3-Plate Tall)"),
    "brick_2x3":         ("3002",  "Brick 2 x 3 (3-Plate Tall)"),
    "brick_2x2":         ("3003",  "Brick 2 x 2 (3-Plate Tall)"),
    "brick_1x4":         ("3010",  "Brick 1 x 4 (3-Plate Tall)"),
    "brick_1x3":         ("3622",  "Brick 1 x 3 (3-Plate Tall)"),
    "brick_1x2":         ("3004",  "Brick 1 x 2 (3-Plate Tall)"),
    "brick_1x1":         ("3005",  "Brick 1 x 1 (3-Plate Tall)"),

    # Sculpted 3D Slopes, Curved Slopes, Triangular Tiles & Wedge Plates
    "tile_tri_2x2":      ("35787", "Tile, Modified 2 x 2 Triangular (45° Diagonal)"),
    "wedge_2x2_left":    ("24299", "Wedge, Plate 2 x 2 Left (Angled Studded)"),
    "wedge_2x2_right":   ("24307", "Wedge, Plate 2 x 2 Right (Angled Studded)"),
    "slope_1x1":         ("54200", "Slope 30 1 x 1 x 2/3 (Cheese Slope)"),
    "slope_1x2":         ("85984", "Slope 30 1 x 2 x 2/3 (Pitched Ramp)"),
    "slope_curved_2x1":  ("11477", "Slope, Curved 2 x 1 x 2/3 (Smooth Curve)"),
    "tile_macaroni_2x2": ("27925", "Tile, Round Corner 2 x 2 Macaroni"),

    # Rectangular Studded Plates (1 Plate Tall)
    "plate_2x4":         ("3020",  "Plate 2 x 4 (Studded)"),
    "plate_2x3":         ("3021",  "Plate 2 x 3 (Studded)"),
    "plate_2x2":         ("3022",  "Plate 2 x 2 (Studded)"),
    "plate_1x4":         ("3710",  "Plate 1 x 4 (Studded)"),
    "plate_1x3":         ("3623",  "Plate 1 x 3 (Studded)"),
    "plate_1x2":         ("3023",  "Plate 1 x 2 (Studded)"),
    "plate_1x1":         ("3024",  "Plate 1 x 1 Square (Studded)"),
    "plate_round_1x1":   ("4073",  "Plate 1 x 1 Round (Studded)"),

    # Rectangular Smooth Flat Tiles (1 Plate Tall, Smooth Top)
    "tile_2x4":          ("87079", "Tile 2 x 4 (Flat)"),
    "tile_2x2":          ("3068",  "Tile 2 x 2 (Flat)"),
    "tile_1x4":          ("2431",  "Tile 1 x 4 (Flat)"),
    "tile_1x3":          ("63864", "Tile 1 x 3 (Flat)"),
    "tile_1x2":          ("3069",  "Tile 1 x 2 (Flat)"),
    "tile_1x1":          ("3070",  "Tile 1 x 1 Square (Flat)"),
    "tile_round_1x1":    ("98138", "Tile 1 x 1 Round (Flat)"),
    "tile_round_2x2":    ("14769", "Tile 2 x 2 Round (Flat)"),

    # Curved / Diagonal 1x1 Accuracy Tiles
    "tile_qtr_1x1":      ("25269", "Tile 1 x 1 Quarter Circle (Curved)"),
}

PLATE_TO_BRICK_KEY = {
    "plate_2x4": "brick_2x4",
    "plate_2x3": "brick_2x3",
    "plate_2x2": "brick_2x2",
    "plate_1x4": "brick_1x4",
    "plate_1x3": "brick_1x3",
    "plate_1x2": "brick_1x2",
    "plate_1x1": "brick_1x1",
}

PART_COLOR_WHITELIST = {
    "tile_tri_2x2":      {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 59, 63, 69, 85, 86, 88, 90, 110, 150, 155, 156},
    "wedge_2x2_left":    {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 48, 55, 59, 63, 69, 80, 85, 86, 88, 110, 120, 155},
    "wedge_2x2_right":   {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 48, 55, 59, 63, 69, 80, 85, 86, 88, 110, 120, 155},
    "slope_1x1":         {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "slope_1x2":         {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "slope_curved_2x1":  {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "tile_macaroni_2x2": {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 48, 59, 63, 69, 71, 85, 86, 88, 90, 104, 105, 110, 150, 156},
    "tile_qtr_1x1":      {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 48, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 150, 153, 155, 156},
    "tile_round_2x2":    {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 59, 63, 69, 85, 86, 88, 90, 110, 150, 156},
    "tile_2x4":          {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "tile_1x3":          {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "tile_round_1x1":    {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "plate_round_1x1":   {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
}


def get_baseplate_module_size(grid_size: tuple[int, int]) -> tuple[int, int]:
    """
    Determines the physical sub-baseplate module dimensions (bp_h, bp_w) based on overall grid size
    so the manual builds 1 isolated baseplate at a time (Step 1: Baseplate 1, Step 2: Baseplate 1 + 2, etc.):
    - 32x32 -> 2x2 grid of 16x16 modular baseplates (4 baseplates)
    - 48x48 -> 2x2 grid of 24x24 baseplate quadrants (4 baseplates)
    - 64x64 -> 2x2 grid of 32x32 baseplates (4 baseplates)
    - 96x96 -> 3x3 grid of 32x32 baseplates (9 baseplates)
    - 128x128 -> 4x4 grid of 32x32 baseplates (16 baseplates)
    """
    h, w = grid_size
    if h <= 32 and w <= 32:
        return (16, 16)
    if h == 48 and w == 48:
        return (24, 24)
    if h % 32 == 0 and w % 32 == 0:
        return (32, 32)
    if h % 48 == 0 and w % 48 == 0:
        return (48, 48)
    return (max(16, h // 2), max(16, w // 2))


def is_part_available(part_key: str, color_id: int) -> bool:
    if part_key not in PART_COLOR_WHITELIST:
        if color_id == 28 and part_key not in ("plate_1x1", "plate_1x2", "tile_1x1", "tile_1x2", "tile_2x2"):
            return False
        return True
    return color_id in PART_COLOR_WHITELIST[part_key]


def rgb2lab_numpy(rgb_norm: np.ndarray) -> np.ndarray:
    mask = rgb_norm > 0.04045
    rgb_lin = np.where(mask, ((rgb_norm + 0.055) / 1.055) ** 2.4, rgb_norm / 12.92)
    m = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ], dtype=np.float32)
    xyz = np.dot(rgb_lin, m.T)
    xyz_ref = np.array([0.95047, 1.00000, 1.08883], dtype=np.float32)
    xyz_norm = xyz / xyz_ref
    epsilon = 0.008856
    kappa = 903.3
    f = np.where(xyz_norm > epsilon, np.cbrt(xyz_norm), (kappa * xyz_norm + 16.0) / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def sobel_edges_numpy(img_rgb_norm: np.ndarray) -> np.ndarray:
    gray = 0.2126 * img_rgb_norm[..., 0] + 0.7152 * img_rgb_norm[..., 1] + 0.0722 * img_rgb_norm[..., 2]
    p = np.pad(gray, pad_width=1, mode="edge")
    gx = (p[:-2, 2:] + 2.0 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2.0 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2.0 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2.0 * p[:-2, 1:-1] + p[:-2, 2:])
    return np.hypot(gx, gy)


def center_crop_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    return img.crop((left, top, left + min_dim, top + min_dim))


def auto_detect_grid_size(img_cropped: Image.Image) -> tuple[int, int]:
    sample = img_cropped.resize((256, 256), Image.Resampling.BILINEAR)
    arr = np.asarray(sample, dtype=np.float32) / 255.0
    edge_energy = float(np.mean(sobel_edges_numpy(arr)))
    if edge_energy < 0.12:
        return (64, 64)
    elif edge_energy < 0.22:
        return (96, 96)
    return (128, 128)


def clamp_rgb(rgb: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c) + delta)) for c in rgb)


def denoise_and_smooth_grid(
    nearest_indices: np.ndarray,
    delta_e: np.ndarray,
    edge_map: np.ndarray,
    merge_tolerance_de: float = 2.2
) -> np.ndarray:
    smoothed = nearest_indices.copy()
    h, w = smoothed.shape
    edge_cutoff = np.quantile(edge_map, 0.75)

    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if edge_map[r, c] > edge_cutoff:
                continue
            center_color = smoothed[r, c]
            neighbors = [
                smoothed[r - 1, c], smoothed[r + 1, c],
                smoothed[r, c - 1], smoothed[r, c + 1]
            ]
            if center_color not in neighbors:
                most_common_color, freq = Counter(neighbors).most_common(1)[0]
                if freq >= 2:
                    current_de = delta_e[r, c, center_color]
                    candidate_de = delta_e[r, c, most_common_color]
                    if (candidate_de - current_de) <= merge_tolerance_de:
                        smoothed[r, c] = most_common_color
    return smoothed


def detect_subpixel_orientation(
    sub_cell_lab: np.ndarray,
    fg_lab: np.ndarray,
    bg_lab: np.ndarray
) -> tuple[str | None, float]:
    d_fg = np.linalg.norm(sub_cell_lab - fg_lab, axis=-1)
    d_bg = np.linalg.norm(sub_cell_lab - bg_lab, axis=-1)
    solid_fg_err = float(np.sum(d_fg))
    orientations = {
        "BR": d_bg[0, 0] + d_fg[0, 1] + d_fg[1, 0] + d_fg[1, 1],
        "BL": d_fg[0, 0] + d_bg[0, 1] + d_fg[1, 0] + d_fg[1, 1],
        "TR": d_fg[0, 0] + d_fg[0, 1] + d_bg[1, 0] + d_fg[1, 1],
        "TL": d_fg[0, 0] + d_fg[0, 1] + d_fg[1, 0] + d_bg[1, 1],
    }
    best_orient, best_err = min(orientations.items(), key=lambda x: x[1])
    return best_orient, solid_fg_err - float(best_err)


def detect_2x2_diagonal_corner(
    nearest_indices: np.ndarray,
    z_grid: np.ndarray,
    groove_mask: np.ndarray | None,
    r: int,
    c: int,
    lz: int
) -> tuple[str, int, int] | None:
    if groove_mask is not None and np.any(groove_mask[r:r + 2, c:c + 2]):
        return None
    if not np.all(z_grid[r:r + 2, c:c + 2] == lz):
        return None

    block = nearest_indices[r:r + 2, c:c + 2]
    vals, counts = np.unique(block, return_counts=True)
    if len(vals) != 2 or not (3 in counts and 1 in counts):
        return None

    fg_col = int(vals[np.argmax(counts)])
    bg_col = int(vals[np.argmin(counts)])

    if block[1, 1] == bg_col:
        return ("TL", fg_col, bg_col)
    if block[1, 0] == bg_col:
        return ("TR", fg_col, bg_col)
    if block[0, 1] == bg_col:
        return ("BL", fg_col, bg_col)
    if block[0, 0] == bg_col:
        return ("BR", fg_col, bg_col)
    return None


def draw_quarter_tile(
    draw: ImageDraw.ImageDraw,
    x0: int, y0: int, x1: int, y1: int,
    fg_color: tuple[int, int, int],
    bg_color: tuple[int, int, int],
    orient: str,
    seam: tuple[int, int, int]
):
    draw.rectangle([x0, y0, x1, y1], fill=bg_color, outline=seam, width=1)
    w = x1 - x0
    h = y1 - y0
    if orient == "BR":
        bbox = [x0, y0, x0 + 2 * w, y0 + 2 * h]
        draw.pieslice(bbox, start=180, end=270, fill=fg_color, outline=seam)
    elif orient == "BL":
        bbox = [x1 - 2 * w, y0, x1, y0 + 2 * h]
        draw.pieslice(bbox, start=270, end=360, fill=fg_color, outline=seam)
    elif orient == "TR":
        bbox = [x0, y1 - 2 * h, x0 + 2 * w, y1]
        draw.pieslice(bbox, start=90, end=180, fill=fg_color, outline=seam)
    else:
        bbox = [x1 - 2 * w, y1 - 2 * h, x1, y1]
        draw.pieslice(bbox, start=0, end=90, fill=fg_color, outline=seam)


def draw_triangular_2x2(
    draw: ImageDraw.ImageDraw,
    x0: int, y0: int, x1: int, y1: int,
    fg_color: tuple[int, int, int],
    bg_color: tuple[int, int, int],
    orient: str,
    seam: tuple[int, int, int],
    highlight: tuple[int, int, int],
    shadow: tuple[int, int, int],
    bevel_w: int = 2
):
    draw.rectangle([x0, y0, x1, y1], fill=bg_color, outline=seam, width=1)
    xm = (x0 + x1) // 2
    ym = (y0 + y1) // 2
    draw.line([(xm, y0), (xm, y1)], fill=clamp_rgb(bg_color, -45), width=1)
    draw.line([(x0, ym), (x1, ym)], fill=clamp_rgb(bg_color, -45), width=1)

    if orient == "TL":
        pts = [(x0, y0), (x1, y0), (x0, y1)]
    elif orient == "TR":
        pts = [(x0, y0), (x1, y0), (x1, y1)]
    elif orient == "BL":
        pts = [(x0, y0), (x1, y1), (x0, y1)]
    else:
        pts = [(x1, y0), (x1, y1), (x0, y1)]

    draw.polygon(pts, fill=fg_color, outline=seam)
    draw.line(pts + [pts[0]], fill=seam, width=max(1, bevel_w))
    draw.line([pts[0], pts[1]], fill=highlight, width=bevel_w)
    draw.line([pts[1], pts[2]], fill=shadow, width=bevel_w)


def draw_slope_piece(
    draw: ImageDraw.ImageDraw,
    x0: int, y0: int, x1: int, y1: int,
    face_color: tuple[int, int, int],
    orient: str,
    seam: tuple[int, int, int],
    is_curved: bool = False
):
    ridge_col = clamp_rgb(face_color, 42)
    upper_ramp = clamp_rgb(face_color, 14)
    lower_ramp = clamp_rgb(face_color, -32)
    toe_shadow = clamp_rgb(face_color, -56)

    draw.rectangle([x0, y0, x1, y1], fill=upper_ramp, outline=seam, width=1)
    w = max(4, x1 - x0)
    h = max(4, y1 - y0)

    if orient == "N":
        ridge_y = y1 - max(2, h // 4)
        mid_y = (y0 + ridge_y) // 2
        draw.rectangle([x0 + 1, y0 + 1, x1 - 1, mid_y], fill=lower_ramp)
        draw.rectangle([x0 + 1, ridge_y, x1 - 1, y1 - 1], fill=ridge_col)
        draw.line([(x0 + 1, ridge_y), (x1 - 1, ridge_y)], fill=seam, width=1)
        draw.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], fill=toe_shadow, width=2)
    elif orient == "S":
        ridge_y = y0 + max(2, h // 4)
        mid_y = (ridge_y + y1) // 2
        draw.rectangle([x0 + 1, mid_y, x1 - 1, y1 - 1], fill=lower_ramp)
        draw.rectangle([x0 + 1, y0 + 1, x1 - 1, ridge_y], fill=ridge_col)
        draw.line([(x0 + 1, ridge_y), (x1 - 1, ridge_y)], fill=seam, width=1)
        draw.line([(x0 + 1, y1 - 1), (x1 - 1, y1 - 1)], fill=toe_shadow, width=2)
    elif orient == "W":
        ridge_x = x1 - max(2, w // 4)
        mid_x = (x0 + ridge_x) // 2
        draw.rectangle([x0 + 1, y0 + 1, mid_x, y1 - 1], fill=lower_ramp)
        draw.rectangle([ridge_x, y0 + 1, x1 - 1, y1 - 1], fill=ridge_col)
        draw.line([(ridge_x, y0 + 1), (ridge_x, y1 - 1)], fill=seam, width=1)
        draw.line([(x0 + 1, y0 + 1), (x0 + 1, y1 - 1)], fill=toe_shadow, width=2)
    else:
        ridge_x = x0 + max(2, w // 4)
        mid_x = (ridge_x + x1) // 2
        draw.rectangle([mid_x, y0 + 1, x1 - 1, y1 - 1], fill=lower_ramp)
        draw.rectangle([x0 + 1, y0 + 1, ridge_x, y1 - 1], fill=ridge_col)
        draw.line([(ridge_x, y0 + 1), (ridge_x, y1 - 1)], fill=seam, width=1)
        draw.line([(x1 - 1, y0 + 1), (x1 - 1, y1 - 1)], fill=toe_shadow, width=2)

    if is_curved:
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        draw.ellipse([cx - w // 4, cy - h // 4, cx + w // 4, cy + h // 4], fill=upper_ramp)


def extract_neural_foreground_mask(img_pil: Image.Image) -> np.ndarray | None:
    work_img = img_pil.resize((256, 256), Image.Resampling.BILINEAR).convert("RGB")
    rgb_norm = np.asarray(work_img, dtype=np.float32) / 255.0
    lab = rgb2lab_numpy(rgb_norm)
    h, w, _ = lab.shape

    b_pad = 8
    border_pixels = np.concatenate([
        lab[:b_pad, :, :].reshape(-1, 3),
        lab[-b_pad:, :, :].reshape(-1, 3),
        lab[:, :b_pad, :].reshape(-1, 3),
        lab[:, -b_pad:, :].reshape(-1, 3),
    ], axis=0)

    step = max(1, len(border_pixels) // 4)
    bg_refs = [np.median(border_pixels[i * step:(i + 1) * step], axis=0) for i in range(4)]
    bg_dists = [np.linalg.norm(lab - ref[np.newaxis, np.newaxis, :], axis=-1) for ref in bg_refs]
    min_bg_dist = np.min(np.stack(bg_dists, axis=-1), axis=-1)

    border_noise = float(np.percentile(
        np.min(np.stack([np.linalg.norm(border_pixels - r[None, :], axis=-1) for r in bg_refs], axis=-1), axis=-1),
        90
    ))

    cutoff = max(14.0, border_noise * 2.5)
    raw_mask = min_bg_dist > cutoff

    mask_img = Image.fromarray((raw_mask.astype(np.uint8) * 255), mode="L")
    mask_img = mask_img.filter(ImageFilter.MedianFilter(size=5))
    fg_mask = np.asarray(mask_img) > 127

    fg_mask[0, :] = False
    fg_mask[-1, :] = False
    fg_mask[:, 0] = False
    fg_mask[:, -1] = False

    if 0.03 < float(np.mean(fg_mask)) < 0.90:
        return fg_mask
    return None


def filter_background_and_abstract_subject(
    img_cropped: Image.Image,
    palette_keys: list[tuple[int, str]]
) -> tuple[Image.Image, np.ndarray, int]:
    work_img = img_cropped.resize((256, 256), Image.Resampling.BILINEAR)
    fg_mask = extract_neural_foreground_mask(work_img)

    rgb_norm = np.asarray(work_img.convert("RGB"), dtype=np.float32) / 255.0
    lab = rgb2lab_numpy(rgb_norm)

    if fg_mask is None:
        h, w, _ = lab.shape
        fg_mask = np.zeros((h, w), dtype=bool)
        fg_mask[h // 6:5 * h // 6, w // 6:5 * w // 6] = True

    subject_L = float(np.mean(lab[fg_mask, 0])) if np.any(fg_mask) else 50.0
    preferred_bg_cid = 63 if subject_L > 48.0 else 86
    bg_palette_idx = next((i for i, (cid, _) in enumerate(palette_keys) if cid == preferred_bg_cid), 0)

    poster_img = work_img.filter(ImageFilter.MedianFilter(size=5))
    poster_img = poster_img.filter(ImageFilter.ModeFilter(size=5))
    poster_img = ImageOps.posterize(poster_img, bits=4)

    return poster_img, fg_mask, bg_palette_idx


def detect_boxed_grooves_and_preserve_lines(
    img_cropped: Image.Image,
    grid_size: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    gh, gw = grid_size
    factor = max(2, 512 // max(gh, gw))
    work_h, work_w = gh * factor, gw * factor
    hi_img = img_cropped.resize((work_w, work_h), Image.Resampling.BILINEAR)
    hi_rgb = np.asarray(hi_img, dtype=np.float32) / 255.0
    hi_gray = 0.2126 * hi_rgb[..., 0] + 0.7152 * hi_rgb[..., 1] + 0.0722 * hi_rgb[..., 2]

    gray_u8 = np.clip(hi_gray * 255.0, 0, 255).astype(np.uint8)
    dilated_u8 = np.asarray(
        Image.fromarray(gray_u8, mode="L").filter(ImageFilter.MaxFilter(size=5)),
        dtype=np.float32
    )
    valley_hi = (dilated_u8 - gray_u8.astype(np.float32)) / 255.0

    valley_blocks = valley_hi.reshape(gh, factor, gw, factor)
    c0 = max(0, factor // 4)
    c1 = max(c0 + 1, (factor * 3) // 4)
    raw_grid_valley = np.max(valley_blocks[:, c0:c1, :, c0:c1], axis=(1, 3))

    pad_v = np.pad(raw_grid_valley, 1, mode="constant", constant_values=0.0)
    vert_peak = (raw_grid_valley >= pad_v[1:-1, :-2]) & (raw_grid_valley > pad_v[1:-1, 2:])
    horiz_peak = (raw_grid_valley >= pad_v[:-2, 1:-1]) & (raw_grid_valley > pad_v[2:, 1:-1])
    nms_valley = np.where(vert_peak | horiz_peak, raw_grid_valley, 0.0)

    active_valleys = nms_valley[nms_valley > 0.05]
    dyn_thresh = float(np.quantile(active_valleys, 0.45)) if len(active_valleys) > 0 else 0.09
    groove_thresh = max(0.085, min(0.15, dyn_thresh))
    groove_mask = nms_valley >= groove_thresh

    rgb_blocks = hi_rgb.reshape(gh, factor, gw, factor, 3).transpose(0, 2, 1, 3, 4).reshape(gh, gw, factor * factor, 3)
    luma_blocks = 0.2126 * rgb_blocks[..., 0] + 0.7152 * rgb_blocks[..., 1] + 0.0722 * rgb_blocks[..., 2]
    dark_idx = np.argsort(luma_blocks, axis=-1)[:, :, :1]
    row_idx = np.arange(gh)[:, None, None]
    col_idx = np.arange(gw)[None, :, None]
    dark_sub_rgb = np.clip(np.mean(rgb_blocks[row_idx, col_idx, dark_idx], axis=2) * 0.55, 0.0, 1.0)

    return groove_mask, dark_sub_rgb


def compute_stable_terrace_z_grid(
    img_lab: np.ndarray,
    edge_map: np.ndarray,
    grid_size: tuple[int, int],
    z_layers: int = 1,
    z_mode: str = "luminance",
    fg_mask_grid: np.ndarray | None = None,
    groove_mask: np.ndarray | None = None
) -> np.ndarray:
    h, w = grid_size
    if z_layers <= 1:
        return np.ones((h, w), dtype=np.int32)

    b_pad = max(2, min(h, w) // 12)
    border_lab = np.concatenate([
        img_lab[:b_pad, :, :].reshape(-1, 3),
        img_lab[-b_pad:, :, :].reshape(-1, 3),
        img_lab[:, :b_pad, :].reshape(-1, 3),
        img_lab[:, -b_pad:, :].reshape(-1, 3),
    ], axis=0)

    step = max(1, len(border_lab) // 4)
    bg_refs = [np.median(border_lab[i * step:(i + 1) * step], axis=0) for i in range(4)]
    min_bg_dist = np.min(
        np.stack([np.linalg.norm(img_lab - ref[None, None, :], axis=-1) for ref in bg_refs], axis=-1),
        axis=-1
    )
    border_noise = float(np.percentile(
        np.min(np.stack([np.linalg.norm(border_lab - r[None, :], axis=-1) for r in bg_refs], axis=-1), axis=-1),
        90
    ))

    is_subject = min_bg_dist > max(14.0, border_noise * 2.5)
    if fg_mask_grid is not None:
        is_subject = is_subject & fg_mask_grid

    s_img = Image.fromarray((is_subject.astype(np.uint8) * 255), mode="L")
    s_img = s_img.filter(ImageFilter.MedianFilter(size=3))
    is_subject = np.asarray(s_img) > 127

    z_grid = np.ones((h, w), dtype=np.int32)
    if not np.any(is_subject):
        return z_grid

    z_grid[is_subject] = z_layers
    recess_z = max(1, z_layers - 1)
    if groove_mask is not None:
        z_grid[is_subject & groove_mask] = recess_z

    return z_grid


def build_interlocking_layers(
    nearest_indices: np.ndarray,
    stud_mask: np.ndarray,
    edge_map: np.ndarray,
    subpixel_lab: np.ndarray,
    palette_lab: np.ndarray,
    palette_keys: list[tuple[int, str]],
    z_grid: np.ndarray,
    groove_mask: np.ndarray | None = None,
    filler_color_id: int = 86
) -> tuple[list[dict], list[dict]]:
    """
    Packs all layers while strictly respecting physical baseplate module seams (bp_h, bp_w)
    so each baseplate can be built independently (Step 1: Baseplate 1, Step 2: Baseplate 1 + 2, etc.)
    without any brick overhanging an unbuilt neighboring baseplate.
    """
    h, w = nearest_indices.shape
    bp_h, bp_w = get_baseplate_module_size((h, w))
    max_z = int(np.max(z_grid))
    filler_idx = next((idx for idx, (cid, _) in enumerate(palette_keys) if cid == filler_color_id), 0)

    def _within_single_baseplate(r: int, c: int, sh: int, sw: int) -> bool:
        return ((r // bp_h) == ((r + sh - 1) // bp_h)) and ((c // bp_w) == ((c + sw - 1) // bp_w))

    horiz_First = [
        (2, 4, "plate_2x4"), (1, 4, "plate_1x4"), (2, 3, "plate_2x3"),
        (1, 3, "plate_1x3"), (2, 2, "plate_2x2"), (1, 2, "plate_1x2"),
        (4, 2, "plate_2x4"), (4, 1, "plate_1x4"), (3, 2, "plate_2x3"),
        (3, 1, "plate_1x3"), (2, 1, "plate_1x2"),
    ]
    vert_First = [
        (4, 2, "plate_2x4"), (4, 1, "plate_1x4"), (3, 2, "plate_2x3"),
        (3, 1, "plate_1x3"), (2, 2, "plate_2x2"), (2, 1, "plate_1x2"),
        (2, 4, "plate_2x4"), (1, 4, "plate_1x4"), (2, 3, "plate_2x3"),
        (1, 3, "plate_1x3"), (1, 2, "plate_1x2"),
    ]
    horiz_Tiles = [
        (2, 4, "tile_2x4"), (1, 4, "tile_1x4"), (2, 2, "tile_2x2"),
        (1, 3, "tile_1x3"), (1, 2, "tile_1x2"),
        (4, 2, "tile_2x4"), (4, 1, "tile_1x4"), (3, 1, "tile_1x3"), (2, 1, "tile_1x2"),
    ]
    vert_Tiles = [
        (4, 2, "tile_2x4"), (4, 1, "tile_1x4"), (2, 2, "tile_2x2"),
        (3, 1, "tile_1x3"), (2, 1, "tile_1x2"),
        (2, 4, "tile_2x4"), (1, 4, "tile_1x4"), (1, 3, "tile_1x3"), (1, 2, "tile_1x2"),
    ]

    surface_placements: list[dict] = []
    under_placements: list[dict] = []

    occupied = np.zeros((max_z + 1, h, w), dtype=bool)
    seam_grids = np.zeros((max_z + 1, h, w), dtype=np.int32)
    uid = 1

    if max_z >= 4:
        brick_under_mask = (z_grid >= 4)
        bu_visited = ~brick_under_mask
        for r in range(h):
            for c in range(w):
                if bu_visited[r, c]:
                    continue
                best_shape = (1, 1, "plate_1x1")
                for sh, sw, p_key in horiz_First:
                    b_key = PLATE_TO_BRICK_KEY[p_key]
                    if not is_part_available(b_key, filler_color_id):
                        continue
                    if (r + sh <= h and c + sw <= w
                            and _within_single_baseplate(r, c, sh, sw)
                            and not np.any(bu_visited[r:r + sh, c:c + sw])):
                        best_shape = (sh, sw, p_key)
                        break
                sh, sw, p_key = best_shape
                b_key = PLATE_TO_BRICK_KEY[p_key]
                bu_visited[r:r + sh, c:c + sw] = True
                occupied[1:4, r:r + sh, c:c + sw] = True
                uid += 1
                seam_grids[3, r:r + sh, c:c + sw] = uid
                under_placements.append({
                    "r": r, "c": c, "h": sh, "w": sw,
                    "z": 3, "z_span": 3,
                    "color_idx": filler_idx,
                    "bg_color_idx": filler_idx,
                    "part_key": b_key,
                    "is_stud": True,
                    "shape": "rect",
                    "orient": None,
                    "is_structural": True,
                })

    for lz in range(1, max_z + 1):
        prev_seam_grid = seam_grids[lz - 1]
        curr_seam_grid = seam_grids[lz].copy()
        odd_layer = (lz % 2 == 1)
        plate_order = horiz_First if odd_layer else vert_First
        tile_order = horiz_Tiles if odd_layer else vert_Tiles

        # 1. Structural Light Bluish Gray (#86) under-plates where z_grid > lz
        struct_visited = (~(z_grid > lz)) | occupied[lz]
        for r in range(h):
            for c in range(w):
                if struct_visited[r, c]:
                    continue
                best_shape = (1, 1, "plate_1x1")
                best_score = -1
                for sh, sw, part_key in plate_order:
                    if not is_part_available(part_key, filler_color_id):
                        continue
                    if (r + sh <= h and c + sw <= w
                            and _within_single_baseplate(r, c, sh, sw)
                            and not np.any(struct_visited[r:r + sh, c:c + sw])):
                        bridged = len(np.unique(prev_seam_grid[r:r + sh, c:c + sw])) if lz > 1 else 1
                        score = (bridged * 35) + (sh * sw * 5)
                        if score > best_score:
                            best_score = score
                            best_shape = (sh, sw, part_key)
                        if bridged >= 2 and sh * sw >= 6:
                            break
                sh, sw, part_key = best_shape
                struct_visited[r:r + sh, c:c + sw] = True
                occupied[lz, r:r + sh, c:c + sw] = True
                uid += 1
                curr_seam_grid[r:r + sh, c:c + sw] = uid
                under_placements.append({
                    "r": r, "c": c, "h": sh, "w": sw,
                    "z": lz, "z_span": 1,
                    "color_idx": filler_idx,
                    "bg_color_idx": filler_idx,
                    "part_key": part_key,
                    "is_stud": True,
                    "shape": "rect",
                    "orient": None,
                    "is_structural": True,
                })

        surf_visited = (~(z_grid == lz)) | occupied[lz]

        # 2A. SCULPTING PASS A: 2x2 Triangular Tiles (#35787) & Wedge Plates (#24299/#24307)
        for r in range(h - 1):
            for c in range(w - 1):
                if not _within_single_baseplate(r, c, 2, 2):
                    continue
                if np.any(surf_visited[r:r + 2, c:c + 2]):
                    continue
                diag_hit = detect_2x2_diagonal_corner(nearest_indices, z_grid, groove_mask, r, c, lz)
                if diag_hit is None:
                    continue
                orient, fg_idx, bg_idx = diag_hit
                fg_cid = palette_keys[fg_idx][0]
                is_st = bool(np.any(stud_mask[r:r + 2, c:c + 2]))

                if is_st and is_part_available("wedge_2x2_left", fg_cid):
                    part_key = "wedge_2x2_left" if orient in ("TL", "BR") else "wedge_2x2_right"
                    shape_type = "wedge_2x2"
                elif is_part_available("tile_tri_2x2", fg_cid):
                    part_key = "tile_tri_2x2"
                    shape_type = "tri_2x2"
                    is_st = False
                else:
                    continue

                surf_visited[r:r + 2, c:c + 2] = True
                occupied[lz, r:r + 2, c:c + 2] = True
                uid += 1
                curr_seam_grid[r:r + 2, c:c + 2] = uid
                surface_placements.append({
                    "r": r, "c": c, "h": 2, "w": 2,
                    "z": lz, "z_span": 1,
                    "color_idx": fg_idx,
                    "bg_color_idx": bg_idx,
                    "part_key": part_key,
                    "is_stud": is_st,
                    "shape": shape_type,
                    "orient": orient,
                    "is_structural": False,
                })

        # 2B. SCULPTING PASS B: 1x2 Slopes (#85984) & 2x1 Curved Slopes (#11477)
        if lz > 1:
            for r in range(h):
                for c in range(w):
                    if surf_visited[r, c]:
                        continue
                    if groove_mask is not None and groove_mask[r, c]:
                        continue
                    color_idx = int(nearest_indices[r, c])
                    color_id = palette_keys[color_idx][0]

                    drop_N = (r > 0 and z_grid[r - 1, c] < lz)
                    drop_S = (r + 1 < h and z_grid[r + 1, c] < lz)
                    drop_W = (c > 0 and z_grid[r, c - 1] < lz)
                    drop_E = (c + 1 < w and z_grid[r, c + 1] < lz)

                    if not (drop_N or drop_S or drop_W or drop_E):
                        continue

                    slope_dir = "N" if drop_N else ("S" if drop_S else ("W" if drop_W else "E"))

                    if (slope_dir in ("N", "S") and c + 2 <= w
                            and _within_single_baseplate(r, c, 1, 2)
                            and not np.any(surf_visited[r:r + 1, c:c + 2])):
                        if (nearest_indices[r, c + 1] == color_idx
                                and (groove_mask is None or not groove_mask[r, c + 1])
                                and is_part_available("slope_1x2", color_id)):
                            surf_visited[r, c:c + 2] = True
                            occupied[lz, r, c:c + 2] = True
                            uid += 1
                            curr_seam_grid[r, c:c + 2] = uid
                            surface_placements.append({
                                "r": r, "c": c, "h": 1, "w": 2,
                                "z": lz, "z_span": 1,
                                "color_idx": color_idx,
                                "bg_color_idx": color_idx,
                                "part_key": "slope_1x2",
                                "is_stud": False,
                                "shape": "slope",
                                "orient": slope_dir,
                                "is_structural": False,
                            })
                            continue
                    elif (slope_dir in ("E", "W") and r + 2 <= h
                          and _within_single_baseplate(r, c, 2, 1)
                          and not np.any(surf_visited[r:r + 2, c:c + 1])):
                        if (nearest_indices[r + 1, c] == color_idx
                                and (groove_mask is None or not groove_mask[r + 1, c])
                                and is_part_available("slope_curved_2x1", color_id)):
                            surf_visited[r:r + 2, c] = True
                            occupied[lz, r:r + 2, c] = True
                            uid += 1
                            curr_seam_grid[r:r + 2, c] = uid
                            surface_placements.append({
                                "r": r, "c": c, "h": 2, "w": 1,
                                "z": lz, "z_span": 1,
                                "color_idx": color_idx,
                                "bg_color_idx": color_idx,
                                "part_key": "slope_curved_2x1",
                                "is_stud": False,
                                "shape": "slope_curved",
                                "orient": slope_dir,
                                "is_structural": False,
                            })
                            continue

        # 3. PASS C: Interior rectangular plates & flat tiles (locked inside each baseplate module)
        for r in range(h):
            for c in range(w):
                if surf_visited[r, c]:
                    continue
                color_idx = int(nearest_indices[r, c])
                color_id = palette_keys[color_idx][0]
                is_stud = bool(stud_mask[r, c])
                is_grv = bool(groove_mask[r, c]) if groove_mask is not None else False
                shapes = plate_order if is_stud else tile_order

                best_candidate = None
                best_score = -1
                for sh, sw, part_key in shapes:
                    if not is_part_available(part_key, color_id):
                        continue
                    if is_grv and min(sh, sw) > 1:
                        continue
                    if r + sh <= h and c + sw <= w and _within_single_baseplate(r, c, sh, sw):
                        reg_vis = surf_visited[r:r + sh, c:c + sw]
                        reg_col = nearest_indices[r:r + sh, c:c + sw]
                        reg_stud = stud_mask[r:r + sh, c:c + sw]
                        reg_grv = (groove_mask[r:r + sh, c:c + sw] == is_grv) if groove_mask is not None else True
                        if (not np.any(reg_vis)
                                and np.all(reg_grv)
                                and np.all(reg_col == color_idx)
                                and np.all(reg_stud == is_stud)):
                            bridged = len(np.unique(prev_seam_grid[r:r + sh, c:c + sw])) if lz > 1 else 1
                            score = (bridged * 30) + (sh * sw * 6)
                            if score > best_score:
                                best_score = score
                                best_candidate = (sh, sw, part_key)
                            if bridged >= 2 and sh * sw >= 4:
                                break

                if best_candidate is not None:
                    sh, sw, part_key = best_candidate
                    surf_visited[r:r + sh, c:c + sw] = True
                    occupied[lz, r:r + sh, c:c + sw] = True
                    uid += 1
                    curr_seam_grid[r:r + sh, c:c + sw] = uid
                    surface_placements.append({
                        "r": r, "c": c, "h": sh, "w": sw,
                        "z": lz, "z_span": 1,
                        "color_idx": color_idx,
                        "bg_color_idx": color_idx,
                        "part_key": part_key,
                        "is_stud": is_stud,
                        "shape": "rect",
                        "orient": None,
                        "is_structural": False,
                    })

        # 4. PASS D: Remaining 1x1 detail cells — Quarter-Circle Curves (#25269) & 1x1 Cheese Slopes (#54200)
        for r in range(h):
            for c in range(w):
                if surf_visited[r, c]:
                    continue
                surf_visited[r, c] = True
                occupied[lz, r, c] = True
                uid += 1
                curr_seam_grid[r, c] = uid
                color_idx = int(nearest_indices[r, c])
                color_id = palette_keys[color_idx][0]
                is_stud = bool(stud_mask[r, c])
                sub_lab = subpixel_lab[r * 2:(r + 1) * 2, c * 2:(c + 1) * 2]

                neighbors = []
                for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
                    if 0 <= nr < h and 0 <= nc < w and nearest_indices[nr, nc] != color_idx:
                        neighbors.append(int(nearest_indices[nr, nc]))

                placed_special = False
                is_groove_cell = bool(groove_mask[r, c]) if groove_mask is not None else False
                if neighbors and not is_groove_cell and is_part_available("tile_qtr_1x1", color_id):
                    bg_color_idx = Counter(neighbors).most_common(1)[0][0]
                    orient, improvement = detect_subpixel_orientation(
                        sub_lab, palette_lab[color_idx], palette_lab[bg_color_idx]
                    )
                    if improvement > 6.5:
                        surface_placements.append({
                            "r": r, "c": c, "h": 1, "w": 1,
                            "z": lz, "z_span": 1,
                            "color_idx": color_idx,
                            "bg_color_idx": bg_color_idx,
                            "part_key": "tile_qtr_1x1",
                            "is_stud": False,
                            "shape": "qtr_1x1",
                            "orient": orient,
                            "is_structural": False,
                        })
                        placed_special = True

                if not placed_special and neighbors and not is_groove_cell and is_part_available("slope_1x1", color_id):
                    if r > 0 and nearest_indices[r - 1, c] != color_idx:
                        s_dir = "N"
                    elif r + 1 < h and nearest_indices[r + 1, c] != color_idx:
                        s_dir = "S"
                    elif c > 0 and nearest_indices[r, c - 1] != color_idx:
                        s_dir = "W"
                    else:
                        s_dir = "E"
                    surface_placements.append({
                        "r": r, "c": c, "h": 1, "w": 1,
                        "z": lz, "z_span": 1,
                        "color_idx": color_idx,
                        "bg_color_idx": color_idx,
                        "part_key": "slope_1x1",
                        "is_stud": False,
                        "shape": "slope",
                        "orient": s_dir,
                        "is_structural": False,
                    })
                    placed_special = True

                if not placed_special:
                    part_key = "plate_1x1" if is_stud else "tile_1x1"
                    surface_placements.append({
                        "r": r, "c": c, "h": 1, "w": 1,
                        "z": lz, "z_span": 1,
                        "color_idx": color_idx,
                        "bg_color_idx": color_idx,
                        "part_key": part_key,
                        "is_stud": is_stud,
                        "shape": "rect",
                        "orient": None,
                        "is_structural": False,
                    })

        seam_grids[lz] = curr_seam_grid

    return surface_placements, under_placements


def render_mixed_mosaic(
    placements: list[dict],
    palette_rgb: np.ndarray,
    grid_size: tuple[int, int],
    target_output_px: int = 2400
) -> Image.Image:
    h, w = grid_size
    scale_factor = max(20, target_output_px // max(h, w))
    baseplate_rgb = (24, 28, 34)
    canvas = Image.new("RGB", (w * scale_factor, h * scale_factor), baseplate_rgb)
    draw = ImageDraw.Draw(canvas)
    bevel_w = max(1, scale_factor // 14)

    max_z = max((p.get("z", 1) for p in placements), default=1)
    sorted_placements = sorted(placements, key=lambda item: (item.get("z", 1), item["r"], item["c"]))

    for p in sorted_placements:
        z = p.get("z", 1)
        x0 = p["c"] * scale_factor
        y0 = p["r"] * scale_factor
        x1 = (p["c"] + p["w"]) * scale_factor - 1
        y1 = (p["r"] + p["h"]) * scale_factor - 1

        base_color = tuple(int(v) for v in palette_rgb[p["color_idx"]])
        bg_color = tuple(int(v) for v in palette_rgb[p["bg_color_idx"]])

        z_boost = (z - max_z) * 14 if max_z > 1 else 0
        face_color = clamp_rgb(base_color, z_boost)
        highlight = clamp_rgb(face_color, 38 if z == max_z else 20)
        shadow = clamp_rgb(face_color, -45)
        seam = clamp_rgb(base_color, -72)
        shape = p["shape"]

        if shape == "qtr_1x1":
            draw_quarter_tile(draw, x0, y0, x1, y1, face_color, bg_color, p["orient"], seam)
        elif shape in ("tri_2x2", "wedge_2x2"):
            draw_triangular_2x2(
                draw, x0, y0, x1, y1,
                face_color, bg_color, p["orient"],
                seam, highlight, shadow, bevel_w
            )
        elif shape in ("slope", "slope_curved"):
            draw_slope_piece(
                draw, x0, y0, x1, y1,
                face_color, p["orient"] or "N",
                seam, is_curved=(shape == "slope_curved")
            )
        elif shape in ("round_1x1", "round_2x2"):
            draw.rectangle([x0, y0, x1, y1], fill=shadow, outline=seam, width=1)
            pad = max(1, scale_factor // 10)
            draw.ellipse([x0 + pad, y0 + pad, x1 - pad, y1 - pad], fill=face_color, outline=seam, width=1)
            draw.arc([x0 + pad + 1, y0 + pad + 1, x1 - pad - 1, y1 - pad - 1],
                     start=200, end=330, fill=highlight, width=bevel_w)
        else:
            b_thick = bevel_w + (1 if z == max_z and max_z > 1 else 0)
            draw.rectangle([x0, y0, x1, y1], fill=face_color, outline=seam, width=1)
            draw.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], fill=highlight, width=b_thick)
            draw.line([(x0 + 1, y0 + 1), (x0 + 1, y1 - 1)], fill=highlight, width=b_thick)
            draw.line([(x0 + 1, y1 - 1), (x1 - 1, y1 - 1)], fill=shadow, width=b_thick)
            draw.line([(x1 - 1, y0 + 1), (x1 - 1, y1 - 1)], fill=shadow, width=b_thick)

        if p["is_stud"]:
            margin = max(3, int(scale_factor * 0.22))
            orient = p.get("orient")
            for sr in range(p["h"]):
                for sc in range(p["w"]):
                    if shape == "wedge_2x2":
                        if (orient == "TL" and sr == 1 and sc == 1) or \
                           (orient == "TR" and sr == 1 and sc == 0) or \
                           (orient == "BL" and sr == 0 and sc == 1) or \
                           (orient == "BR" and sr == 0 and sc == 0):
                            continue
                    cx0 = (p["c"] + sc) * scale_factor + margin
                    cy0 = (p["r"] + sr) * scale_factor + margin
                    cx1 = (p["c"] + sc + 1) * scale_factor - 1 - margin
                    cy1 = (p["r"] + sr + 1) * scale_factor - 1 - margin
                    draw.ellipse([cx0 + 1, cy0 + 2, cx1 + 1, cy1 + 2], fill=shadow)
                    draw.ellipse([cx0, cy0, cx1, cy1], fill=face_color, outline=shadow, width=1)
                    draw.arc([cx0 + 1, cy0 + 1, cx1 - 1, cy1 - 1],
                             start=200, end=330, fill=highlight, width=bevel_w)

    return canvas


def _draw_iso_baseplate_tile(
    draw: ImageDraw.ImageDraw,
    r0: int, r1: int, c0: int, c1: int,
    origin_x: float, origin_y: float,
    u_x: float, u_y: float, z_px: float,
    is_active_bp: bool = False
):
    """
    Draws an individual isolated baseplate module [r0..r1, c0..c1] in 3D isometric space,
    highlighting the rim in gold if it is the new baseplate currently being built/attached.
    """
    def proj(row: float, col: float, layer_z: float) -> tuple[float, float]:
        return (origin_x + (col - row) * u_x, origin_y + (col + row) * u_y - layer_z * z_px)

    top_col = (114, 118, 124) if is_active_bp else (96, 100, 106)
    left_col = (82, 86, 90)
    right_col = (64, 68, 72)
    edge_col = (245, 178, 36) if is_active_bp else (46, 50, 56)

    p_top = proj(r0, c0, 0.0)
    p_right = proj(r0, c1, 0.0)
    p_front = proj(r1, c1, 0.0)
    p_left = proj(r1, c0, 0.0)
    p_left_bot = proj(r1, c0, -0.5)
    p_front_bot = proj(r1, c1, -0.5)
    p_right_bot = proj(r0, c1, -0.5)

    draw.polygon([p_left, p_front, p_front_bot, p_left_bot], fill=left_col, outline=edge_col)
    draw.polygon([p_front, p_right, p_right_bot, p_front_bot], fill=right_col, outline=edge_col)
    draw.polygon([p_top, p_right, p_front, p_left], fill=top_col, outline=edge_col)

    grid_line_col = (100, 104, 110) if is_active_bp else (86, 90, 96)
    for r in range(r0 + 1, r1):
        draw.line([proj(r, c0, 0.0), proj(r, c1, 0.0)], fill=grid_line_col, width=1)
    for c in range(c0 + 1, c1):
        draw.line([proj(r0, c, 0.0), proj(r1, c, 0.0)], fill=grid_line_col, width=1)

    if u_x >= 4.2:
        srx = max(1.4, u_x * 0.28)
        sry = max(0.8, u_y * 0.28)
        for r in range(r0, r1):
            for c in range(c0, c1):
                sx, sy = proj(r + 0.5, c + 0.5, 0.0)
                draw.ellipse([sx - srx, sy - sry, sx + srx, sy + sry], outline=(88, 92, 98))

    if is_active_bp:
        draw.line([p_top, p_right, p_front, p_left, p_top], fill=(245, 178, 36), width=2)


def _draw_iso_brick(
    draw: ImageDraw.ImageDraw,
    r: float, c: float, h: float, w: float, z: int,
    color_rgb: tuple[int, int, int],
    is_stud: bool,
    origin_x: float, origin_y: float,
    u_x: float, u_y: float, z_px: float,
    is_new_step: bool = False,
    z_span: int = 1,
    shape: str = "rect",
    orient: str | None = None
):
    def proj(row: float, col: float, layer_z: float) -> tuple[float, float]:
        return (origin_x + (col - row) * u_x, origin_y + (col + row) * u_y - layer_z * z_px)

    top_col = color_rgb
    left_col = clamp_rgb(color_rgb, -24)
    right_col = clamp_rgb(color_rgb, -44)
    slope_col = clamp_rgb(color_rgb, -12)
    outline_col = (224, 36, 36) if is_new_step else (42, 46, 52)
    stud_outline = (55, 60, 66)

    z_top = float(z)
    z_bot = float(z - z_span)

    if shape in ("slope", "slope_curved"):
        z_N = z_bot + 0.25 if orient == "N" else z_top
        z_S = z_bot + 0.25 if orient == "S" else z_top
        z_W = z_bot + 0.25 if orient == "W" else z_top
        z_E = z_bot + 0.25 if orient == "E" else z_top

        p_top = proj(r, c, min(z_N, z_W))
        p_right = proj(r, c + w, min(z_N, z_E))
        p_front = proj(r + h, c + w, min(z_S, z_E))
        p_left = proj(r + h, c, min(z_S, z_W))

        p_left_bot = proj(r + h, c, z_bot)
        p_front_bot = proj(r + h, c + w, z_bot)
        p_right_bot = proj(r, c + w, z_bot)

        draw.polygon([p_left, p_front, p_front_bot, p_left_bot], fill=left_col, outline=outline_col)
        draw.polygon([p_front, p_right, p_right_bot, p_front_bot], fill=right_col, outline=outline_col)
        draw.polygon([p_top, p_right, p_front, p_left], fill=slope_col, outline=outline_col)
        if is_new_step:
            draw.line([p_top, p_right, p_front, p_left, p_top], fill=(224, 36, 36), width=2)
        return

    if shape in ("tri_2x2", "wedge_2x2"):
        c_tl = proj(r, c, z_top)
        c_tr = proj(r, c + w, z_top)
        c_br = proj(r + h, c + w, z_top)
        c_bl = proj(r + h, c, z_top)
        if orient == "TL":
            tri_pts = [c_tl, c_tr, c_bl]
        elif orient == "TR":
            tri_pts = [c_tl, c_tr, c_br]
        elif orient == "BL":
            tri_pts = [c_tl, c_br, c_bl]
        else:
            tri_pts = [c_tr, c_br, c_bl]
        draw.polygon(tri_pts, fill=top_col, outline=outline_col)
        if is_new_step:
            draw.line(tri_pts + [tri_pts[0]], fill=(224, 36, 36), width=2)
        return

    p_top = proj(r, c, z_top)
    p_right = proj(r, c + w, z_top)
    p_front = proj(r + h, c + w, z_top)
    p_left = proj(r + h, c, z_top)

    p_left_bot = proj(r + h, c, z_bot)
    p_front_bot = proj(r + h, c + w, z_bot)
    p_right_bot = proj(r, c + w, z_bot)

    draw.polygon([p_left, p_front, p_front_bot, p_left_bot], fill=left_col, outline=outline_col)
    draw.polygon([p_front, p_right, p_right_bot, p_front_bot], fill=right_col, outline=outline_col)
    draw.polygon([p_top, p_right, p_front, p_left], fill=top_col, outline=outline_col)

    if is_new_step:
        draw.line([p_top, p_right, p_front, p_left, p_top], fill=(224, 36, 36), width=2)

    if is_stud and u_x >= 3.6:
        stud_rx = max(1.6, u_x * 0.32)
        stud_ry = max(0.9, u_y * 0.32)
        stud_h = max(1.0, z_px * 0.34)
        for sr in range(int(h)):
            for sc in range(int(w)):
                sx, sy = proj(r + sr + 0.5, c + sc + 0.5, z_top)
                draw.rectangle([sx - stud_rx, sy - stud_h, sx + stud_rx, sy], fill=left_col, outline=stud_outline)
                draw.ellipse([sx - stud_rx, sy - stud_ry, sx + stud_rx, sy + stud_ry], fill=left_col, outline=stud_outline)
                draw.ellipse(
                    [sx - stud_rx, sy - stud_h - stud_ry, sx + stud_rx, sy - stud_h + stud_ry],
                    fill=top_col,
                    outline=stud_outline
                )


def _get_manual_font(size: int = 16):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _compute_iso_viewport_transform(
    min_r: int, max_r: int, min_c: int, max_c: int, max_z: int,
    vp_x0: float, vp_y0: float, vp_x1: float, vp_y1: float,
    max_ux: float = 13.5
) -> tuple[float, float, float, float, float]:
    """
    Computes (origin_x, origin_y, u_x, u_y, z_px) so any isolated baseplate [min_r..max_r, min_c..max_c]
    or group of baseplates fills its viewport rectangle cleanly and centered.
    """
    span_units = max(12, (max_c - min_c) + (max_r - min_r))
    vp_w = max(80.0, vp_x1 - vp_x0)
    vp_h = max(80.0, vp_y1 - vp_y0)

    u_x = min(max_ux, max(3.8, min((vp_w * 0.88) / span_units, (vp_h * 0.82) / (span_units * 0.52))))
    u_y = u_x * 0.50
    z_px = u_x * 0.42

    mid_iso_x = ((min_c - max_r) + (max_c - min_r)) * 0.5 * u_x
    mid_iso_y = ((min_c + min_r) + (max_c + max_r)) * 0.5 * u_y - (max_z * 0.35) * z_px

    origin_x = (vp_x0 + vp_x1) * 0.5 - mid_iso_x
    origin_y = (vp_y0 + vp_y1) * 0.5 - mid_iso_y
    return origin_x, origin_y, u_x, u_y, z_px


def generate_isometric_manual(
    surface_placements: list[dict],
    under_placements: list[dict],
    palette_keys: list[tuple[int, str]],
    palette_rgb: np.ndarray,
    grid_size: tuple[int, int],
    output_manual_path: str
) -> str:
    """
    Baseplate-Isolated Progressive Isometric Manual:
    - Isolates physical baseplates based on grid_size (e.g. 4x 32x32 baseplates for 64x64).
    - Builds 1 baseplate at a time (Z=1 -> Z=2 -> Z=3, capped at <=55 pieces per step):
      * Baseplate 1 Steps: Shows Baseplate 1 isolated at massive 2.5x zoom.
      * Baseplate 2+ Steps: Shows the isolated active baseplate at 2.5x zoom on the main stage
        PLUS the progressive multi-baseplate assembly (Baseplate 1 + Baseplate 2, then 1 + 2 + 3, etc.)
        so builders see both every individual brick clearly and how the baseplates connect!
    """
    h, w = grid_size
    bp_h, bp_w = get_baseplate_module_size(grid_size)
    bp_rows = (h + bp_h - 1) // bp_h
    bp_cols = (w + bp_w - 1) // bp_w

    all_placements = under_placements + surface_placements
    max_z = max((p.get("z", 1) for p in all_placements), default=1)

    font_qty = _get_manual_font(20)
    font_step = _get_manual_font(30)
    font_small = _get_manual_font(13)

    # Order baseplates in natural assembly sequence: (0,0) -> (0,1) -> (1,0) -> (1,1)...
    bp_coords = [(br, bc) for br in range(bp_rows) for bc in range(bp_cols)]

    # Build steps baseplate-by-baseplate, then layer-by-layer (capped at <= 55 pieces per step)
    MAX_PCS_PER_STEP = 55
    steps = []
    global_accumulated: list[dict] = []
    introduced_bps: list[tuple[int, int]] = []
    step_num = 0

    for bp_idx, (br, bc) in enumerate(bp_coords, start=1):
        r0, r1 = br * bp_h, min(h, (br + 1) * bp_h)
        c0, c1 = bc * bp_w, min(w, (bc + 1) * bp_w)

        bp_pcs = [
            p for p in all_placements
            if r0 <= p["r"] < r1 and c0 <= p["c"] < c1
        ]
        if not bp_pcs:
            continue

        introduced_bps.append((br, bc))
        bp_prior_pcs: list[dict] = []

        for lz in range(1, max_z + 1):
            layer_bp_pcs = [p for p in bp_pcs if p.get("z", 1) == lz]
            if not layer_bp_pcs:
                continue

            # Sort structural plates first, then back-to-front along isometric diagonal
            layer_bp_pcs.sort(key=lambda p: (0 if p.get("is_structural", False) else 1, p["r"] + p["c"], p["r"], p["c"]))

            num_chunks = max(1, (len(layer_bp_pcs) + MAX_PCS_PER_STEP - 1) // MAX_PCS_PER_STEP)
            chunk_sz = max(1, (len(layer_bp_pcs) + num_chunks - 1) // num_chunks)

            for s_i in range(0, len(layer_bp_pcs), chunk_sz):
                batch = layer_bp_pcs[s_i:s_i + chunk_sz]
                step_num += 1
                steps.append({
                    "step_num": step_num,
                    "bp_idx": bp_idx,
                    "bp_coord": (br, bc),
                    "bp_bounds": (r0, r1, c0, c1),
                    "introduced_bps": list(introduced_bps),
                    "bp_prior_pcs": list(bp_prior_pcs),
                    "global_prior_pcs": list(global_accumulated),
                    "active_pcs": batch,
                })
                bp_prior_pcs.extend(batch)
                global_accumulated.extend(batch)

    cols = 2
    rows = (len(steps) + cols - 1) // cols
    panel_w = 1120
    panel_h = 580
    page_w = panel_w * cols
    iso_section_h = panel_h * rows
    map_section_h = 1240
    page_h = iso_section_h + map_section_h

    manual = Image.new("RGB", (page_w, page_h), (228, 240, 248))
    draw = ImageDraw.Draw(manual)

    for idx, st in enumerate(steps):
        step_num = st["step_num"]
        br, bc = st["bp_coord"]
        r0, r1, c0, c1 = st["bp_bounds"]
        intro_bps = st["introduced_bps"]
        bp_prior = st["bp_prior_pcs"]
        global_prior = st["global_prior_pcs"]
        active_pcs = st["active_pcs"]

        row_idx = idx // cols
        col_idx = idx % cols
        px0 = col_idx * panel_w
        py0 = row_idx * panel_h
        px1 = px0 + panel_w
        py1 = py0 + panel_h

        draw.rectangle([px0, py0, px1, py1], fill=(228, 240, 248), outline=(255, 255, 255), width=4)

        # 1. Left Parts Callout Box (Wordless: '1x', '2x' quantities only)
        box_x0, box_y0 = px0 + 22, py0 + 22
        box_x1, box_y1 = px0 + 308, py0 + 480
        draw.rounded_rectangle(
            [box_x0, box_y0, box_x1, box_y1],
            radius=10,
            fill=(245, 248, 252),
            outline=(176, 196, 214),
            width=2
        )

        # Step number below the callout box
        draw.text((box_x0 + 8, box_y1 + 16), f"{step_num}", fill=(25, 32, 42), font=font_step)

        # Wordless Mini Baseplate Quadrant Locator Icon (bottom-left next to step number)
        if bp_rows > 1 or bp_cols > 1:
            loc_cell = 14
            loc_x0 = box_x0 + 86
            loc_y0 = box_y1 + 14
            for mr in range(bp_rows):
                for mc in range(bp_cols):
                    mx0 = loc_x0 + mc * (loc_cell + 3)
                    my0 = loc_y0 + mr * (loc_cell + 3)
                    if mr == br and mc == bc:
                        fill_c = (245, 178, 36)
                        out_c = (180, 110, 10)
                    elif (mr, mc) in intro_bps:
                        fill_c = (140, 155, 170)
                        out_c = (85, 95, 108)
                    else:
                        fill_c = (220, 228, 236)
                        out_c = (170, 182, 194)
                    draw.rectangle([mx0, my0, mx0 + loc_cell, my0 + loc_cell], fill=fill_c, outline=out_c, width=1)

        step_counts = Counter(
            (p["color_idx"], p["part_key"], p["h"], p["w"], p["is_stud"], p.get("z_span", 1), p.get("shape", "rect"))
            for p in active_pcs
        )
        top_step_parts = step_counts.most_common(10)

        for p_idx, ((c_idx, p_key, ph, pw, is_st, z_sp, shp), qty) in enumerate(top_step_parts):
            rgb = tuple(int(v) for v in palette_rgb[c_idx])
            p_col = p_idx % 2
            p_row = p_idx // 2

            cell_x = box_x0 + 16 + p_col * 136
            cell_y = box_y0 + 24 + p_row * 86

            _draw_iso_brick(
                draw, r=0, c=0, h=min(2, ph), w=min(3, pw), z=z_sp,
                color_rgb=rgb, is_stud=is_st,
                origin_x=cell_x + 28, origin_y=cell_y + 12 + (6 if z_sp > 1 else 0),
                u_x=8.2, u_y=4.1, z_px=3.5,
                is_new_step=False,
                z_span=z_sp,
                shape=shp,
                orient="TL" if shp in ("tri_2x2", "wedge_2x2") else "N"
            )
            draw.text((cell_x + 70, cell_y + 8), f"{qty}x", fill=(20, 24, 30), font=font_qty)

        # 2. Main Stage: Isolated Active Baseplate at 2.5x Zoom
        has_assembly_inset = len(intro_bps) > 1
        main_vp_x0 = px0 + 324
        main_vp_y0 = py0 + 24
        main_vp_x1 = (px1 - 270) if has_assembly_inset else (px1 - 24)
        main_vp_y1 = py1 - 24

        iso_ox, iso_oy, u_x, u_y, z_px = _compute_iso_viewport_transform(
            r0, r1, c0, c1, max_z,
            main_vp_x0, main_vp_y0, main_vp_x1, main_vp_y1,
            max_ux=13.5
        )

        _draw_iso_baseplate_tile(
            draw, r0, r1, c0, c1,
            iso_ox, iso_oy, u_x, u_y, z_px,
            is_active_bp=True
        )

        combined_bp = [(False, p) for p in bp_prior] + [(True, p) for p in active_pcs]
        combined_bp.sort(
            key=lambda item: (
                item[1].get("z", 1),
                item[1]["r"] + item[1]["c"],
                item[1]["r"],
                item[1]["c"]
            )
        )

        for is_new, p in combined_bp:
            rgb = tuple(int(v) for v in palette_rgb[p["color_idx"]])
            _draw_iso_brick(
                draw,
                r=p["r"], c=p["c"], h=p["h"], w=p["w"], z=p.get("z", 1),
                color_rgb=rgb,
                is_stud=p["is_stud"],
                origin_x=iso_ox, origin_y=iso_oy,
                u_x=u_x, u_y=u_y, z_px=z_px,
                is_new_step=is_new,
                z_span=p.get("z_span", 1),
                shape=p.get("shape", "rect"),
                orient=p.get("orient")
            )

        # 3. Progressive Multi-Baseplate Assembly View (Baseplate 1 + 2, then 1 + 2 + 3...)
        if has_assembly_inset:
            ins_x0, ins_y0 = px1 - 258, py0 + 24
            ins_x1, ins_y1 = px1 - 20, py1 - 24
            draw.rounded_rectangle(
                [ins_x0, ins_y0, ins_x1, ins_y1],
                radius=10,
                fill=(236, 244, 250),
                outline=(176, 196, 214),
                width=2
            )

            min_ir = min(ibr * bp_h for ibr, _ in intro_bps)
            max_ir = max(min(h, (ibr + 1) * bp_h) for ibr, _ in intro_bps)
            min_ic = min(ibc * bp_w for _, ibc in intro_bps)
            max_ic = max(min(w, (ibc + 1) * bp_w) for _, ibc in intro_bps)

            a_ox, a_oy, a_ux, a_uy, a_zpx = _compute_iso_viewport_transform(
                min_ir, max_ir, min_ic, max_ic, max_z,
                ins_x0 + 10, ins_y0 + 16, ins_x1 - 10, ins_y1 - 16,
                max_ux=6.2
            )

            # Draw only the baseplates introduced so far ( highlighting the current one in gold )
            for ibr, ibc in sorted(intro_bps, key=lambda item: (item[0] + item[1], item[0], item[1])):
                ir0, ir1 = ibr * bp_h, min(h, (ibr + 1) * bp_h)
                ic0, ic1 = ibc * bp_w, min(w, (ibc + 1) * bp_w)
                _draw_iso_baseplate_tile(
                    draw, ir0, ir1, ic0, ic1,
                    a_ox, a_oy, a_ux, a_uy, a_zpx,
                    is_active_bp=(ibr == br and ibc == bc)
                )

            combined_global = [(False, p) for p in global_prior] + [(True, p) for p in active_pcs]
            combined_global.sort(
                key=lambda item: (
                    item[1].get("z", 1),
                    item[1]["r"] + item[1]["c"],
                    item[1]["r"],
                    item[1]["c"]
                )
            )
            for is_new, p in combined_global:
                rgb = tuple(int(v) for v in palette_rgb[p["color_idx"]])
                _draw_iso_brick(
                    draw,
                    r=p["r"], c=p["c"], h=p["h"], w=p["w"], z=p.get("z", 1),
                    color_rgb=rgb,
                    is_stud=p["is_stud"],
                    origin_x=a_ox, origin_y=a_oy,
                    u_x=a_ux, u_y=a_uy, z_px=a_zpx,
                    is_new_step=is_new,
                    z_span=p.get("z_span", 1),
                    shape=p.get("shape", "rect"),
                    orient=p.get("orient")
                )

    # Bottom Section: 2D Color Key & Full Baseplate-Divided Quadrant Map
    map_y0 = iso_section_h
    draw.rectangle([0, map_y0, page_w, page_h], fill=(238, 245, 250), outline=(255, 255, 255), width=4)

    color_usage = Counter(p["color_idx"] for p in surface_placements)
    color_num_map: dict[int, int] = {}
    for rank_idx, (c_idx, _) in enumerate(color_usage.most_common(), start=1):
        color_num_map[c_idx] = rank_idx

    leg_x0, leg_y0 = 24, map_y0 + 36
    leg_x1, leg_y1 = 440, page_h - 24
    draw.rounded_rectangle(
        [leg_x0, leg_y0, leg_x1, leg_y1],
        radius=12,
        fill=(255, 255, 255),
        outline=(176, 196, 214),
        width=2
    )

    used_colors_sorted = color_usage.most_common()
    for idx_c, (c_idx, pcs_count) in enumerate(used_colors_sorted[:32]):
        key_num = color_num_map[c_idx]
        rgb = tuple(int(v) for v in palette_rgb[c_idx])
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        txt_col = (20, 24, 30) if lum > 140 else (255, 255, 255)

        sub_col = idx_c // 16
        sub_row = idx_c % 16
        sx = leg_x0 + 24 + sub_col * 195
        sy = leg_y0 + 24 + sub_row * 68

        draw.rounded_rectangle([sx, sy, sx + 44, sy + 44], radius=6, fill=rgb, outline=(60, 70, 80), width=2)
        num_str = str(key_num)
        draw.text((sx + (16 if len(num_str) == 1 else 11), sy + 11), num_str, fill=txt_col, font=font_qty)
        draw.text((sx + 56, sy + 11), f"{pcs_count}x", fill=(25, 32, 40), font=font_qty)

    grid_area_x0 = 480
    grid_area_y0 = map_y0 + 56
    max_grid_px = 1120
    cell_px = max(8, min(max_grid_px // max(h, w), 34))
    grid_w_px = w * cell_px
    grid_h_px = h * cell_px

    gx0 = grid_area_x0 + ((page_w - grid_area_x0 - 40) - grid_w_px) // 2
    gy0 = grid_area_y0 + (1120 - grid_h_px) // 2

    draw.rectangle(
        [gx0 - 36, gy0 - 36, gx0 + grid_w_px + 16, gy0 + grid_h_px + 16],
        fill=(255, 255, 255),
        outline=(160, 180, 200),
        width=2
    )

    coord_step = 1 if max(h, w) <= 32 else (2 if max(h, w) <= 64 else 4)
    for c in range(0, w, coord_step):
        cx = gx0 + c * cell_px + cell_px // 4
        draw.text((cx, gy0 - 22), str(c + 1), fill=(70, 85, 100), font=font_small)
    for r in range(0, h, coord_step):
        ry = gy0 + r * cell_px + cell_px // 4
        draw.text((gx0 - 28, ry), str(r + 1), fill=(70, 85, 100), font=font_small)

    for p in surface_placements:
        r, c, ph, pw = p["r"], p["c"], p["h"], p["w"]
        c_idx = p["color_idx"]
        key_num = color_num_map.get(c_idx, 1)
        rgb = tuple(int(v) for v in palette_rgb[c_idx])
        bg_rgb = tuple(int(v) for v in palette_rgb[p["bg_color_idx"]])
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        txt_col = (15, 20, 25) if lum > 140 else (250, 252, 255)
        seam_col = (30, 35, 42)

        x0 = gx0 + c * cell_px
        y0 = gy0 + r * cell_px
        x1 = x0 + pw * cell_px
        y1 = y0 + ph * cell_px

        if p["shape"] == "qtr_1x1":
            draw_quarter_tile(draw, x0, y0, x1, y1, rgb, bg_rgb, p["orient"], seam_col)
        elif p["shape"] in ("tri_2x2", "wedge_2x2"):
            draw_triangular_2x2(
                draw, x0, y0, x1, y1,
                rgb, bg_rgb, p["orient"] or "TL",
                seam_col, clamp_rgb(rgb, 24), clamp_rgb(rgb, -24), 1
            )
        elif p["shape"] in ("slope", "slope_curved"):
            draw_slope_piece(
                draw, x0, y0, x1, y1,
                rgb, p["orient"] or "N",
                seam_col, is_curved=(p["shape"] == "slope_curved")
            )
        elif p["shape"] in ("round_1x1", "round_2x2"):
            draw.rectangle([x0, y0, x1, y1], fill=(35, 42, 50), outline=(70, 80, 90), width=1)
            pad = max(1, cell_px // 8)
            draw.ellipse([x0 + pad, y0 + pad, x1 - pad, y1 - pad], fill=rgb, outline=seam_col, width=2)
        else:
            draw.rectangle([x0, y0, x1, y1], fill=rgb, outline=seam_col, width=2)

        if p["is_stud"] and cell_px >= 12:
            s_pad = max(2, cell_px // 4)
            ring_col = clamp_rgb(rgb, -32 if lum > 140 else 32)
            for sr in range(ph):
                for sc in range(pw):
                    sx0 = x0 + sc * cell_px + s_pad
                    sy0 = y0 + sr * cell_px + s_pad
                    sx1 = x0 + (sc + 1) * cell_px - s_pad
                    sy1 = y0 + (sr + 1) * cell_px - s_pad
                    draw.ellipse([sx0, sy0, sx1, sy1], outline=ring_col, width=1)

        label_str = str(key_num)
        tx = (x0 + x1) // 2 - (4 * len(label_str))
        ty = (y0 + y1) // 2 - 6
        draw.text((tx, ty), label_str, fill=txt_col, font=font_small)

    # Draw Baseplate Module Seams in bold gold/red
    quad_line_col = (220, 38, 38)
    for r_q in range(bp_h, h, bp_h):
        qy = gy0 + r_q * cell_px
        draw.line([(gx0, qy), (gx0 + grid_w_px, qy)], fill=quad_line_col, width=3)
    for c_q in range(bp_w, w, bp_w):
        qx = gx0 + c_q * cell_px
        draw.line([(qx, gy0), (qx, gy0 + grid_h_px)], fill=quad_line_col, width=3)

    draw.rectangle([gx0, gy0, gx0 + grid_w_px, gy0 + grid_h_px], outline=(20, 28, 36), width=3)

    manual.save(output_manual_path, format="PNG")
    return output_manual_path


def delta_e_ciede2000_numpy(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    C_bar = 0.5 * (C1 + C2)

    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - np.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))

    a1_p = (1.0 + G) * a1
    a2_p = (1.0 + G) * a2
    C1_p = np.hypot(a1_p, b1)
    C2_p = np.hypot(a2_p, b2)

    h1_p = np.degrees(np.arctan2(b1, a1_p)) % 360.0
    h2_p = np.degrees(np.arctan2(b2, a2_p)) % 360.0

    dL_p = L2 - L1
    dC_p = C2_p - C1_p

    dh_p = h2_p - h1_p
    dh_p = np.where(dh_p > 180.0, dh_p - 360.0, dh_p)
    dh_p = np.where(dh_p < -180.0, dh_p + 360.0, dh_p)
    dh_p = np.where((C1_p * C2_p) == 0.0, 0.0, dh_p)
    dH_p = 2.0 * np.sqrt(C1_p * C2_p) * np.sin(np.radians(0.5 * dh_p))

    L_bar_p = 0.5 * (L1 + L2)
    C_bar_p = 0.5 * (C1_p + C2_p)

    h_sum = h1_p + h2_p
    h_diff = np.abs(h1_p - h2_p)
    h_bar_p = np.where(
        (C1_p * C2_p) == 0.0,
        h_sum,
        np.where(h_diff <= 180.0, 0.5 * h_sum, np.where(h_sum < 360.0, 0.5 * (h_sum + 360.0), 0.5 * (h_sum - 360.0)))
    )

    T = (
        1.0
        - 0.17 * np.cos(np.radians(h_bar_p - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * h_bar_p))
        + 0.32 * np.cos(np.radians(3.0 * h_bar_p + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * h_bar_p - 63.0))
    )

    d_theta = 30.0 * np.exp(-(((h_bar_p - 275.0) / 25.0) ** 2))
    C_bar_p7 = C_bar_p ** 7
    R_C = 2.0 * np.sqrt(C_bar_p7 / (C_bar_p7 + 25.0 ** 7))

    L_diff_sq = (L_bar_p - 50.0) ** 2
    S_L = 1.0 + (0.015 * L_diff_sq) / np.sqrt(20.0 + L_diff_sq)
    S_C = 1.0 + 0.045 * C_bar_p
    S_H = 1.0 + 0.015 * C_bar_p * T
    R_T = -np.sin(np.radians(2.0 * d_theta)) * R_C

    term_L = dL_p / S_L
    term_C = dC_p / S_C
    term_H = dH_p / S_H

    return np.sqrt(term_L ** 2 + term_C ** 2 + term_H ** 2 + R_T * term_C * term_H)


def generate_brick_mosaic(
    input_path: str,
    output_path: str,
    grid_size: tuple[int, int] | None = None,
    target_output_px: int = 2400,
    palette: dict = BRICK_PALETTE,
    stud_ratio: float = 0.45,
    merge_tolerance_de: float = 2.2,
    pre_sharpen: bool = False,
    z_layers: int = 1,
    z_mode: str = "luminance",
    abstract_mode: bool = False,
    manual_output_path: str | None = None
) -> tuple[dict, tuple[int, int], int]:
    img = Image.open(input_path).convert("RGB")
    img_cropped = center_crop_square(img)

    if img_cropped.width > 512:
        img_cropped = img_cropped.resize((512, 512), Image.Resampling.BILINEAR)

    palette_keys = list(palette.keys())
    palette_rgb = np.array(list(palette.values()), dtype=np.uint8)
    palette_rgb_norm = (palette_rgb.astype(np.float32) / 255.0)[np.newaxis, :, :]
    palette_lab = rgb2lab_numpy(palette_rgb_norm)[0]

    fg_mask_grid = None
    bg_palette_idx = 0

    if abstract_mode:
        if grid_size is None or grid_size[0] > 48:
            grid_size = (32, 32)
        img_cropped, fg_mask_256, bg_palette_idx = filter_background_and_abstract_subject(
            img_cropped, palette_keys
        )
        fg_mask_img = Image.fromarray((fg_mask_256.astype(np.uint8) * 255), mode="L").resize(
            grid_size, Image.Resampling.NEAREST
        )
        fg_mask_grid = np.asarray(fg_mask_img) > 127
        merge_tolerance_de = max(merge_tolerance_de, 5.5)
    else:
        if grid_size is None:
            grid_size = auto_detect_grid_size(img_cropped)
        if z_layers > 1:
            neural_mask_256 = extract_neural_foreground_mask(img_cropped)
            if neural_mask_256 is not None:
                fg_mask_img = Image.fromarray((neural_mask_256.astype(np.uint8) * 255), mode="L").resize(
                    grid_size, Image.Resampling.NEAREST
                )
                fg_mask_grid = np.asarray(fg_mask_img) > 127

    groove_mask, dark_sub_rgb = detect_boxed_grooves_and_preserve_lines(img_cropped, grid_size)

    if pre_sharpen and not abstract_mode:
        img_cropped = img_cropped.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=4))

    img_small = img_cropped.resize(grid_size, Image.Resampling.LANCZOS)
    sub_grid_size = (grid_size[0] * 2, grid_size[1] * 2)
    img_sub = img_cropped.resize(sub_grid_size, Image.Resampling.LANCZOS)

    img_rgb_norm = np.asarray(img_small, dtype=np.float32) / 255.0
    img_lab = rgb2lab_numpy(img_rgb_norm)

    sub_rgb_norm = np.asarray(img_sub, dtype=np.float32) / 255.0
    subpixel_lab = rgb2lab_numpy(sub_rgb_norm)

    delta_e = delta_e_ciede2000_numpy(
        img_lab[:, :, np.newaxis, :],
        palette_lab[np.newaxis, np.newaxis, :, :]
    )
    raw_indices = np.argmin(delta_e, axis=-1)

    dark_sub_lab = rgb2lab_numpy(dark_sub_rgb)
    dark_de = delta_e_ciede2000_numpy(
        dark_sub_lab[:, :, np.newaxis, :],
        palette_lab[np.newaxis, np.newaxis, :, :]
    )
    surface_L = palette_lab[raw_indices, 0][..., np.newaxis]
    cand_L = palette_lab[np.newaxis, np.newaxis, :, 0]
    not_darker_penalty = np.where(cand_L > (surface_L - 12.0), 100.0, 0.0)
    dark_indices = np.argmin(dark_de + not_darker_penalty, axis=-1)
    raw_indices = np.where(groove_mask, dark_indices, raw_indices)

    if abstract_mode and fg_mask_grid is not None:
        raw_indices = np.where(fg_mask_grid, raw_indices, bg_palette_idx)
        subj_pixels = raw_indices[fg_mask_grid]
        if len(subj_pixels) > 0:
            dominant_colors = [c for c, _ in Counter(subj_pixels.tolist()).most_common(7)]
            if bg_palette_idx not in dominant_colors:
                dominant_colors.append(bg_palette_idx)
            allowed = np.array(dominant_colors, dtype=np.int32)
            restricted_de = delta_e[:, :, allowed]
            snapped = allowed[np.argmin(restricted_de, axis=-1)]
            raw_indices = np.where(fg_mask_grid, snapped, bg_palette_idx)

        black_idx = next((i for i, (cid, _) in enumerate(palette_keys) if cid == 11), 0)
        raw_indices[0, :] = black_idx
        raw_indices[-1, :] = black_idx
        raw_indices[:, 0] = black_idx
        raw_indices[:, -1] = black_idx

    edge_map = sobel_edges_numpy(img_rgb_norm)
    edge_map = np.where(groove_mask, np.max(edge_map) + 1.0, edge_map)
    nearest_indices = denoise_and_smooth_grid(
        raw_indices, delta_e, edge_map, merge_tolerance_de=merge_tolerance_de
    )

    effective_z = max(2, z_layers) if abstract_mode else z_layers

    z_grid = compute_stable_terrace_z_grid(
        img_lab=img_lab,
        edge_map=edge_map,
        grid_size=grid_size,
        z_layers=effective_z,
        z_mode=z_mode,
        fg_mask_grid=fg_mask_grid,
        groove_mask=groove_mask,
    )

    if effective_z > 1:
        stud_mask = (z_grid == np.max(z_grid)) & (z_grid > 1) & (~groove_mask)
        bg_mask = (z_grid == 1) & (~groove_mask)
        if np.any(bg_mask):
            dominant_bg_col = Counter(nearest_indices[bg_mask].tolist()).most_common(1)[0][0]
            nearest_indices = np.where(bg_mask, dominant_bg_col, nearest_indices)
    else:
        threshold = np.quantile(edge_map, 1.0 - stud_ratio)
        stud_mask = (edge_map >= threshold) & (~groove_mask)

    if abstract_mode and fg_mask_grid is not None:
        stud_mask = stud_mask & fg_mask_grid
        stud_mask[0, :] = False
        stud_mask[-1, :] = False
        stud_mask[:, 0] = False
        stud_mask[:, -1] = False

    surface_placements, under_placements = build_interlocking_layers(
        nearest_indices=nearest_indices,
        stud_mask=stud_mask,
        edge_map=edge_map,
        subpixel_lab=subpixel_lab,
        palette_lab=palette_lab,
        palette_keys=palette_keys,
        z_grid=z_grid,
        groove_mask=groove_mask,
    )

    mosaic_img = render_mixed_mosaic(surface_placements, palette_rgb, grid_size, target_output_px=target_output_px)
    mosaic_img.save(output_path, format="PNG")

    if manual_output_path is None:
        manual_output_path = output_path.replace("_hd.png", "_manual.png")
        if manual_output_path == output_path:
            manual_output_path = output_path + "_manual.png"

    generate_isometric_manual(
        surface_placements=surface_placements,
        under_placements=under_placements,
        palette_keys=palette_keys,
        palette_rgb=palette_rgb,
        grid_size=grid_size,
        output_manual_path=manual_output_path,
    )

    counts = Counter()
    for p in surface_placements:
        counts[(p["color_idx"], p["part_key"])] += 1
    for u in under_placements:
        counts[(u["color_idx"], u["part_key"])] += 1

    bom = {}
    for (color_idx, part_key), count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        color_id, color_name = palette_keys[color_idx]
        part_id, part_name = PART_CATALOG[part_key]
        bom[(color_id, color_name, part_id, part_name)] = count

    total_studs = int(np.sum(z_grid))
    return bom, grid_size, total_studs


def export_bricklink_xml(
    bom: dict,
    xml_output_path: str,
    grid_size: tuple[int, int] | None = None,
    include_baseplates: bool = True,
    baseplate_color_id: int = 85,
    condition: str = "N"
) -> str:
    lines = ["<INVENTORY>"]

    if include_baseplates and grid_size is not None:
        h, w = grid_size
        if h % 48 == 0 and w % 48 == 0:
            bp_id = "4186"
            bp_qty = (h // 48) * (w // 48)
            bp_color = baseplate_color_id
        elif h % 32 == 0 and w % 32 == 0:
            bp_id = "3811"
            bp_qty = (h // 32) * (w // 32)
            bp_color = 11 if baseplate_color_id == 85 else baseplate_color_id
        else:
            bp_id, bp_qty, bp_color = None, 0, None

        if bp_id and bp_qty > 0:
            lines.append("  <ITEM>")
            lines.append("    <ITEMTYPE>P</ITEMTYPE>")
            lines.append(f"    <ITEMID>{bp_id}</ITEMID>")
            lines.append(f"    <COLOR>{bp_color}</COLOR>")
            lines.append(f"    <MINQTY>{bp_qty}</MINQTY>")
            if condition:
                lines.append(f"    <CONDITION>{condition}</CONDITION>")
            lines.append("  </ITEM>")

    for (color_id, color_name, part_id, part_name), count in bom.items():
        lines.append(f"  <!-- {count}x {color_name} {part_name} -->")
        lines.append("  <ITEM>")
        lines.append("    <ITEMTYPE>P</ITEMTYPE>")
        lines.append(f"    <ITEMID>{part_id}</ITEMID>")
        lines.append(f"    <COLOR>{color_id}</COLOR>")
        lines.append(f"    <MINQTY>{count}</MINQTY>")
        if condition:
            lines.append(f"    <CONDITION>{condition}</CONDITION>")
        lines.append("  </ITEM>")

    lines.append("</INVENTORY>")
    xml_content = "\n".join(lines)

    with open(xml_output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return xml_content


def create_demo_image(output_path: str = "demo_rego.png") -> str:
    """
    Generates a crisp 512x512 studio demo image of the boxed 3D 'RE-GO' brick
    with angled corners & beveled letter cuts so 2x2 Triangular Tiles (#35787),
    Wedge Plates (#24299/#24307), and Cheese Slopes (#54200/#85984) shine.
    """
    img = Image.new("RGB", (512, 512), (242, 205, 55))
    draw = ImageDraw.Draw(img)

    red_main = (201, 26, 9)
    red_side = (145, 18, 12)
    dark_line = (55, 8, 8)

    # 1. Left shaded 3D side wall & top rim of the brick
    draw.polygon([(76, 178), (112, 196), (112, 384), (76, 362)], fill=red_side, outline=dark_line, width=4)
    draw.polygon([(76, 178), (404, 118), (440, 136), (112, 196)], fill=red_main, outline=dark_line, width=4)

    # 2. 6 raised studs along the top rim
    for i in range(6):
        sx = 122 + i * 52
        sy = 168 - i * 9
        draw.rectangle([sx - 16, sy - 12, sx + 16, sy + 4], fill=red_main, outline=dark_line, width=3)
        draw.ellipse([sx - 16, sy - 18, sx + 16, sy - 6], fill=red_main, outline=dark_line, width=3)

    # 3. Main front brick face (tilted isometric rectangle)
    draw.polygon([(112, 196), (440, 136), (440, 324), (112, 384)], fill=red_main, outline=dark_line, width=4)

    # 4. Boxed 'RE-GO' letter panels and carved internal letter grooves
    for div_x, top_y, bot_y in [(196, 181, 369), (268, 168, 355), (316, 159, 347), (380, 147, 335)]:
        draw.line([(div_x, top_y), (div_x, bot_y)], fill=dark_line, width=5)

    draw.rectangle([144, 224, 170, 262], fill=red_side, outline=dark_line, width=4)
    draw.line([(156, 292), (156, 374)], fill=dark_line, width=6)

    draw.line([(224, 222), (266, 214)], fill=dark_line, width=6)
    draw.line([(224, 278), (266, 270)], fill=dark_line, width=6)

    draw.polygon([(276, 254), (308, 248), (308, 276), (276, 282)], fill=red_main, outline=dark_line, width=5)

    draw.rectangle([338, 196, 360, 304], fill=red_side, outline=dark_line, width=4)
    draw.line([(350, 248), (378, 244)], fill=dark_line, width=5)

    draw.rectangle([400, 184, 422, 294], fill=red_side, outline=dark_line, width=4)

    img.save(output_path, format="PNG")
    return output_path
if __name__ == "__main__":
    demo_path = create_demo_image("demo_rego.png")
    print("Running Baseplate-Isolated Manual + Sculpted Slope 3D Test on Demo Image...")
    bom, grid, studs = generate_brick_mosaic(
        input_path=demo_path,
        output_path="test_3d_hd.png",
        grid_size=(64, 64),
        z_layers=3,
        manual_output_path="test_3d_manual.png",
    )
    total_pcs = sum(bom.values())
    saved_pct = (1.0 - total_pcs / max(1, studs)) * 100.0
    print(f"Done! Grid: {grid} | Stud Volume: {studs} | Pieces: {total_pcs} ({saved_pct:.1f}% saved)")
    print("\n--- Top Sculpted Slopes, Wedges & Tiles Used ---")
    for (cid, cname, pid, pname), qty in list(bom.items())[:12]:
        print(f"  {qty:>4}x  #{pid:<5} {cname} {pname}")
    try:
        os.startfile("test_3d_manual.png")
    except Exception:
        pass