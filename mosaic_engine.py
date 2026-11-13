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
_U2NETP_SESSION = None


def extract_neural_foreground_mask(img_pil: Image.Image) -> np.ndarray | None:
    """
    Runs the lightweight 4.7 MB 'u2netp' neural model via rembg (cached globally
    so Render Free Tier RAM stays under ~160 MB) and returns a boolean subject mask.
    """
    global _U2NETP_SESSION
    try:
        from rembg import remove, new_session  # type: ignore
        if _U2NETP_SESSION is None:
            # Store model weights in /tmp/.u2net so Render's ephemeral filesystem has write access
            os.environ.setdefault("U2NET_HOME", "/tmp/.u2net")
            _U2NETP_SESSION = new_session("u2netp")

        work_img = img_pil.resize((256, 256), Image.Resampling.BILINEAR)
        mask_pil = remove(work_img, session=_U2NETP_SESSION, only_mask=True)
        mask_arr = np.asarray(mask_pil, dtype=np.float32)
        if mask_arr.ndim == 3:
            mask_arr = mask_arr[..., 0]
        fg_mask = mask_arr > 95.0
        if 0.04 < float(np.mean(fg_mask)) < 0.94:
            return fg_mask
    except Exception:
        pass
    return None


def filter_background_and_abstract_subject(
    img_cropped: Image.Image,
    palette_keys: list[tuple[int, str]]
) -> tuple[Image.Image, np.ndarray, int]:
    """
    Isolates the foreground subject using the cached 4 MB 'u2netp' neural session
    (with pure-NumPy CIELAB fallback), replaces busy backgrounds with a clean studio
    brick color, and applies edge-preserving abstraction for 32x32 frame builds.
    """
    work_img = img_cropped.resize((256, 256), Image.Resampling.BILINEAR)
    fg_mask = extract_neural_foreground_mask(work_img)

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
    preferred_bg_cid = 63 if subject_L > 48.0 else 86  # Dark Blue (#63) or Light Bluish Gray (#86)
    bg_palette_idx = next((i for i, (cid, _) in enumerate(palette_keys) if cid == preferred_bg_cid), 0)

    poster_img = work_img.filter(ImageFilter.MedianFilter(size=5))
    poster_img = poster_img.filter(ImageFilter.ModeFilter(size=5))
    poster_img = ImageOps.posterize(poster_img, bits=4)

    return poster_img, fg_mask, bg_palette_idx


