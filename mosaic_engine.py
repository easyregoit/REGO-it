import os
import importlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
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
    # Rectangular Studded Plates
    "plate_2x4":       ("3020",  "Plate 2 x 4 (Studded)"),
    "plate_2x3":       ("3021",  "Plate 2 x 3 (Studded)"),
    "plate_2x2":       ("3022",  "Plate 2 x 2 (Studded)"),
    "plate_1x4":       ("3710",  "Plate 1 x 4 (Studded)"),
    "plate_1x3":       ("3623",  "Plate 1 x 3 (Studded)"),
    "plate_1x2":       ("3023",  "Plate 1 x 2 (Studded)"),
    "plate_1x1":       ("3024",  "Plate 1 x 1 Square (Studded)"),
    "plate_round_1x1": ("4073",  "Plate 1 x 1 Round (Studded)"),

    # Rectangular Smooth Flat Tiles (base IDs without 'b' import cleanly on BrickOwl & BrickLink)
    "tile_2x4":        ("87079", "Tile 2 x 4 (Flat)"),
    "tile_2x2":        ("3068",  "Tile 2 x 2 (Flat)"),
    "tile_1x4":        ("2431",  "Tile 1 x 4 (Flat)"),
    "tile_1x3":        ("63864", "Tile 1 x 3 (Flat)"),
    "tile_1x2":        ("3069",  "Tile 1 x 2 (Flat)"),
    "tile_1x1":        ("3070",  "Tile 1 x 1 Square (Flat)"),
    "tile_round_1x1":  ("98138", "Tile 1 x 1 Round (Flat)"),
    "tile_round_2x2":  ("14769", "Tile 2 x 2 Round (Flat)"),

    # Curved / Diagonal Accuracy Tiles
    "tile_qtr_1x1":    ("25269", "Tile 1 x 1 Quarter Circle (Curved)"),
}

# Colors (by BrickLink Color ID) where newer/specialty parts are poorly stocked or nonexistent.
# Restricting these parts to high-production colors eliminates BrickOwl "Rows with issues"!
PART_COLOR_WHITELIST = {
    # Quarter-circle tile (#25269) only in common active colors (excludes Nougat, Sand Blue, Dark Brown, Bright Green)
    "tile_qtr_1x1":    {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 48, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 150, 153, 155, 156},
    # 2x2 Round Flat Tile (#14769) only in high-availability colors
    "tile_round_2x2":  {1, 2, 3, 4, 5, 6, 7, 11, 34, 42, 59, 63, 69, 85, 86, 88, 90, 110, 150, 156},
    # 2x4 Flat Tile (#87079) & 1x3 Flat Tile (#63864) exclude Nougat (28)
    "tile_2x4":        {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "tile_1x3":        {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    # 1x1 Round Tile (#98138) & 1x1 Round Plate (#4073) exclude Nougat (28)
    "tile_round_1x1":  {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
    "plate_round_1x1": {1, 2, 3, 4, 5, 6, 7, 11, 34, 36, 42, 48, 55, 59, 63, 69, 71, 80, 85, 86, 88, 89, 90, 104, 105, 110, 120, 150, 153, 155, 156},
}


def is_part_available(part_key: str, color_id: int) -> bool:
    """Checks if a brick shape actually exists in the given official Color ID."""
    if part_key not in PART_COLOR_WHITELIST:
        # Standard 1x1, 1x2, 1x4, 2x2, 2x3, 2x4 plates and 1x1, 1x2, 2x2 tiles exist in all palette colors except Nougat (28) for some plates
        if color_id == 28 and part_key not in ("plate_1x1", "plate_1x2", "tile_1x1", "tile_1x2", "tile_2x2"):
            return False
        return True
    return color_id in PART_COLOR_WHITELIST[part_key]


def rgb2lab_numpy(rgb_norm: np.ndarray) -> np.ndarray:
    """Pure NumPy conversion from normalized sRGB [0, 1] to CIE L*a*b*."""
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
    """Pure NumPy Sobel edge detector."""
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
        chosen = (64, 64)
    elif edge_energy < 0.22:
        chosen = (96, 96)
    else:
        chosen = (128, 128)

    print(f"[Auto-Scale] Measured detail score: {edge_energy:.3f} -> Selected {chosen[0]}x{chosen[1]} stud grid.")
    return chosen


def clamp_rgb(rgb: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c) + delta)) for c in rgb)


