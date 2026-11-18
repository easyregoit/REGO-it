import asyncio
import base64
import hashlib
import hmac
import re
import fcntl
from contextlib import contextmanager
import json
import os
import tempfile
import threading
import time
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFilter
from mosaic_engine import generate_brick_mosaic, export_bricklink_xml, create_demo_image
from role_bot import bot as discord_bot, TOKEN as DISCORD_TOKEN

app = FastAPI(title="REGO Mosaic Studio API")


@app.on_event("startup")
async def start_discord_bot_in_background():
    if DISCORD_TOKEN:
        asyncio.create_task(discord_bot.start(DISCORD_TOKEN))
        print("Started REGO Role Bot background task on Render.")
    else:
        print("DISCORD_BOT_TOKEN not set; skipping Discord bot startup.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERNAL_UNLOCK_SECRET = os.getenv("INTERNAL_UNLOCK_SECRET")
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


def _build_mosaic_payload(
    input_path: str,
    order_id: str,
    grid_size: tuple[int, int] | None,
    stud_ratio: float,
    merge_tolerance: float,
    safe_z: int,
    z_mode: str,
    abstract_mode: bool,
    is_demo: bool = False,
) -> dict:
    output_png = os.path.join(ORDERS_DIR, f"{order_id}_hd.png")
    output_manual = os.path.join(ORDERS_DIR, f"{order_id}_manual.png")
    output_xml = os.path.join(ORDERS_DIR, f"{order_id}_parts.xml")

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

    with open(output_png, "rb") as img_f:
        hd_b64 = f"data:image/png;base64,{base64.b64encode(img_f.read()).decode('utf-8')}"

    with open(output_manual, "rb") as man_f:
        manual_b64 = f"data:image/png;base64,{base64.b64encode(man_f.read()).decode('utf-8')}"

    peek_b64 = hd_b64 if is_demo else make_peek_preview(output_png, blur_radius=16)
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
        "is_demo": is_demo,
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


@app.get("/")
def serve_home():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(script_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "REGO Mosaic Studio Python API v5 (Live Stripe + Everyone Mosaic 128x64) is running"}


@app.get("/api/demo-image")
def get_demo_image():
    demo_path = os.path.join(ORDERS_DIR, "builtin_demo.png")
    create_demo_image(demo_path)
    return FileResponse(demo_path, media_type="image/png", filename="rego_demo.png")


@app.get("/api/demo")
def get_mandatory_demo_showcase():
    demo_path = os.path.join(ORDERS_DIR, "builtin_demo.png")
    create_demo_image(demo_path)
    return _build_mosaic_payload(
        input_path=demo_path,
        order_id="demo_rego_3d",
        grid_size=(64, 64),
        stud_ratio=0.45,
        merge_tolerance=2.2,
        safe_z=3,
        z_mode="luminance",
        abstract_mode=False,
        is_demo=True,
    )


@app.post("/api/generate")
async def create_mosaic(
    file: UploadFile | None = File(default=None),
    preset: str = Form("auto"),
    stud_ratio: float = Form(0.45),
    merge_tolerance: float = Form(2.2),
    z_layers: int = Form(3),
    z_mode: str = Form("luminance"),
    abstract_mode: bool = Form(False),
    use_demo: bool = Form(False),
):
    try:
        safe_z = max(1, min(4, int(z_layers)))
        fname = getattr(file, "filename", "") or ""
        is_demo = use_demo or (file is None) or (fname == "") or ("rego_demo" in fname.lower())

        if is_demo and (file is None or fname == ""):
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

        with open(input_path, "wb") as f:
            f.write(file_bytes)

        if abstract_mode:
            grid_size = (32, 32)
        elif preset in PRESET_MAP and PRESET_MAP[preset] is not None:
            grid_size = PRESET_MAP[preset]
        elif is_demo:
            grid_size = (64, 64)
        else:
            grid_size = None

        result = _build_mosaic_payload(
            input_path=input_path,
            order_id=order_id,
            grid_size=grid_size,
            stud_ratio=stud_ratio,
            merge_tolerance=merge_tolerance,
            safe_z=safe_z,
            z_mode=z_mode,
            abstract_mode=abstract_mode,
            is_demo=is_demo,
        )

        if os.path.exists(input_path):
            os.remove(input_path)

        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/unlock/{order_id}")
def unlock_order(order_id: str, x_internal_secret: str = Header(default="")):
    if not INTERNAL_UNLOCK_SECRET or x_internal_secret != INTERNAL_UNLOCK_SECRET:
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


# ============================================================================
# THE EVERYONE MOSAIC (128x64 Collaborative Canvas — $0.50 per 1x1 Tile)
# ============================================================================
EVERYONE_FILE = os.path.join(ORDERS_DIR, "everyone_mosaic_128x64.json")
EVERYONE_LOCK = threading.Lock()
LOCK_TTL_SECONDS = 300


@contextmanager
def _board_transaction():
    with EVERYONE_LOCK, open(EVERYONE_FILE + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _load_everyone_state() -> dict:
    if os.path.exists(EVERYONE_FILE):
        try:
            with open(EVERYONE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("paid_cells", {})
                data.setdefault("active_locks", {})
                return data
        except (OSError, ValueError) as exc:
            raise HTTPException(503, 'Board storage unavailable') from exc
    return {"paid_cells": {}, "active_locks": {}}


def _save_everyone_state(state: dict) -> None:
    with open(EVERYONE_FILE + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(EVERYONE_FILE + '.tmp', EVERYONE_FILE)


def _purge_expired_locks(state: dict) -> bool:
    now = time.time()
    expired = [k for k, v in state["active_locks"].items() if v.get("expires_at", 0) < now]
    for k in expired:
        del state["active_locks"][k]
    return len(expired) > 0


def _parse_cell_coords(item: dict) -> tuple[int, int]:
    if "cell_key" in item or "cellKey" in item or "key" in item:
        raw_key = str(item.get("cell_key") or item.get("cellKey") or item.get("key"))
        parts = raw_key.replace(":", ",").split(",")
        return int(parts[0]), int(parts[1])
    r = int(item.get("r", item.get("row", item.get("y", 0))))
    c = int(item.get("c", item.get("col", item.get("x", 0))))
    return r, c


def _format_state_response(state: dict, /, **extra) -> dict:
    cells = {k: {field: value for field, value in row.items() if field not in ('payment_intent', 'session_id')} for k, row in state['paid_cells'].items()}
    if 'state' in extra:
        extra['state'] = {'paid_cells': cells, 'active_locks': state['active_locks']}
    return {
        "ok": True,
        "paid_cells": cells,
        "paidCells": cells,
        "cells": cells,
        "active_locks": state["active_locks"],
        "activeLocks": state["active_locks"],
        "locks": state["active_locks"],
        "paid_count": len(state["paid_cells"]),
        **extra,
    }


@app.get("/api/everyone/state")
async def get_everyone_state():
    with _board_transaction():
        state = _load_everyone_state()
        if _purge_expired_locks(state):
            _save_everyone_state(state)
        return _format_state_response(state)


@app.post("/api/everyone/lock")
async def lock_everyone_cell(req: Request):
    body = await req.json()
    client_id = str(body.get("client_id") or body.get("clientId") or "anon")
    action = str(body.get("action") or "").lower()
    is_release = action in ("release", "unlock", "remove") or body.get("release") is True or body.get("unlock") is True
    now = time.time()

    raw_items = body.get("items") or body.get("tiles") or body.get("cells")
    if not raw_items:
        raw_items = [body]

    with _board_transaction():
        state = _load_everyone_state()
        _purge_expired_locks(state)

        for item in raw_items:
            r, c = _parse_cell_coords(item)
            if not (0 <= r < 64 and 0 <= c < 128):
                raise HTTPException(status_code=400, detail=f"Coordinates ({r},{c}) out of 128x64 bounds.")
            cell_key = f"{r},{c}"

            if is_release:
                existing = state["active_locks"].get(cell_key)
                if existing and existing.get("client_id") == client_id:
                    del state["active_locks"][cell_key]
                continue

            if cell_key in state["paid_cells"]:
                raise HTTPException(status_code=409, detail=f"Box ({r},{c}) is already purchased.")

            existing = state["active_locks"].get(cell_key)
            if existing and existing.get("client_id") != client_id:
                raise HTTPException(status_code=409, detail=f"Box ({r},{c}) is currently locked by another builder.")

            piece = item.get("piece") or {
                "part_key": item.get("part_key") or item.get("partKey") or item.get("shape") or "tile_1x1",
                "color_id": item.get("color_id") or item.get("colorId") or item.get("color") or 1,
                "orient": item.get("orient") or item.get("orientation") or item.get("rotation"),
                "hex": item.get("hex"),
            }

            state["active_locks"][cell_key] = {
                "r": r,
                "c": c,
                "client_id": client_id,
                "clientId": client_id,
                "piece": piece,
                "expires_at": now + LOCK_TTL_SECONDS,
                "expiresAt": int((now + LOCK_TTL_SECONDS) * 1000),
            }

        _save_everyone_state(state)
        return _format_state_response(state, state=state)


@app.post("/api/everyone/release")
@app.post("/api/everyone/unlock")
async def release_everyone_cell(req: Request):
    body = await req.json()
    client_id = str(body.get("client_id") or body.get("clientId") or "anon")
    raw_items = body.get("items") or body.get("tiles") or body.get("cells") or [body]

    with _board_transaction():
        state = _load_everyone_state()
        for item in raw_items:
            r, c = _parse_cell_coords(item)
            cell_key = f"{r},{c}"
            existing = state["active_locks"].get(cell_key)
            if existing and existing.get("client_id") == client_id:
                del state["active_locks"][cell_key]
        _save_everyone_state(state)
        return _format_state_response(state, state=state)


@app.post('/api/everyone/moderate')
async def moderate_board(req: Request, x_internal_secret: str = Header(default='')):
    if not INTERNAL_UNLOCK_SECRET or not hmac.compare_digest(x_internal_secret.encode(), INTERNAL_UNLOCK_SECRET.encode()):
        raise HTTPException(403, 'Creator access required')
    body = await req.json()
    op = req.headers.get('idempotency-key', '')
    if not re.fullmatch(r'[a-f0-9-]{36}', op):
        raise HTTPException(400, 'Operation ID required')
    with _board_transaction():
        state = _load_everyone_state()
        ledger = state.setdefault('moderations', {})
        pending = next((key for key, value in ledger.items() if not value.get('done')), None)
        if body.get('inspect'):
            return {'pending': pending}
        receipt = ledger.get(op)
        if body.get('complete'):
            if not receipt:
                raise HTTPException(404, 'Unknown operation')
            receipt['done'] = True
            _save_everyone_state(state)
            return {'ok': True}
        if receipt:
            return receipt
        if pending:
            raise HTTPException(409, 'Finish the pending refund first')
        cells = body.get('cells')
        if not isinstance(cells, list) or not 0 < len(cells) <= 8192:
            raise HTTPException(400, 'Select valid boxes')
        for key in cells:
            if not isinstance(key, str) or not re.fullmatch(r'(0|[1-9]\d?),(0|[1-9]\d{0,2})', key) or int(key.split(',')[0]) >= 64 or int(key.split(',')[1]) >= 128:
                raise HTTPException(400, 'Invalid coordinate')
        paid, released = [], 0
        for key in dict.fromkeys(cells):
            row = state['paid_cells'].pop(key, None)
            if row:
                if not row.get('payment_intent') or not row.get('session_id'):
                    raise HTTPException(409, 'Selection includes a legacy purchase; reconcile its payment first')
                paid.append({'cell': key, 'payment_intent': row['payment_intent']})
                state.setdefault('removed_sessions', {}).setdefault(row['session_id'], []).append(key)
            released += int(state['active_locks'].pop(key, None) is not None)
        ledger[op] = receipt = {'paid_items': paid, 'released': released, 'cells': list(dict.fromkeys(cells)), 'done': False}
        _save_everyone_state(state)
        return receipt


@app.post("/api/everyone/commit")
@app.post("/api/everyone/save")
async def commit_everyone_cells(
    req: Request,
    x_internal_secret: str = Header(default=""),
    authorization: str = Header(default=""),
):
    bearer = authorization.replace("Bearer ", "").strip() if authorization else ""
    body = await req.json()
    provided_secret = x_internal_secret or bearer or str(body.get("secret") or "")

    if not INTERNAL_UNLOCK_SECRET or not hmac.compare_digest(provided_secret.encode(), INTERNAL_UNLOCK_SECRET.encode()):
        raise HTTPException(status_code=403, detail='Unauthorized commit request')
    intent, session = body.get('payment_intent'), body.get('session_id')
    if not isinstance(intent, str) or not re.fullmatch(r'pi_[A-Za-z0-9]+', intent) or not isinstance(session, str) or not re.fullmatch(r'cs_[\w]+', session):
        raise HTTPException(400, 'Verified payment references required')

    raw_items = body.get("items") or body.get("tiles") or body.get("cells") or []

    with _board_transaction():
        state = _load_everyone_state()
        for item in raw_items:
            r, c = _parse_cell_coords(item)
            if not (0 <= r < 64 and 0 <= c < 128):
                continue
            cell_key = f"{r},{c}"
            if cell_key in state.get('removed_sessions', {}).get(session, []):
                raise HTTPException(409, 'Placement has been moderated')
            existing = state['paid_cells'].get(cell_key)
            if existing and existing.get('session_id') != session:
                raise HTTPException(409, 'Box already purchased')
            piece = item.get("piece") if isinstance(item.get("piece"), dict) else item
            part_key = piece.get("part_key") or piece.get("partKey") or piece.get("shape") or "tile_1x1"
            color_id = piece.get('color_id') or piece.get('colorId') or piece.get('color') or 1
            orient = piece.get("orient") or piece.get("orientation") or piece.get("rotation")
            hex_val = piece.get("hex")

            state["paid_cells"][cell_key] = {
                "r": r,
                "c": c,
                "part_key": part_key,
                "partKey": part_key,
                "color_id": color_id,
                "colorId": color_id,
                "orient": orient,
                "orientation": orient,
                "hex": hex_val,
                'session_id': session, 'payment_intent': intent, 'piece': piece,
                "paid_at": int(time.time()),
            }
            state["active_locks"].pop(cell_key, None)

        _save_everyone_state(state)
        return _format_state_response(state, state=state)