def detect_boxed_grooves_and_preserve_lines(
    img_cropped: Image.Image,
    grid_size: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    """
    Detects thin dark outlines, letter boxes, and structural creases at 512x512 BEFORE downsampling
    so boxed letters (like 'RE-GO') are never washed out by LANCZOS averaging.
    Returns:
      - groove_mask (h, w): True where a crisp dark contour/box outline exists on the stud grid.
      - dark_sub_rgb (h, w, 3): The darkest 20th-percentile RGB color inside each stud cell.
    """
    gh, gw = grid_size
    factor = max(2, 512 // max(gh, gw))
    work_h, work_w = gh * factor, gw * factor
    hi_img = img_cropped.resize((work_w, work_h), Image.Resampling.BILINEAR)
    hi_rgb = np.asarray(hi_img, dtype=np.float32) / 255.0
    hi_gray = 0.2126 * hi_rgb[..., 0] + 0.7152 * hi_rgb[..., 1] + 0.0722 * hi_rgb[..., 2]

    # Black-hat morphological valley detector: local maximum minus pixel brightness catches thin dark lines
    gray_u8 = np.clip(hi_gray * 255.0, 0, 255).astype(np.uint8)
    dilated_u8 = np.asarray(
        Image.fromarray(gray_u8, mode="L").filter(ImageFilter.MaxFilter(size=max(3, factor | 1))),
        dtype=np.float32
    )
    valley_hi = (dilated_u8 - gray_u8.astype(np.float32)) / 255.0

    # Max-pool valley strength per stud cell so 2px outlines survive downsampling
    valley_blocks = valley_hi.reshape(gh, factor, gw, factor)
    max_valley = np.max(valley_blocks, axis=(1, 3))
    mean_valley = np.mean(valley_blocks, axis=(1, 3))
    groove_score = 0.70 * max_valley + 0.30 * mean_valley

    # Adaptive threshold: cells with a sharp dark stroke inside a brighter surrounding
    groove_thresh = max(0.085, float(np.quantile(groove_score, 0.82)))
    groove_mask = groove_score >= groove_thresh

    # Compute the 20th-percentile darkest RGB inside each stud block to color the preserved outline accurately
    rgb_blocks = hi_rgb.reshape(gh, factor, gw, factor, 3).transpose(0, 2, 1, 3, 4).reshape(gh, gw, factor * factor, 3)
    luma_blocks = 0.2126 * rgb_blocks[..., 0] + 0.7152 * rgb_blocks[..., 1] + 0.0722 * rgb_blocks[..., 2]
    dark_idx = np.argsort(luma_blocks, axis=-1)[:, :, :max(1, (factor * factor) // 5)]
    row_idx = np.arange(gh)[:, None, None]
    col_idx = np.arange(gw)[None, :, None]
    dark_sub_rgb = np.mean(rgb_blocks[row_idx, col_idx, dark_idx], axis=2)

    return groove_mask, dark_sub_rgb


def compute_focus_and_detail_maps(img_rgb_norm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Extracts two AI perception maps that work even on blurry or low-contrast photos:
    1. focus_map (0..1): Local high-frequency Laplacian variance — detects what is in-focus
       vs. blurry background bokeh so blurry areas are never elevated to top layers.
    2. detail_band (0..1): Multi-scale Difference-of-Gaussians (DoG) that recovers distinct
       internal features (eyes, noses, mouths, boxed letters) from soft/blurry images.
    """
    gray_u8 = np.clip(
        (0.2126 * img_rgb_norm[..., 0] + 0.7152 * img_rgb_norm[..., 1] + 0.0722 * img_rgb_norm[..., 2]) * 255.0,
        0, 255
    ).astype(np.uint8)
    pil_g = Image.fromarray(gray_u8, mode="L")

    # Multi-scale Gaussian pyramid for Difference-of-Gaussians (DoG) detail recovery
    g_fine = np.asarray(pil_g.filter(ImageFilter.GaussianBlur(radius=0.8)), dtype=np.float32)
    g_med = np.asarray(pil_g.filter(ImageFilter.GaussianBlur(radius=2.2)), dtype=np.float32)
    g_coarse = np.asarray(pil_g.filter(ImageFilter.GaussianBlur(radius=5.0)), dtype=np.float32)

    # DoG captures distinct structural features regardless of overall lighting or blur
    dog_fine = np.abs(g_fine - g_med)
    dog_broad = np.abs(g_med - g_coarse)
    raw_detail = 0.65 * dog_fine + 0.35 * dog_broad
    detail_max = float(np.percentile(raw_detail, 98)) or 1.0
    detail_band = np.clip(raw_detail / detail_max, 0.0, 1.0)

    # Local Focus / Sharpness energy (smoothed over neighborhood to find the in-focus subject)
    lap_energy = np.clip((dog_fine / (float(np.percentile(dog_fine, 95)) or 1.0)) * 255.0, 0, 255).astype(np.uint8)
    focus_smooth = Image.fromarray(lap_energy, mode="L").filter(ImageFilter.BoxBlur(radius=3))
    focus_arr = np.asarray(focus_smooth, dtype=np.float32)
    f_max = float(np.max(focus_arr)) or 1.0
    focus_map = np.clip(focus_arr / f_max, 0.0, 1.0)

    return focus_map, detail_band


def compute_stable_terrace_z_grid(
    img_lab: np.ndarray,
    edge_map: np.ndarray,
    grid_size: tuple[int, int],
    z_layers: int = 1,
    z_mode: str = "luminance",
    fg_mask_grid: np.ndarray | None = None,
    groove_mask: np.ndarray | None = None
) -> np.ndarray:
    """
    AI Detail & Focus-Aware 3D Layer Allocator:
    - Works across sharp logos, portraits, pets, and blurry photos.
    - Pushes out-of-focus / background regions to Layer Z=1.
    - Allocates the subject across Layers 2..z_layers by distinct feature salience
      (mid-tone body on lower terrace, distinct facial/object details on top terrace,
      and dark contour outlines carved 1 layer down so details never blob together).
    """
    h, w = grid_size
    if z_layers <= 1:
        return np.ones((h, w), dtype=np.int32)

    # Reconstruct normalized RGB approximation from L*a*b* lightness & chroma for focus/detail analysis
    lum_norm = np.clip(img_lab[..., 0] / 100.0, 0.0, 1.0)
    chroma = np.hypot(img_lab[..., 1], img_lab[..., 2])
    chroma_norm = np.clip(chroma / (float(np.percentile(chroma, 95)) or 1.0), 0.0, 1.0)
    pseudo_rgb = np.stack([lum_norm, lum_norm, chroma_norm], axis=-1)
    focus_map, detail_band = compute_focus_and_detail_maps(pseudo_rgb)

    # 1. Identify Background vs. Foreground Subject using Border Lab + Focus Map + Center Prior
    b_pad = max(2, min(h, w) // 12)
    border_lab = np.concatenate([
        img_lab[:b_pad, :, :].reshape(-1, 3),
        img_lab[-b_pad:, :, :].reshape(-1, 3),
        img_lab[:, :b_pad, :].reshape(-1, 3),
        img_lab[:, -b_pad:, :].reshape(-1, 3),
    ], axis=0)

    # Cluster border into 3 reference tones (handles two-tone sky/ground or indoor walls)
    step = max(1, len(border_lab) // 3)
    bg_refs = [np.median(border_lab[i * step:(i + 1) * step], axis=0) for i in range(3)]
    bg_dists = [np.linalg.norm(img_lab - ref[np.newaxis, np.newaxis, :], axis=-1) for ref in bg_refs]
    min_bg_dist = np.min(np.stack(bg_dists, axis=-1), axis=-1)
    bg_dist_norm = np.clip(min_bg_dist / (float(np.percentile(min_bg_dist, 92)) or 1.0), 0.0, 1.0)

    border_spread = float(np.percentile(np.linalg.norm(border_lab - np.median(border_lab, axis=0), axis=-1), 75))
    has_uniform_backdrop = border_spread < 18.0

    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h * 0.50, w * 0.50
    radial = np.hypot((yy - cy) / (h * 0.50), (xx - cx) / (w * 0.50))
    center_prior = np.clip(1.20 - 0.45 * (radial ** 2), 0.20, 1.15)

    if fg_mask_grid is not None:
        is_subject = fg_mask_grid.copy()
    elif has_uniform_backdrop:
        raw_subj = min_bg_dist > max(13.0, border_spread * 2.1)
        s_img = Image.fromarray((raw_subj.astype(np.uint8) * 255), mode="L")
        s_img = s_img.filter(ImageFilter.MaxFilter(size=3)).filter(ImageFilter.MinFilter(size=3))
        is_subject = np.asarray(s_img) > 127
    else:
        # For complex/blurry real-world photos: combine color contrast from border, focus sharpness, and center prior
        subject_likelihood = (0.45 * bg_dist_norm + 0.35 * focus_map + 0.20 * chroma_norm) * center_prior
        subj_cutoff = float(np.quantile(subject_likelihood, 0.36))
        raw_subj = subject_likelihood >= subj_cutoff
        s_img = Image.fromarray((raw_subj.astype(np.uint8) * 255), mode="L")
        s_img = s_img.filter(ImageFilter.MedianFilter(size=5)).filter(ImageFilter.MaxFilter(size=3))
        is_subject = np.asarray(s_img) > 127

    # 2. CASE A: Clean Graphic Logo / Boxed Icon (like REGO.jpg)
    if has_uniform_backdrop and np.any(is_subject) and np.mean(is_subject) < 0.82:
        z_grid = np.ones((h, w), dtype=np.int32)
        mid_z = max(1, z_layers - 1)
        subj_L = img_lab[..., 0][is_subject]
        shade_cutoff = float(np.percentile(subj_L, 28)) if len(subj_L) > 0 else 40.0
        is_shaded_panel = is_subject & (img_lab[..., 0] <= shade_cutoff)

        z_grid[is_subject] = z_layers
        if z_layers >= 3:
            z_grid[is_shaded_panel] = mid_z
            if groove_mask is not None:
                z_grid[is_subject & groove_mask] = mid_z
        elif z_layers == 2 and groove_mask is not None:
            z_grid[is_subject & groove_mask] = 1
        return z_grid

    # 3. CASE B: Complex / Blurry Photo — Allocate Layers by Distinct Detail + Focus + Tone
    edge_max = float(np.max(edge_map)) or 1.0
    edge_norm = edge_map / edge_max

    if z_mode == "invert_luminance":
        tone_score = 1.0 - lum_norm
    elif z_mode == "edge_relief":
        tone_score = 0.30 * lum_norm + 0.70 * detail_band
    else:
        tone_score = lum_norm

    # Fuse local distinct detail (DoG), focus sharpness, chroma, and tone inside the subject
    detail_elevation_score = (
        0.38 * detail_band
        + 0.32 * tone_score
        + 0.18 * focus_map
        + 0.12 * edge_norm
    )

    # Smooth slightly so features form buildable multi-stud plateaus instead of single-stud noise
    s_u8 = np.clip(detail_elevation_score * 255.0, 0, 255).astype(np.uint8)
    smooth_detail = np.asarray(
        Image.fromarray(s_u8, mode="L").filter(ImageFilter.MedianFilter(size=3)),
        dtype=np.float32
    ) / 255.0

    z_grid = np.ones((h, w), dtype=np.int32)
    subj_scores = smooth_detail[is_subject]

    if len(subj_scores) > 0:
        if z_layers == 2:
            # Layer 1 = Background; Layer 2 = Subject (with recessed contour grooves at Layer 1)
            z_grid[is_subject] = 2
        else:
            # Allocate subject across Layers 2 .. z_layers based on distinct feature percentiles
            upper_levels = z_layers - 1  # e.g., Layers 2, 3 (or 2, 3, 4)
            q_points = [i / upper_levels for i in range(1, upper_levels)]
            cutoffs = np.quantile(subj_scores, q_points)
            z_grid[is_subject] = (np.searchsorted(cutoffs, smooth_detail[is_subject]) + 2).astype(np.int32)

    # Enforce stepped terrace stability: Layer Z must sit on a slightly wider Layer Z-1 base
    for lz in range(z_layers, 2, -1):
        upper_mask = (z_grid >= lz).astype(np.uint8) * 255
        dilated = Image.fromarray(upper_mask, mode="L").filter(ImageFilter.MaxFilter(size=3))
        must_support = np.asarray(dilated) > 127
        z_grid = np.where(must_support & (z_grid < lz - 1), lz - 1, z_grid)

    # Carve sharp dark contour lines / grooves 1 layer down so distinct details stay separated
    if groove_mask is not None and z_layers >= 2:
        z_grid = np.where(is_subject & groove_mask & (z_grid > 1), z_grid - 1, z_grid)

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
    filler_color_id: int = 86  # 86 = Light Bluish Gray structural plates
) -> tuple[list[dict], list[dict]]:
    """
    Packs the mosaic strictly layer-by-layer from Z = 1 up to max_z with 90-degree
    cross-seam interlocking, keeping boxed letters crisp with square plates/tiles.
    """
    h, w = nearest_indices.shape
    max_z = int(np.max(z_grid))
    filler_idx = next((idx for idx, (cid, _) in enumerate(palette_keys) if cid == filler_color_id), 0)

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

    high_edge_thresh = np.quantile(edge_map, 0.75)

    surface_placements: list[dict] = []
    under_placements: list[dict] = []
    prev_seam_grid = np.zeros((h, w), dtype=np.int32)
    uid = 1

    for lz in range(1, max_z + 1):
        curr_seam_grid = np.zeros((h, w), dtype=np.int32)
        odd_layer = (lz % 2 == 1)
        plate_order = horiz_First if odd_layer else vert_First
        tile_order = horiz_Tiles if odd_layer else vert_Tiles

        # 1. Pack structural studded under-plates for all cells where z_grid > lz
        struct_visited = ~(z_grid > lz)
        for r in range(h):
            for c in range(w):
                if struct_visited[r, c]:
                    continue
                best_shape = (1, 1, "plate_1x1")
                best_score = -1
                for sh, sw, part_key in plate_order:
                    if not is_part_available(part_key, filler_color_id):
                        continue
                    if r + sh <= h and c + sw <= w and not np.any(struct_visited[r:r + sh, c:c + sw]):
                        bridged = len(np.unique(prev_seam_grid[r:r + sh, c:c + sw])) if lz > 1 else 1
                        score = (bridged * 35) + (sh * sw * 5)
                        if score > best_score:
                            best_score = score
                            best_shape = (sh, sw, part_key)
                        if bridged >= 2 and sh * sw >= 6:
                            break
                sh, sw, part_key = best_shape
                struct_visited[r:r + sh, c:c + sw] = True
                uid += 1
                curr_seam_grid[r:r + sh, c:c + sw] = uid
                under_placements.append({
                    "r": r, "c": c, "h": sh, "w": sw, "z": lz,
                    "color_idx": filler_idx,
                    "bg_color_idx": filler_idx,
                    "part_key": part_key,
                    "is_stud": True,
                    "shape": "rect",
                    "orient": None,
                    "is_structural": True,
                })

        # 2. Pack visible surface pieces for all cells where z_grid == lz
        surf_visited = ~(z_grid == lz)
        for r in range(h):
            for c in range(w):
                if surf_visited[r, c]:
                    continue
                if groove_mask is not None and groove_mask[r, c]:
                    continue  # Keep 1-stud contour grooves sharp before packing multi-stud blocks
                color_idx = int(nearest_indices[r, c])
                color_id = palette_keys[color_idx][0]
                is_stud = bool(stud_mask[r, c])
                shapes = plate_order if is_stud else tile_order

                best_candidate = None
                best_score = -1
                for sh, sw, part_key in shapes:
                    if not is_part_available(part_key, color_id):
                        continue
                    if r + sh <= h and c + sw <= w:
                        reg_vis = surf_visited[r:r + sh, c:c + sw]
                        reg_col = nearest_indices[r:r + sh, c:c + sw]
                        reg_stud = stud_mask[r:r + sh, c:c + sw]
                        reg_grv = groove_mask[r:r + sh, c:c + sw] if groove_mask is not None else False
                        if (not np.any(reg_vis)
                                and not np.any(reg_grv)
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
                    uid += 1
                    curr_seam_grid[r:r + sh, c:c + sw] = uid
                    surface_placements.append({
                        "r": r, "c": c, "h": sh, "w": sw, "z": lz,
                        "color_idx": color_idx,
                        "bg_color_idx": color_idx,
                        "part_key": part_key,
                        "is_stud": is_stud,
                        "shape": "rect",
                        "orient": None,
                        "is_structural": False,
                    })

        # 3. Remaining 1x1 detail & contour groove cells on Layer lz (uses square 1x1s to prevent black gaps)
        for r in range(h):
            for c in range(w):
                if surf_visited[r, c]:
                    continue
                surf_visited[r, c] = True
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

                placed_curve = False
                is_groove_cell = bool(groove_mask[r, c]) if groove_mask is not None else False
                if neighbors and not is_groove_cell and is_part_available("tile_qtr_1x1", color_id):
                    bg_color_idx = Counter(neighbors).most_common(1)[0][0]
                    orient, improvement = detect_subpixel_orientation(
                        sub_lab, palette_lab[color_idx], palette_lab[bg_color_idx]
                    )
                    if improvement > 9.5:
                        surface_placements.append({
                            "r": r, "c": c, "h": 1, "w": 1, "z": lz,
                            "color_idx": color_idx,
                            "bg_color_idx": bg_color_idx,
                            "part_key": "tile_qtr_1x1",
                            "is_stud": False,
                            "shape": "qtr_1x1",
                            "orient": orient,
                            "is_structural": False,
                        })
                        placed_curve = True

                if not placed_curve:
                    part_key = "plate_1x1" if is_stud else "tile_1x1"
                    surface_placements.append({
                        "r": r, "c": c, "h": 1, "w": 1, "z": lz,
                        "color_idx": color_idx,
                        "bg_color_idx": color_idx,
                        "part_key": part_key,
                        "is_stud": is_stud,
                        "shape": "rect",
                        "orient": None,
                        "is_structural": False,
                    })

        prev_seam_grid = curr_seam_grid

    return surface_placements, under_placements


def render_mixed_mosaic(
    placements: list[dict],
    palette_rgb: np.ndarray,
    grid_size: tuple[int, int],
    target_output_px: int = 2400
) -> Image.Image:
    """
    Renders 2D and 3D mosaics with crisp step-relief shading so elevated boxed letters
    and plateaus stand out cleanly without shifting over and covering 1-stud outlines.
    """
    h, w = grid_size
    scale_factor = max(20, target_output_px // max(h, w))
    baseplate_rgb = (24, 28, 34)
    canvas = Image.new("RGB", (w * scale_factor, h * scale_factor), baseplate_rgb)
    draw = ImageDraw.Draw(canvas)
    bevel_w = max(1, scale_factor // 15)
    z_step_px = max(1, scale_factor // 16)

    max_z = max((p.get("z", 1) for p in placements), default=1)
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

        # Subtle depth lighting: top layer is brightest; recessed grooves/layers are slightly shaded
        z_boost = (z - max_z) * 10 if max_z > 1 else 0
        face_color = clamp_rgb(base_color, z_boost)
        highlight = clamp_rgb(face_color, 36)
        shadow = clamp_rgb(face_color, -42)
        wall_color = clamp_rgb(base_color, -52)
        seam = clamp_rgb(base_color, -68)

        if z > 1:
            # Draw subtle 3D side wall & drop-shadow without swallowing adjacent 1-stud grooves
            sh_pad = max(2, elev_offset + 1)
            draw.rectangle(
                [raw_x0 + sh_pad, raw_y0 + sh_pad,
                 min(w * scale_factor - 1, raw_x1 + sh_pad),
                 min(h * scale_factor - 1, raw_y1 + sh_pad)],
                fill=clamp_rgb(base_color, -85)
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
            draw.rectangle([x0, y0, x1, y1], fill=wall_color, outline=seam, width=1)
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


def _draw_iso_baseplate(
    draw: ImageDraw.ImageDraw,
    h: int, w: int,
    origin_x: float, origin_y: float,
    u_x: float, u_y: float, z_px: float
):
    """Draws an authentic LEGO Dark Bluish Gray baseplate with visible stud grid rings."""
    def proj(row: float, col: float, layer_z: float) -> tuple[float, float]:
        return (origin_x + (col - row) * u_x, origin_y + (col + row) * u_y - layer_z * z_px)

    top_col = (108, 112, 116)
    left_col = (82, 86, 90)
    right_col = (64, 68, 72)
    edge_col = (48, 52, 56)

    p_top = proj(0, 0, 0.0)
    p_right = proj(0, w, 0.0)
    p_front = proj(h, w, 0.0)
    p_left = proj(h, 0, 0.0)
    p_left_bot = proj(h, 0, -0.5)
    p_front_bot = proj(h, w, -0.5)
    p_right_bot = proj(0, w, -0.5)

    draw.polygon([p_left, p_front, p_front_bot, p_left_bot], fill=left_col, outline=edge_col)
    draw.polygon([p_front, p_right, p_right_bot, p_front_bot], fill=right_col, outline=edge_col)
    draw.polygon([p_top, p_right, p_front, p_left], fill=top_col, outline=edge_col)

    grid_line_col = (96, 100, 104)
    for r in range(1, h):
        draw.line([proj(r, 0, 0.0), proj(r, w, 0.0)], fill=grid_line_col, width=1)
    for c in range(1, w):
        draw.line([proj(0, c, 0.0), proj(h, c, 0.0)], fill=grid_line_col, width=1)

    if u_x >= 4.0:
        srx = max(1.4, u_x * 0.28)
        sry = max(0.8, u_y * 0.28)
        for r in range(h):
            for c in range(w):
                sx, sy = proj(r + 0.5, c + 0.5, 0.0)
                draw.ellipse([sx - srx, sy - sry, sx + srx, sy + sry], outline=(88, 92, 96))


def _draw_iso_brick(
    draw: ImageDraw.ImageDraw,
    r: float, c: float, h: float, w: float, z: int,
    color_rgb: tuple[int, int, int],
    is_stud: bool,
    origin_x: float, origin_y: float,
    u_x: float, u_y: float, z_px: float,
    is_new_step: bool = False
):
    def proj(row: float, col: float, layer_z: float) -> tuple[float, float]:
        return (origin_x + (col - row) * u_x, origin_y + (col + row) * u_y - layer_z * z_px)

    top_col = color_rgb
    left_col = clamp_rgb(color_rgb, -24)
    right_col = clamp_rgb(color_rgb, -44)
    outline_col = (224, 36, 36) if is_new_step else (42, 46, 52)
    stud_outline = (55, 60, 66)

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

    if is_new_step:
        draw.line([p_top, p_right, p_front, p_left, p_top], fill=(224, 36, 36), width=2)

    if is_stud and u_x >= 3.8:
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
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def generate_isometric_manual(
    surface_placements: list[dict],
    under_placements: list[dict],
    palette_keys: list[tuple[int, str]],
    palette_rgb: np.ndarray,
    grid_size: tuple[int, int],
    output_manual_path: str
) -> str:
    """100% Wordless LEGO-Style Isometric Instruction Manual ('1x', '2x', '3x' only)."""
    h, w = grid_size
    all_placements = under_placements + surface_placements
    max_z = max((p.get("z", 1) for p in all_placements), default=1)

    font_qty = _get_manual_font(16)
    font_step = _get_manual_font(28)
    font_small = _get_manual_font(13)

    raw_batches: list[list[dict]] = []
    for lz in range(1, max_z + 1):
        layer_pcs = [p for p in all_placements if p.get("z", 1) == lz]
        if not layer_pcs:
            continue
        layer_pcs.sort(key=lambda p: (p["r"] + p["c"], p["r"], p["c"]))

        num_splits = 4 if max_z <= 2 else 2
        chunk_size = max(1, (len(layer_pcs) + num_splits - 1) // num_splits)
        for s_idx in range(0, len(layer_pcs), chunk_size):
            raw_batches.append(layer_pcs[s_idx:s_idx + chunk_size])

    steps = []
    accumulated: list[dict] = []
    for step_num, batch in enumerate(raw_batches, start=1):
        steps.append((step_num, list(accumulated), batch))
        accumulated.extend(batch)

    cols = 2
    rows = (len(steps) + cols - 1) // cols
    panel_w = 920
    panel_h = 520
    page_w = panel_w * cols
    iso_section_h = panel_h * rows
    map_section_h = 1220
    page_h = iso_section_h + map_section_h

    manual = Image.new("RGB", (page_w, page_h), (228, 240, 248))
    draw = ImageDraw.Draw(manual)

    for idx, (step_num, prior_pcs, active_pcs) in enumerate(steps):
        row_idx = idx // cols
        col_idx = idx % cols
        px0 = col_idx * panel_w
        py0 = row_idx * panel_h
        px1 = px0 + panel_w
        py1 = py0 + panel_h

        draw.rectangle([px0, py0, px1, py1], fill=(228, 240, 248), outline=(255, 255, 255), width=4)

        box_x0, box_y0 = px0 + 24, py0 + 24
        box_x1, box_y1 = px0 + 300, py0 + 425
        draw.rounded_rectangle(
            [box_x0, box_y0, box_x1, box_y1],
            radius=10,
            fill=(245, 248, 252),
            outline=(176, 196, 214),
            width=2
        )

        draw.text((box_x0 + 8, box_y1 + 14), f"{step_num}", fill=(25, 32, 42), font=font_step)

        step_counts = Counter((p["color_idx"], p["part_key"], p["h"], p["w"], p["is_stud"]) for p in active_pcs)
        top_step_parts = step_counts.most_common(10)

        for p_idx, ((c_idx, p_key, ph, pw, is_st), qty) in enumerate(top_step_parts):
            rgb = tuple(int(v) for v in palette_rgb[c_idx])
            p_col = p_idx % 2
            p_row = p_idx // 2

            cell_x = box_x0 + 18 + p_col * 132
            cell_y = box_y0 + 26 + p_row * 76

            _draw_iso_brick(
                draw, r=0, c=0, h=min(2, ph), w=min(3, pw), z=1,
                color_rgb=rgb, is_stud=is_st,
                origin_x=cell_x + 28, origin_y=cell_y + 10,
                u_x=7.5, u_y=3.75, z_px=3.2,
                is_new_step=False
            )
            draw.text((cell_x + 68, cell_y + 8), f"{qty}x", fill=(20, 24, 30), font=font_qty)

        u_x = min(9.5, max(3.6, 265.0 / max(h, w)))
        u_y = u_x * 0.50
        z_px = u_x * 0.40
        board_pixel_h = (h + w) * u_y
        iso_center_x = px0 + 605.0
        iso_origin_y = py0 + (panel_h - board_pixel_h) * 0.5 + 10.0

        _draw_iso_baseplate(draw, h, w, iso_center_x, iso_origin_y, u_x, u_y, z_px)

        combined = [(False, p) for p in prior_pcs] + [(True, p) for p in active_pcs]
        combined.sort(key=lambda item: (item[1].get("z", 1), item[1]["r"] + item[1]["c"], item[1]["r"], item[1]["c"]))

        for is_new, p in combined:
            rgb = tuple(int(v) for v in palette_rgb[p["color_idx"]])
            _draw_iso_brick(
                draw,
                r=p["r"], c=p["c"], h=p["h"], w=p["w"], z=p.get("z", 1),
                color_rgb=rgb,
                is_stud=p["is_stud"],
                origin_x=iso_center_x, origin_y=iso_origin_y,
                u_x=u_x, u_y=u_y, z_px=z_px,
                is_new_step=is_new
            )

    map_y0 = iso_section_h
    draw.rectangle([0, map_y0, page_w, page_h], fill=(238, 245, 250), outline=(255, 255, 255), width=4)

    color_usage = Counter(p["color_idx"] for p in surface_placements)
    color_num_map: dict[int, int] = {}
    for rank_idx, (c_idx, _) in enumerate(color_usage.most_common(), start=1):
        color_num_map[c_idx] = rank_idx

    leg_x0, leg_y0 = 24, map_y0 + 36
    leg_x1, leg_y1 = 420, page_h - 24
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
        sx = leg_x0 + 24 + sub_col * 185
        sy = leg_y0 + 24 + sub_row * 68

        draw.rounded_rectangle([sx, sy, sx + 44, sy + 44], radius=6, fill=rgb, outline=(60, 70, 80), width=2)
        num_str = str(key_num)
        draw.text((sx + (16 if len(num_str) == 1 else 11), sy + 13), num_str, fill=txt_col, font=font_qty)
        draw.text((sx + 56, sy + 13), f"{pcs_count}x", fill=(25, 32, 40), font=font_qty)

    grid_area_x0 = 460
    grid_area_y0 = map_y0 + 56
    max_grid_px = 1100
    cell_px = max(8, min(max_grid_px // max(h, w), 34))
    grid_w_px = w * cell_px
    grid_h_px = h * cell_px

    gx0 = grid_area_x0 + (1340 - grid_w_px) // 2
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

    quad_line_col = (220, 38, 38)
    for r_q in range(16, h, 16):
        qy = gy0 + r_q * cell_px
        draw.line([(gx0, qy), (gx0 + grid_w_px, qy)], fill=quad_line_col, width=3)
    for c_q in range(16, w, 16):
        qx = gx0 + c_q * cell_px
        draw.line([(qx, gy0), (qx, gy0 + grid_h_px)], fill=quad_line_col, width=3)

    draw.rectangle([gx0, gy0, gx0 + grid_w_px, gy0 + grid_h_px], outline=(20, 28, 36), width=3)

    manual.save(output_manual_path, format="PNG")
    return output_manual_path


# --- START OF TRUE-TONE COLOR CHANGE IN mosaic_engine.py ---
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
        # In 3D mode, use the 4.7 MB u2netp neural mask to isolate the subject from any background
        if z_layers > 1:
            neural_mask_256 = extract_neural_foreground_mask(img_cropped)
            if neural_mask_256 is not None:
                fg_mask_img = Image.fromarray((neural_mask_256.astype(np.uint8) * 255), mode="L").resize(
                    grid_size, Image.Resampling.NEAREST
                )
                fg_mask_grid = np.asarray(fg_mask_img) > 127

    # Detect thin boxed letter outlines & structural grooves at 512x512 BEFORE downsampling
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

    # Preserve boxed letter outlines (e.g. 'RE-GO' internal lines) by matching the darkest sub-pixels on groove cells
    dark_sub_lab = rgb2lab_numpy(dark_sub_rgb)
    dark_de = delta_e_ciede2000_numpy(
        dark_sub_lab[:, :, np.newaxis, :],
        palette_lab[np.newaxis, np.newaxis, :, :]
    )
    dark_indices = np.argmin(dark_de, axis=-1)
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
    # Boost edge_map on groove cells so denoise_and_smooth_grid never erases boxed letter outlines
    edge_map = np.where(groove_mask, np.max(edge_map) + 1.0, edge_map)
    nearest_indices = denoise_and_smooth_grid(
        raw_indices, delta_e, edge_map, merge_tolerance_de=merge_tolerance_de
    )

    effective_z = max(2, z_layers) if abstract_mode else z_layers

    # 1. Compute Boxed-Subject 3D Elevation Map first
    z_grid = compute_stable_terrace_z_grid(
        img_lab=img_lab,
        edge_map=edge_map,
        grid_size=grid_size,
        z_layers=effective_z,
        z_mode=z_mode,
        fg_mask_grid=fg_mask_grid,
        groove_mask=groove_mask,
    )

    # 2. Put tactile studs on elevated boxed letters/surfaces, and smooth flat tiles in recessed grooves & background
    if effective_z > 1:
        stud_mask = (z_grid == np.max(z_grid)) & (~groove_mask)
    else:
        threshold = np.quantile(edge_map, 1.0 - stud_ratio)
        stud_mask = (edge_map >= threshold) & (~groove_mask)

    if abstract_mode and fg_mask_grid is not None:
        stud_mask = stud_mask & fg_mask_grid
        stud_mask[0, :] = False
        stud_mask[-1, :] = False
        stud_mask[:, 0] = False
        stud_mask[:, -1] = False

    # 3. Pack each layer from Z=1 to effective_z with 90-degree cross-seam interlocking
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

    total_studs = int(np.sum(z_grid))
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