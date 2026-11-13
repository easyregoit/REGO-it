import base64
import hashlib
import os
import tempfile
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFilter
from mosaic_engine import generate_brick_mosaic, export_bricklink_xml, create_demo_image

app = FastAPI(title="REGO Mosaic Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERNAL_UNLOCK_SECRET = os.getenv("INTERNAL_UNLOCK_SECRET", "rego_unlock_8492019482_x9k2m7p4")
ORDERS_DIR = os.path.join(tempfile.gettempdir(), "rego_orders")
os.makedirs(ORDERS_DIR, exist_ok=True)

PRESET_MAP = {
    "auto": None,
    "frame_32": (32, 32),
    "small_48": (48, 48),
    "medium_64": (64, 64),
    "large_96": (96, 96),
    "xl_128": (128, 128),
}


def make_peek_preview(img_path: str, blur_radius: int = 16) -> str:
    """Heavily blurs 85% of the mosaic while keeping a razor-sharp HD center peek window."""
    img = Image.open(img_path).convert("RGB")
    sharp = img.resize((1200, 1200), Image.Resampling.LANCZOS)
    blurred = sharp.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    box = (400, 400, 800, 800)
    blurred.paste(sharp.crop(box), box)
    draw = ImageDraw.Draw(blurred)
    draw.rectangle(box, outline=(255, 200, 50), width=4)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        blurred.save(tmp.name, format="PNG")
        with open(tmp.name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    os.remove(tmp.name)
    return f"data:image/png;base64,{b64}"


@app.get("/")
def serve_home():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(script_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "REGO Mosaic Studio Python API v3 (Demo + Isometric Manual + 3D Layers) is running"}


@app.get("/api/demo-image")
def get_demo_image():
    """Returns the built-in RE-GO demo PNG so the frontend can load it with 1 click."""
    demo_path = os.path.join(ORDERS_DIR, "builtin_demo.png")
    create_demo_image(demo_path)
    return FileResponse(demo_path, media_type="image/png", filename="rego_demo.png")


@app.post("/api/generate")
async def create_mosaic(
    file: UploadFile | None = File(default=None),
    preset: str = Form("auto"),
    stud_ratio: float = Form(0.45),
    merge_tolerance: float = Form(2.2),
    z_layers: int = Form(1),
    z_mode: str = Form("luminance"),
    abstract_mode: bool = Form(False),
    use_demo: bool = Form(False),
):
    safe_z = max(1, min(4, int(z_layers)))

    if use_demo or file is None:
        demo_tmp = os.path.join(ORDERS_DIR, "builtin_demo.png")
        create_demo_image(demo_tmp)
        with open(demo_tmp, "rb") as df:
            file_bytes = df.read()
    else:
        file_bytes = await file.read()

    sig = (
        file_bytes[:4096]
        + str(len(file_bytes)).encode()
        + f"_{preset}_{stud_ratio}_z{safe_z}_{z_mode}_abs{abstract_mode}".encode()
    )
    order_id = hashlib.md5(sig).hexdigest()[:12]

    input_path = os.path.join(ORDERS_DIR, f"{order_id}_in.png")
    output_png = os.path.join(ORDERS_DIR, f"{order_id}_hd.png")
    output_manual = os.path.join(ORDERS_DIR, f"{order_id}_manual.png")
    output_xml = os.path.join(ORDERS_DIR, f"{order_id}_parts.xml")

    with open(input_path, "wb") as f:
        f.write(file_bytes)

    grid_size = (32, 32) if abstract_mode else PRESET_MAP.get(preset, None)
    bom, final_grid, total_studs = generate_brick_mosaic(
        input_path=input_path,
        output_path=output_png,
        grid_size=grid_size,
        target_output_px=1920,
        stud_ratio=stud_ratio,
        merge_tolerance_de=merge_tolerance,
        pre_sharpen=False,
        z_layers=safe_z,
        z_mode=z_mode,
        abstract_mode=abstract_mode,
        manual_output_path=output_manual,
    )

    xml_string = export_bricklink_xml(
        bom=bom,
        xml_output_path=output_xml,
        grid_size=final_grid,
        include_baseplates=True,
        condition="N",
    )

    if os.path.exists(input_path):
        os.remove(input_path)

    with open(output_png, "rb") as img_f:
        hd_b64 = f"data:image/png;base64,{base64.b64encode(img_f.read()).decode('utf-8')}"

    with open(output_manual, "rb") as man_f:
        manual_b64 = f"data:image/png;base64,{base64.b64encode(man_f.read()).decode('utf-8')}"

    peek_b64 = make_peek_preview(output_png, blur_radius=16)
    total_pieces = sum(bom.values())
    reduction_pct = round((1.0 - (total_pieces / max(1, total_studs))) * 100.0, 1)
    is_3d = safe_z > 1 or abstract_mode

    if abstract_mode:
        price_usd = 2.99
    elif safe_z > 1:
        price_usd = 7.99
    else:
        price_usd = 4.99

    parts_summary = [
        {
            "color_id": cid,
            "color_name": cname,
            "part_id": pid,
            "part_name": pname,
            "count": count,
        }
        for (cid, cname, pid, pname), count in list(bom.items())[:25]
    ]

    return {
        "order_id": order_id,
        "grid": f"{final_grid[0]}x{final_grid[1]} Frame" if abstract_mode else (f"{final_grid[0]}x{final_grid[1]}x{safe_z}" if is_3d else f"{final_grid[0]}x{final_grid[1]}"),
        "is_3d": is_3d,
        "abstract_mode": abstract_mode,
        "price_usd": price_usd,
        "total_studs": total_studs,
        "total_pieces": total_pieces,
        "reduction_pct": reduction_pct,
        "blurred_preview_image": peek_b64,
        "preview_image": hd_b64,
        "hd_image": hd_b64,
        "manual_image": manual_b64,
        "xml_content": xml_string,
        "top_parts": parts_summary,
        "parts_breakdown": parts_summary,
    }


@app.get("/api/unlock/{order_id}")
def unlock_order(order_id: str, x_internal_secret: str = Header(default="")):
    if x_internal_secret != INTERNAL_UNLOCK_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized unlock request")

    output_png = os.path.join(ORDERS_DIR, f"{order_id}_hd.png")
    output_manual = os.path.join(ORDERS_DIR, f"{order_id}_manual.png")
    output_xml = os.path.join(ORDERS_DIR, f"{order_id}_parts.xml")

    if not os.path.exists(output_png) or not os.path.exists(output_xml):
        raise HTTPException(status_code=404, detail="Order expired or not found. Please regenerate.")

    with open(output_png, "rb") as img_f:
        hd_b64 = base64.b64encode(img_f.read()).decode("utf-8")
    with open(output_xml, "r", encoding="utf-8") as xml_f:
        xml_string = xml_f.read()

    manual_b64 = ""
    if os.path.exists(output_manual):
        with open(output_manual, "rb") as man_f:
            manual_b64 = f"data:image/png;base64,{base64.b64encode(man_f.read()).decode('utf-8')}"

    return {
        "order_id": order_id,
        "preview_image": f"data:image/png;base64,{hd_b64}",
        "hd_image": f"data:image/png;base64,{hd_b64}",
        "manual_image": manual_b64,
        "xml_content": xml_string,
    }