def denoise_and_smooth_grid(
    nearest_indices: np.ndarray,
    delta_e: np.ndarray,
    edge_map: np.ndarray,
    merge_tolerance_de: float = 4.2
) -> np.ndarray:
    """
    Replaces isolated noisy single pixels with their dominant neighbor color
    IF the perceptual Delta-E penalty is small (< merge_tolerance_de) and not on a sharp feature.
    Dramatically increases how many 2x4, 2x2, 1x4, and 1x2 pieces can be combined.
    """
    smoothed = nearest_indices.copy()
    h, w = smoothed.shape
    edge_cutoff = np.quantile(edge_map, 0.75)

    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if edge_map[r, c] > edge_cutoff:
                continue  # Keep sharp eyes/outlines untouched

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
    """
    Compares a 2x2 sub-pixel block against the 4 rotations of a Quarter-Circle tile
    (TL, TR, BL, BR) to see if a curved tile is more accurate than a flat square.
    """
    # Distance of each of the 4 sub-pixels (top-left, top-right, bottom-left, bottom-right) to FG and BG
    d_fg = np.linalg.norm(sub_cell_lab - fg_lab, axis=-1)  # shape (2, 2)
    d_bg = np.linalg.norm(sub_cell_lab - bg_lab, axis=-1)  # shape (2, 2)

    solid_fg_err = float(np.sum(d_fg))

    # Each orientation leaves 1 corner exposed to background (bg) and 3 quadrants covered by the curve (fg)
    orientations = {
        "BR": d_bg[0, 0] + d_fg[0, 1] + d_fg[1, 0] + d_fg[1, 1],  # Flat corner at Bottom-Right, curve opens Top-Left
        "BL": d_fg[0, 0] + d_bg[0, 1] + d_fg[1, 0] + d_fg[1, 1],  # Exposed top-right
        "TR": d_fg[0, 0] + d_fg[0, 1] + d_bg[1, 0] + d_fg[1, 1],  # Exposed bottom-left
        "TL": d_fg[0, 0] + d_fg[0, 1] + d_fg[1, 0] + d_bg[1, 1],  # Exposed bottom-right
    }

    best_orient, best_err = min(orientations.items(), key=lambda x: x[1])
    improvement = solid_fg_err - float(best_err)
    return best_orient, improvement


# --- START OF CHANGE 2 ---
def pack_multi_shape_mosaic(
    nearest_indices: np.ndarray,
    stud_mask: np.ndarray,
    edge_map: np.ndarray,
    subpixel_lab: np.ndarray,
    palette_lab: np.ndarray,
    palette_keys: list[tuple[int, str]]
) -> list[dict]:
    h, w = nearest_indices.shape
    visited = np.zeros((h, w), dtype=bool)
    placements = []

    plate_shapes = [
        (2, 4, "plate_2x4"), (4, 2, "plate_2x4"),
        (2, 3, "plate_2x3"), (3, 2, "plate_2x3"),
        (2, 2, "plate_2x2"),
        (1, 4, "plate_1x4"), (4, 1, "plate_1x4"),
        (1, 3, "plate_1x3"), (3, 1, "plate_1x3"),
        (1, 2, "plate_1x2"), (2, 1, "plate_1x2"),
    ]
    tile_shapes = [
        (2, 4, "tile_2x4"), (4, 2, "tile_2x4"),
        (2, 2, "tile_2x2"),
        (1, 4, "tile_1x4"), (4, 1, "tile_1x4"),
        (1, 3, "tile_1x3"), (3, 1, "tile_1x3"),
        (1, 2, "tile_1x2"), (2, 1, "tile_1x2"),
    ]
# --- START OF CHANGE 2 IN mosaic_engine.py ---
    high_edge_thresh = np.quantile(edge_map, 0.68)
    med_edge_thresh = np.quantile(edge_map, 0.50)

    # Pass 1: Multi-size rectangular plates and tiles
    for r in range(h):
        for c in range(w):
            if visited[r, c] or edge_map[r, c] > high_edge_thresh:
                continue
            color_idx = int(nearest_indices[r, c])
            color_id = palette_keys[color_idx][0]
            is_stud = bool(stud_mask[r, c])
            shapes = plate_shapes if is_stud else tile_shapes

            for sh, sw, part_key in shapes:
                if not is_part_available(part_key, color_id):
                    continue
                if r + sh <= h and c + sw <= w:
                    reg_vis = visited[r:r + sh, c:c + sw]
                    reg_col = nearest_indices[r:r + sh, c:c + sw]
                    reg_stud = stud_mask[r:r + sh, c:c + sw]
                    if (not np.any(reg_vis)
                            and np.all(reg_col == color_idx)
                            and np.all(reg_stud == is_stud)):
                        final_key = part_key
                        shape_type = "rect"
                        if (part_key == "tile_2x2"
                                and is_part_available("tile_round_2x2", color_id)
                                and np.mean(edge_map[r:r + 2, c:c + 2]) > med_edge_thresh):
                            final_key = "tile_round_2x2"
                            shape_type = "round_2x2"
                        visited[r:r + sh, c:c + sw] = True
                        placements.append({
                            "r": r, "c": c, "h": sh, "w": sw,
                            "color_idx": color_idx,
                            "bg_color_idx": color_idx,
                            "part_key": final_key,
                            "is_stud": is_stud,
                            "shape": shape_type,
                            "orient": None
                        })
                        break

    # Pass 2: Remaining 1x1 detail cells
