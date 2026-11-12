import base64
import hashlib
import os
import tempfile
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFilter
from mosaic_engine import generate_brick_mosaic, export_bricklink_xml

app = FastAPI(title="REGO Mosaic Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERNAL_UNLOCK_SECRET = os.getenv("INTERNAL_UNLOCK_SECRET", "change-me-in-render-and-vercel")
ORDERS_DIR = os.path.join(tempfile.gettempdir(), "rego_orders")
os.makedirs(ORDERS_DIR, exist_ok=True)

PRESET_MAP = {
    "auto": None,
    "small_48": (48, 48),
    "medium_64": (64, 64),
    "large_96": (96, 96),
    "xl_128": (128, 128),
}


def make_peek_preview(img_path: str, blur_radius: int = 6) -> str:
    img = Image.open(img_path).convert("RGB")
    sharp = img.resize((700, 700), Image.Resampling.BILINEAR)
    blurred = sharp.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    box = (230, 230, 470, 470)
    blurred.paste(sharp.crop(box), box)
    draw = ImageDraw.Draw(blurred)
    draw.rectangle(box, outline=(255, 200, 50), width=3)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        blurred.save(tmp.name, format="PNG")
        with open(tmp.name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    os.remove(tmp.name)
    return f"data:image/png;base64,{b64}"


@app.get("/")
def health_check():
    return {"status": "REGO Mosaic Studio Python API is running"}


@app.post("/api/generate")
async def create_mosaic(
    file: UploadFile = File(...),
    preset: str = Form("auto"),
    stud_ratio: float = Form(0.45),
    merge_tolerance: float = Form(4.2),
    z_layers: int = Form(1),
    z_mode: str = Form("luminance"),
):
    file_bytes = await file.read()
    safe_z = max(1, min(4, int(z_layers)))
    sig = file_bytes[:4096] + str(len(file_bytes)).encode() + f"_{preset}_{stud_ratio}_z{safe_z}_{z_mode}".encode()
    order_id = hashlib.md5(sig).hexdigest()[:12]

    input_path = os.path.join(ORDERS_DIR, f"{order_id}_in.png")
    output_png = os.path.join(ORDERS_DIR, f"{order_id}_hd.png")
    output_xml = os.path.join(ORDERS_DIR, f"{order_id}_parts.xml")

    with open(input_path, "wb") as f:
        f.write(file_bytes)

    grid_size = PRESET_MAP.get(preset, None)
    bom, final_grid, total_studs = generate_brick_mosaic(
        input_path=input_path,
        output_path=output_png,
        grid_size=grid_size,
        target_output_px=1920,
        stud_ratio=stud_ratio,
        merge_tolerance_de=merge_tolerance,
        pre_sharpen=True,
        z_layers=safe_z,
        z_mode=z_mode,
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

    peek_b64 = make_peek_preview(output_png, blur_radius=6)
    total_pieces = sum(bom.values())
    reduction_pct = round((1.0 - (total_pieces / max(1, total_studs))) * 100.0, 1)
    is_3d = safe_z > 1

    return {
        "order_id": order_id,
        "grid": f"{final_grid[0]}x{final_grid[1]}x{safe_z}" if is_3d else f"{final_grid[0]}x{final_grid[1]}",
        "is_3d": is_3d,
        "price_usd": 7.99 if is_3d else 4.99,
        "total_studs": total_studs,
        "total_pieces": total_pieces,
        "reduction_pct": reduction_pct,
        "preview_image": peek_b64,
        "blurred_preview_image": peek_b64,
        "xml_content": xml_string,
    }

s
@app.get("/api/unlock/{order_id}")
def unlock_order(order_id: str, x_internal_secret: str = Header(default="")):
    if x_internal_secret != INTERNAL_UNLOCK_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized unlock request")

    output_png = os.path.join(ORDERS_DIR, f"{order_id}_hd.png")
    output_xml = os.path.join(ORDERS_DIR, f"{order_id}_parts.xml")

    if not os.path.exists(output_png) or not os.path.exists(output_xml):
        raise HTTPException(status_code=404, detail="Order expired or not found. Please regenerate.")

    with open(output_png, "rb") as img_f:
        hd_b64 = base64.b64encode(img_f.read()).decode("utf-8")
    with open(output_xml, "r", encoding="utf-8") as xml_f:
        xml_string = xml_f.read()

    return {
        "order_id": order_id,
        "preview_image": f"data:image/png;base64,{hd_b64}",
        "xml_content": xml_string,
    }