# --- END OF CHANGE 2 IN mosaic_engine.py ---

    for r in range(h):
        for c in range(w):
            if visited[r, c]:
                continue
            visited[r, c] = True
            color_idx = int(nearest_indices[r, c])
            color_id = palette_keys[color_idx][0]
            is_stud = bool(stud_mask[r, c])
            sub_lab = subpixel_lab[r * 2:(r + 1) * 2, c * 2:(c + 1) * 2]

            neighbors = []
            for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
                if 0 <= nr < h and 0 <= nc < w and nearest_indices[nr, nc] != color_idx:
                    neighbors.append(int(nearest_indices[nr, nc]))

            placed_curve = False
            if neighbors and is_part_available("tile_qtr_1x1", color_id):
                bg_color_idx = Counter(neighbors).most_common(1)[0][0]
                orient, improvement = detect_subpixel_orientation(
                    sub_lab, palette_lab[color_idx], palette_lab[bg_color_idx]
                )
                if improvement > 8.5:
                    placements.append({
                        "r": r, "c": c, "h": 1, "w": 1,
                        "color_idx": color_idx,
                        "bg_color_idx": bg_color_idx,
                        "part_key": "tile_qtr_1x1",
                        "is_stud": False,
                        "shape": "qtr_1x1",
                        "orient": orient
                    })
                    placed_curve = True

            if not placed_curve:
                want_round = edge_map[r, c] > high_edge_thresh
                if is_stud:
                    can_round = want_round and is_part_available("plate_round_1x1", color_id)
                    part_key = "plate_round_1x1" if can_round else "plate_1x1"
                else:
                    can_round = want_round and is_part_available("tile_round_1x1", color_id)
                    part_key = "tile_round_1x1" if can_round else "tile_1x1"

                placements.append({
                    "r": r, "c": c, "h": 1, "w": 1,
                    "color_idx": color_idx,
                    "bg_color_idx": color_idx,
                    "part_key": part_key,
                    "is_stud": is_stud,
                    "shape": "round_1x1" if can_round else "rect",
                    "orient": None
                })

    return placements
# --- END OF CHANGE 2 ---


def draw_quarter_tile(
    draw: ImageDraw.ImageDraw,
    x0: int, y0: int, x1: int, y1: int,
    fg_color: tuple[int, int, int],
    bg_color: tuple[int, int, int],
    orient: str,
    seam: tuple[int, int, int]
):
    """Draws an accurate 1x1 Quarter-Circle tile (Part #25269) with exposed corner background."""
    # Fill underlying corner with the neighboring background color
    draw.rectangle([x0, y0, x1, y1], fill=bg_color, outline=seam, width=1)
    w = x1 - x0
    h = y1 - y0

    # Draw the 90-degree pie slice anchored at the flat corner
    if orient == "BR":
        bbox = [x0, y0, x0 + 2 * w, y0 + 2 * h]
        draw.pieslice(bbox, start=180, end=270, fill=fg_color, outline=seam)
    elif orient == "BL":
        bbox = [x1 - 2 * w, y0, x1, y0 + 2 * h]
        draw.pieslice(bbox, start=270, end=360, fill=fg_color, outline=seam)
    elif orient == "TR":
        bbox = [x0, y1 - 2 * h, x0 + 2 * w, y1]
        draw.pieslice(bbox, start=90, end=180, fill=fg_color, outline=seam)
    else:  # "TL"
        bbox = [x1 - 2 * w, y1 - 2 * h, x1, y1]
        draw.pieslice(bbox, start=0, end=90, fill=fg_color, outline=seam)


# --- START OF COMBINED CHANGE IN mosaic_engine.py ---
def filter_background_and_abstract_subject(
    img_cropped: Image.Image,
    palette_keys: list[tuple[int, str]]
) -> tuple[Image.Image, np.ndarray, int]:
    """
    Isolates the foreground subject (using U2-Net `rembg` if installed, or pure-NumPy
    CIELAB border-salience + edge contour segmentation), replaces busy backgrounds with a
    clean contrasting official brick color, and applies edge-preserving abstraction.
    """
    work_img = img_cropped.resize((256, 256), Image.Resampling.BILINEAR)
    fg_mask = None

    try:
        from rembg import remove # type: ignore
        rgba = remove(work_img)
        alpha = np.asarray(rgba)[..., 3].astype(np.float32) / 255.0
        if np.mean(alpha > 0.35) > 0.08:
            fg_mask = alpha > 0.35
    except Exception:
        fg_mask = None

    rgb_norm = np.asarray(work_img.convert("RGB"), dtype=np.float32) / 255.0
    lab = rgb2lab_numpy(rgb_norm)

    if fg_mask is None:
        h, w, _ = lab.shape
        b_pad = max(8, h // 12)
        border_pixels = np.concatenate([
            lab[:b_pad, :, :].reshape(-1, 3),
            lab[-b_pad:, :, :].reshape(-1, 3),
            lab[:, :b_pad, :].reshape(-1, 3),
            lab[:, -b_pad:, :].reshape(-1, 3),
        ], axis=0)

        step = max(1, len(border_pixels) // 4)
        bg_refs = border_pixels[::step][:4]
        dists = [np.linalg.norm(lab - ref[np.newaxis, np.newaxis, :], axis=-1) for ref in bg_refs]
        min_bg_dist = np.min(np.stack(dists, axis=-1), axis=-1)

        yy, xx = np.mgrid[0:h, 0:w]
        cy, cx = h * 0.52, w * 0.50
        radial = np.hypot((yy - cy) / (h * 0.48), (xx - cx) / (w * 0.45))
        center_weight = np.clip(1.25 - 0.55 * (radial ** 2), 0.15, 1.15)

        edges = sobel_edges_numpy(rgb_norm)
        salience = (min_bg_dist * center_weight) + (edges * 14.0)
        thresh = np.quantile(salience, 0.42)
        raw_mask = (salience >= thresh) & (radial < 1.18)

        mask_img = Image.fromarray((raw_mask.astype(np.uint8) * 255), mode="L")
        mask_img = mask_img.filter(ImageFilter.MedianFilter(size=9))
        mask_img = mask_img.filter(ImageFilter.MaxFilter(size=5))
        mask_img = mask_img.filter(ImageFilter.MinFilter(size=5))
        fg_mask = np.asarray(mask_img) > 127

    subject_L = float(np.mean(lab[fg_mask, 0])) if np.any(fg_mask) else 50.0
    preferred_bg_cid = 63 if subject_L > 48.0 else 48  # Dark Blue (#63) or Sand Green (#48)
    bg_palette_idx = next((i for i, (cid, _) in enumerate(palette_keys) if cid == preferred_bg_cid), 0)

    poster_img = work_img.filter(ImageFilter.MedianFilter(size=5))
    poster_img = poster_img.filter(ImageFilter.ModeFilter(size=5))
    poster_img = ImageOps.posterize(poster_img, bits=4)

    return poster_img, fg_mask, bg_palette_idx


def build_overlapping_z_layers(
    surface_placements: list[dict],
    img_lab: np.ndarray,
    edge_map: np.ndarray,
    palette_keys: list[tuple[int, str]],
    grid_size: tuple[int, int],
    z_layers: int = 1,
    z_mode: str = "luminance",
    filler_color_id: int = 86  # 86 = Light Bluish Gray structural interlocking plates
) -> tuple[list[dict], list[dict]]:
    """
    Packs staggered, 90-degree alternating structural plate layers (Z = 1 .. z_layers - 1)
    that bridge across the seams of adjacent layers so multi-layer builds are rigid and never flimsy.
    Also couples isolated 1x1 vertical columns (Z >= 3) to adjacent base plates.
    """
    h, w = grid_size
    if z_layers <= 1:
        for p in surface_placements:
            p["z"] = 1
        return surface_placements, []

    filler_idx = next((idx for idx, (cid, _) in enumerate(palette_keys) if cid == filler_color_id), 0)

    lum_norm = np.clip(img_lab[..., 0] / 100.0, 0.0, 1.0)
    edge_max = float(np.max(edge_map)) or 1.0
    edge_norm = edge_map / edge_max

    if z_mode == "invert_luminance":
        score_map = 0.75 * (1.0 - lum_norm) + 0.25 * edge_norm
    elif z_mode == "edge_relief":
        score_map = 0.35 * lum_norm + 0.65 * edge_norm
    else:
        score_map = 0.75 * lum_norm + 0.25 * edge_norm

    quantiles = [i / z_layers for i in range(1, z_layers)]
    cutoffs = np.quantile(score_map, quantiles)

    top_z_grid = np.ones((h, w), dtype=np.int32)
    surface_seam_grid = np.zeros((h, w), dtype=np.int32)

    for idx, p in enumerate(surface_placements, start=1):
        r, c, ph, pw = p["r"], p["c"], p["h"], p["w"]
        region_score = float(np.mean(score_map[r:r + ph, c:c + pw]))
        z_height = int(np.searchsorted(cutoffs, region_score)) + 1
        p["z"] = z_height
        top_z_grid[r:r + ph, c:c + pw] = z_height
        surface_seam_grid[r:r + ph, c:c + pw] = idx

    # Prevent flimsy 1x1 vertical towers (Z >= 3) by widening their structural support footprint on lower layers
    support_z_grid = top_z_grid.copy()
    if z_layers >= 3:
        for r in range(h):
            for c in range(w):
                if top_z_grid[r, c] >= 3:
                    for nr, nc in [(r, c + 1), (r + 1, c), (r, c - 1), (r - 1, c)]:
                        if 0 <= nr < h and 0 <= nc < w and top_z_grid[nr, nc] >= 2:
                            support_z_grid[nr, nc] = max(support_z_grid[nr, nc], top_z_grid[r, c] - 1)
                            break

    # Odd layers prioritize horizontal plates; Even layers rotate 90° to cross-bridge seams
    horiz_plates = [
        (2, 4, "plate_2x4"), (1, 4, "plate_1x4"), (2, 3, "plate_2x3"),
        (1, 3, "plate_1x3"), (2, 2, "plate_2x2"), (1, 2, "plate_1x2"),
        (4, 2, "plate_2x4"), (4, 1, "plate_1x4"), (3, 2, "plate_2x3"),
        (3, 1, "plate_1x3"), (2, 1, "plate_1x2"), (1, 1, "plate_1x1"),
    ]
    vert_plates = [
        (4, 2, "plate_2x4"), (4, 1, "plate_1x4"), (3, 2, "plate_2x3"),
        (3, 1, "plate_1x3"), (2, 2, "plate_2x2"), (2, 1, "plate_1x2"),
        (2, 4, "plate_2x4"), (1, 4, "plate_1x4"), (2, 3, "plate_2x3"),
        (1, 3, "plate_1x3"), (1, 2, "plate_1x2"), (1, 1, "plate_1x1"),
    ]

    under_placements = []
    prev_layer_seams = surface_seam_grid.copy()
    piece_uid = 10000

    for layer_z in range(1, z_layers):
        need_mask = support_z_grid > layer_z
        visited = ~need_mask
        current_seams = np.zeros((h, w), dtype=np.int32)
        candidate_shapes = vert_plates if (layer_z % 2 == 1) else horiz_plates

        for r in range(h):
            for c in range(w):
                if visited[r, c]:
                    continue

                best_shape = (1, 1, "plate_1x1")
                best_score = -1

                for sh, sw, part_key in candidate_shapes:
                    if not is_part_available(part_key, filler_color_id):
                        continue
                    if r + sh <= h and c + sw <= w and not np.any(visited[r:r + sh, c:c + sw]):
                        bridged_ids = np.unique(prev_layer_seams[r:r + sh, c:c + sw])
                        bridged_count = len(bridged_ids[bridged_ids > 0])
                        score = (bridged_count * 30) + (sh * sw * 4)
                        if score > best_score:
                            best_score = score
                            best_shape = (sh, sw, part_key)
                        if bridged_count >= 2 and sh * sw >= 6:
                            break

                sh, sw, part_key = best_shape
                visited[r:r + sh, c:c + sw] = True
                piece_uid += 1
                current_seams[r:r + sh, c:c + sw] = piece_uid

                under_placements.append({
                    "r": r, "c": c, "h": sh, "w": sw,
                    "z": layer_z,
                    "color_idx": filler_idx,
                    "bg_color_idx": filler_idx,
                    "part_key": part_key,
                    "is_stud": True,
                    "shape": "rect",
                    "orient": None,
                })

        prev_layer_seams = current_seams

    return surface_placements, under_placements


def render_mixed_mosaic(
    placements: list[dict],
    palette_rgb: np.ndarray,
    grid_size: tuple[int, int],
    target_output_px: int = 2400
) -> Image.Image:
    h, w = grid_size
    scale_factor = max(20, target_output_px // max(h, w))
    baseplate_rgb = (18, 22, 26)
    canvas = Image.new("RGB", (w * scale_factor, h * scale_factor), baseplate_rgb)
    draw = ImageDraw.Draw(canvas)
    bevel_w = max(1, scale_factor // 16)
    z_step_px = max(2, scale_factor // 9)

    sorted_placements = sorted(placements, key=lambda item: (item.get("z", 1), item["r"], item["c"]))

    for p in sorted_placements:
        z = p.get("z", 1)
        elev_offset = (z - 1) * z_step_px

        raw_x0 = p["c"] * scale_factor
        raw_y0 = p["r"] * scale_factor
        raw_x1 = (p["c"] + p["w"]) * scale_factor - 1
        raw_y1 = (p["r"] + p["h"]) * scale_factor - 1

        base_color = tuple(int(v) for v in palette_rgb[p["color_idx"]])
        bg_color = tuple(int(v) for v in palette_rgb[p["bg_color_idx"]])
        z_boost = (z - 1) * 8
        face_color = clamp_rgb(base_color, z_boost)
        highlight = clamp_rgb(face_color, 34)
        shadow = clamp_rgb(face_color, -40)
        wall_color = clamp_rgb(base_color, -55)
        seam = clamp_rgb(base_color, -70)

        if z > 1:
            sh_pad = elev_offset + 2
            draw.rectangle(
                [raw_x0 + sh_pad, raw_y0 + sh_pad,
                 min(w * scale_factor - 1, raw_x1 + sh_pad),
                 min(h * scale_factor - 1, raw_y1 + sh_pad)],
                fill=(10, 12, 15)
            )
            draw.rectangle([raw_x0, raw_y0, raw_x1, raw_y1], fill=wall_color, outline=seam, width=1)

        x0 = max(0, raw_x0 - elev_offset)
        y0 = max(0, raw_y0 - elev_offset)
        x1 = max(x0 + 4, raw_x1 - elev_offset)
        y1 = max(y0 + 4, raw_y1 - elev_offset)
        shape = p["shape"]

        if shape == "qtr_1x1":
            draw_quarter_tile(draw, x0, y0, x1, y1, face_color, bg_color, p["orient"], seam)
        elif shape in ("round_1x1", "round_2x2"):
            pad = max(1, scale_factor // 10)
            draw.ellipse([x0 + pad, y0 + pad, x1 - pad, y1 - pad], fill=face_color, outline=seam, width=1)
            draw.arc([x0 + pad + 1, y0 + pad + 1, x1 - pad - 1, y1 - pad - 1],
                     start=200, end=330, fill=highlight, width=bevel_w)
        else:
            draw.rectangle([x0, y0, x1, y1], fill=face_color, outline=seam, width=1)
            draw.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], fill=highlight, width=bevel_w)
            draw.line([(x0 + 1, y0 + 1), (x0 + 1, y1 - 1)], fill=highlight, width=bevel_w)
            draw.line([(x0 + 1, y1 - 1), (x1 - 1, y1 - 1)], fill=shadow, width=bevel_w)
            draw.line([(x1 - 1, y0 + 1), (x1 - 1, y1 - 1)], fill=shadow, width=bevel_w)

        if p["is_stud"]:
            margin = max(3, int(scale_factor * 0.22))
            for sr in range(p["h"]):
                for sc in range(p["w"]):
                    cx0 = max(0, (p["c"] + sc) * scale_factor + margin - elev_offset)
                    cy0 = max(0, (p["r"] + sr) * scale_factor + margin - elev_offset)
                    cx1 = max(cx0 + 2, (p["c"] + sc + 1) * scale_factor - 1 - margin - elev_offset)
                    cy1 = max(cy0 + 2, (p["r"] + sr + 1) * scale_factor - 1 - margin - elev_offset)
                    draw.ellipse([cx0 + 1, cy0 + 2, cx1 + 1, cy1 + 2], fill=shadow)
                    draw.ellipse([cx0, cy0, cx1, cy1], fill=face_color, outline=shadow, width=1)
                    draw.arc([cx0 + 1, cy0 + 1, cx1 - 1, cy1 - 1],
                             start=200, end=330, fill=highlight, width=bevel_w)

    return canvas


def _draw_iso_brick(
    draw: ImageDraw.ImageDraw,
    r: float, c: float, h: float, w: float, z: int,
    color_rgb: tuple[int, int, int],
    is_stud: bool,
    origin_x: float, origin_y: float,
    u_x: float, u_y: float, z_px: float,
    ghosted: bool = False,
    highlight_active: bool = False
):
    """Draws a 3D isometric brick/plate with top diamond face, side walls, and cylindrical 3D studs."""
    def proj(row: float, col: float, layer_z: float) -> tuple[float, float]:
        px = origin_x + (col - row) * u_x
        py = origin_y + (col + row) * u_y - layer_z * z_px
        return (px, py)

    if ghosted:
        top_col = tuple(int(0.62 * v + 0.38 * 225) for v in color_rgb)
        left_col = clamp_rgb(top_col, -16)
        right_col = clamp_rgb(top_col, -30)
        outline_col = (145, 165, 185)
    else:
        top_col = color_rgb
        left_col = clamp_rgb(color_rgb, -28)
        right_col = clamp_rgb(color_rgb, -50)
        outline_col = (255, 210, 35) if highlight_active else clamp_rgb(color_rgb, -75)

    z_top = float(z)
    z_bot = float(z - 1)

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

    if is_stud and u_x >= 4.2:
        stud_rx = max(1.8, u_x * 0.34)
        stud_ry = max(1.1, u_y * 0.34)
        stud_h = max(1.4, z_px * 0.32)
        for sr in range(int(h)):
            for sc in range(int(w)):
                sx, sy = proj(r + sr + 0.5, c + sc + 0.5, z_top)
                draw.rectangle([sx - stud_rx, sy - stud_h, sx + stud_rx, sy], fill=left_col, outline=outline_col)
                draw.ellipse([sx - stud_rx, sy - stud_ry, sx + stud_rx, sy + stud_ry], fill=left_col, outline=outline_col)
                draw.ellipse(
                    [sx - stud_rx, sy - stud_h - stud_ry, sx + stud_rx, sy - stud_h + stud_ry],
                    fill=top_col,
                    outline=outline_col
                )


def generate_isometric_manual(
    surface_placements: list[dict],
    under_placements: list[dict],
    palette_keys: list[tuple[int, str]],
    palette_rgb: np.ndarray,
    grid_size: tuple[int, int],
    output_manual_path: str
) -> str:
    """
    Renders an official LEGO-style 3D Isometric Instruction Manual showing:
    - Step-by-step overlapping brick-bond layer assembly in 3D isometric perspective
    - Parts Callout Box per step with mini isometric brick icons & exact quantities
    - Ghosted previous layers + highlighted active bricks
    """
    h, w = grid_size
    all_placements = under_placements + surface_placements
    max_z = max((p.get("z", 1) for p in all_placements), default=1)

    steps = []
    if max_z > 1:
        for lz in range(1, max_z):
            layer_pcs = [p for p in under_placements if p.get("z", 1) == lz]
            prior_pcs = [p for p in under_placements if p.get("z", 1) < lz]
            orient_tag = "90° Cross-Seam Interlock" if lz % 2 == 1 else "Horizontal Brick-Bond"
            steps.append((
                f"STEP {lz} — Structural Overlapping Layer Z={lz} ({orient_tag})",
                prior_pcs,
                layer_pcs
            ))
        steps.append((
            f"STEP {max_z} — Top Surface Mosaic & Relief Tiles (Z=1..{max_z})",
            under_placements,
            surface_placements
        ))
    else:
        mid_r, mid_c = h // 2, w // 2
        q1 = [p for p in surface_placements if p["r"] < mid_r and p["c"] < mid_c]
        q2 = [p for p in surface_placements if p["r"] < mid_r and p["c"] >= mid_c]
        q3 = [p for p in surface_placements if p["r"] >= mid_r and p["c"] < mid_c]
        q4 = [p for p in surface_placements if p["r"] >= mid_r and p["c"] >= mid_c]
        steps = [
            ("STEP 1 — Top-Left Quadrant Assembly", [], q1),
            ("STEP 2 — Top-Right Quadrant (Bridges Center Seam)", q1, q2),
            ("STEP 3 — Bottom-Left Quadrant Assembly", q1 + q2, q3),
            ("STEP 4 — Final Quadrant & Curved Detail Tiles", q1 + q2 + q3, q4),
        ]

    page_w = 1800
    step_h = 560
    header_h = 110
    page_h = header_h + len(steps) * step_h + 40

    manual = Image.new("RGB", (page_w, page_h), (212, 230, 245))
    draw = ImageDraw.Draw(manual)

    draw.rectangle([0, 0, page_w, header_h], fill=(24, 52, 86))
    draw.text((40, 28), f"ISOMETRIC ASSEMBLY BLUEPRINT — {w}x{h}x{max_z} INTERLOCKING BUILD", fill=(255, 215, 50))
    draw.text(
        (40, 62),
        "Each structural layer rotates 90 degrees to overlap lower seams. Ghosted bricks indicate completed steps.",
        fill=(210, 225, 240)
    )

    for idx, (step_title, ghost_list, active_list) in enumerate(steps):
        y_top = header_h + idx * step_h + 16
        y_bot = y_top + step_h - 24

        draw.rounded_rectangle([30, y_top, page_w - 30, y_bot], radius=18, fill=(230, 242, 252), outline=(165, 195, 220), width=3)

        callout_x0, callout_y0 = 55, y_top + 22
        callout_x1, callout_y1 = 500, y_bot - 22
        draw.rounded_rectangle(
            [callout_x0, callout_y0, callout_x1, callout_y1],
            radius=14,
            fill=(255, 255, 255),
            outline=(180, 205, 228),
            width=2
        )
        draw.rectangle([callout_x0, callout_y0, callout_x1, callout_y0 + 44], fill=(35, 72, 115))
        draw.text((callout_x0 + 18, callout_y0 + 14), step_title, fill=(255, 255, 255))

        step_counts = Counter((p["color_idx"], p["part_key"], p["h"], p["w"], p["is_stud"]) for p in active_list)
        top_step_parts = step_counts.most_common(7)

        row_y = callout_y0 + 62
        for (c_idx, p_key, ph, pw, is_st), qty in top_step_parts:
            c_id, c_name = palette_keys[c_idx]
            p_id, p_name = PART_CATALOG[p_key]
            rgb = tuple(int(v) for v in palette_rgb[c_idx])

            _draw_iso_brick(
                draw, r=0, c=0, h=min(2, ph), w=min(3, pw), z=1,
                color_rgb=rgb, is_stud=is_st,
                origin_x=callout_x0 + 55, origin_y=row_y + 12,
                u_x=9.0, u_y=5.0, z_px=7.0,
                ghosted=False, highlight_active=False
            )
            short_part = p_name.split("(")[0].strip()
            draw.text((callout_x0 + 115, row_y + 4), f"{qty}x  {c_name} {short_part} (#{p_id})", fill=(25, 35, 48))
            row_y += 58

        if len(step_counts) > 7:
            extra_pcs = sum(q for _, q in list(step_counts.items())[7:])
            draw.text((callout_x0 + 20, callout_y1 - 28), f"+ {extra_pcs} additional pieces in this step", fill=(90, 110, 130))

        iso_center_x = 1140.0
        u_x = min(13.0, max(4.2, 510.0 / max(h, w)))
        u_y = u_x * 0.55
        z_px = max(5.0, u_x * 0.68)
        iso_origin_y = y_top + 65.0

        _draw_iso_brick(
            draw, r=0, c=0, h=h, w=w, z=0,
            color_rgb=(45, 54, 66), is_stud=False,
            origin_x=iso_center_x, origin_y=iso_origin_y,
            u_x=u_x, u_y=u_y, z_px=z_px,
            ghosted=False
        )

        combined = [(True, p) for p in ghost_list] + [(False, p) for p in active_list]
        combined.sort(key=lambda item: (item[1].get("z", 1), item[1]["r"] + item[1]["c"], item[1]["r"], item[1]["c"]))

        for is_ghost, p in combined:
            rgb = tuple(int(v) for v in palette_rgb[p["color_idx"]])
            _draw_iso_brick(
                draw,
                r=p["r"], c=p["c"], h=p["h"], w=p["w"], z=p.get("z", 1),
                color_rgb=rgb,
                is_stud=p["is_stud"],
                origin_x=iso_center_x, origin_y=iso_origin_y,
                u_x=u_x, u_y=u_y, z_px=z_px,
                ghosted=is_ghost,
                highlight_active=(not is_ghost and max_z > 1)
            )

    manual.save(output_manual_path, format="PNG")
    return output_manual_path


# --- START OF TRUE-TONE COLOR CHANGE IN mosaic_engine.py ---
def delta_e_ciede2000_numpy(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """
    Perceptual CIEDE2000 color distance between image pixels (H, W, 1, 3)
    and official brick palette (1, 1, N, 3) for true-tone color accuracy.
    """
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
    nearest_indices = denoise_and_smooth_grid(
        raw_indices, delta_e, edge_map, merge_tolerance_de=merge_tolerance_de
    )

    threshold = np.quantile(edge_map, 1.0 - stud_ratio)
    stud_mask = edge_map >= threshold
    if abstract_mode and fg_mask_grid is not None:
        stud_mask = stud_mask & fg_mask_grid
        stud_mask[0, :] = False
        stud_mask[-1, :] = False
        stud_mask[:, 0] = False
        stud_mask[:, -1] = False

    surface_placements = pack_multi_shape_mosaic(
        nearest_indices=nearest_indices,
        stud_mask=stud_mask,
        edge_map=edge_map,
        subpixel_lab=subpixel_lab,
        palette_lab=palette_lab,
        palette_keys=palette_keys
    )

    effective_z = max(2, z_layers) if abstract_mode else z_layers
    surface_placements, under_placements = build_overlapping_z_layers(
        surface_placements=surface_placements,
        img_lab=img_lab,
        edge_map=edge_map,
        palette_keys=palette_keys,
        grid_size=grid_size,
        z_layers=effective_z,
        z_mode=z_mode
    )

    mosaic_img = render_mixed_mosaic(surface_placements, palette_rgb, grid_size, target_output_px=target_output_px)
    mosaic_img.save(output_path, format="PNG")

    if manual_output_path is None:
        manual_output_path = output_path.replace(".png", "_manual.png")
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

    total_studs = (
        grid_size[0] * grid_size[1]
        + sum(u["h"] * u["w"] for u in under_placements)
    )
    return bom, grid_size, total_studs
# --- END OF TRUE-TONE COLOR CHANGE IN mosaic_engine.py ---

def export_bricklink_xml(
    bom: dict,
    xml_output_path: str,
    grid_size: tuple[int, int] | None = None,
    include_baseplates: bool = True,
    baseplate_color_id: int = 85,  # 85 = Dark Bluish Gray (standard for 48x48 #4186), 11 = Black
    condition: str = "N"           # "N" = New parts only, "U" = Used, or "" = Any condition
) -> str:
    """
    Exports the multi-shape Bill of Materials (BOM) into a valid BrickLink Wanted List XML file
    AND returns the raw XML string (so you can also paste it into BrickLink's 'Upload BrickLink XML' box).
    """
    lines = ["<INVENTORY>"]

    # 1. Automatically include the physical baseplates needed to build the grid
    if include_baseplates and grid_size is not None:
        h, w = grid_size
        if h % 48 == 0 and w % 48 == 0:
            bp_id = "4186"  # Official 48 x 48 Baseplate
            bp_qty = (h // 48) * (w // 48)
            bp_color = baseplate_color_id
        elif h % 32 == 0 and w % 32 == 0:
            bp_id = "3811"  # Official 32 x 32 Baseplate
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

    # 2. Add every multi-size plate, flat tile, round piece, and curved tile from the BOM
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
if __name__ == "__main__":
    from tkinter import Tk, filedialog

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print("Select a photo in the popup file browser...")
    test_input = filedialog.askopenfilename(
        title="Select a Photo for Your Brick Mosaic",
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp")]
    )

    if not test_input:
        print("No photo selected. Exiting.")
    else:
        print("\n=== Select Mosaic Resolution Preset ===")
        for key, (_, _, desc) in GRID_PRESETS.items():
            print(f"  [{key}] {desc}")
        choice = input("\nEnter preset number (1-6) [Default = 6 (Auto)]: ").strip() or "6"
        preset_key, chosen_grid, _ = GRID_PRESETS.get(choice, GRID_PRESETS["6"])

        script_dir = os.path.dirname(os.path.abspath(__file__))
        photo_name = os.path.splitext(os.path.basename(test_input))[0]
        test_output = os.path.join(script_dir, f"{photo_name}_optimized_{preset_key}.png")
        xml_output = os.path.join(script_dir, f"{photo_name}_bricklink_{preset_key}.xml")

        parts_list, final_grid, total_studs = generate_brick_mosaic(
            input_path=test_input,
            output_path=test_output,
            grid_size=chosen_grid,
            target_output_px=2400,
            stud_ratio=0.45,
            merge_tolerance_de=4.2,
            pre_sharpen=True
        )

        # Export the BrickLink Wanted List XML
        export_bricklink_xml(
            bom=parts_list,
            xml_output_path=xml_output,
            grid_size=final_grid,
            include_baseplates=True,
            condition="N"  # "N" = New parts, or change to "" for Any condition (cheaper on BrickLink!)
        )

        total_pieces = sum(parts_list.values())
        reduction_pct = (1.0 - (total_pieces / total_studs)) * 100.0

        print(f"\nSaved {final_grid[0]}x{final_grid[1]} multi-shape mosaic PNG to:\n  {test_output}")
        print(f"Saved BrickLink Wanted List XML to:\n  {xml_output}")
        print(f"\n--- Part Optimizer Summary ---")
        print(f"Grid Capacity : {total_studs} studs")
        print(f"Physical Parts: {total_pieces} pcs ({reduction_pct:.1f}% fewer pieces used!)")
        print(f"\n--- Top 25 Parts in Bill of Materials ---")
        for (color_id, color_name, part_id, part_name), count in list(parts_list.items())[:25]:
            print(f"Color {color_id:<3} ({color_name:<20}) | Part #{part_id:<5} {part_name:<34} : {count} pcs")