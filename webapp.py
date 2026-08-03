"""
DropTag web app — SaaS-style UI for SEO image tagging.

Run:  py -m uvicorn webapp:app --host 127.0.0.1 --port 7860
Or double-click run_web.bat
"""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from add_keywords import (
    SUPPORTED,
    make_seo_filename,
    parse_keyword_list,
    process_image,
    unique_dest,
)

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="DropTag", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/", response_class=HTMLResponse)
def home() -> FileResponse:
    index = STATIC / "index.html"
    if not index.exists():
        raise HTTPException(500, "UI missing: static/index.html")
    return FileResponse(index)


@app.post("/api/process")
async def process(
    files: list[UploadFile] = File(...),
    title: str = Form(""),
    description: str = Form(""),
    keywords: str = Form(""),
    rating: int = Form(5),
) -> StreamingResponse:
    title = (title or "").strip()
    description = (description or "").strip()
    keyword_list = parse_keyword_list(keywords)
    rating = max(1, min(5, int(rating or 5)))

    if not files:
        raise HTTPException(400, "Upload at least one image.")
    if not keyword_list:
        raise HTTPException(400, "Add at least one keyword.")

    # Filter to supported image types
    uploads: list[UploadFile] = []
    for f in files:
        name = f.filename or "image.png"
        ext = Path(name).suffix.lower()
        if ext in SUPPORTED:
            uploads.append(f)
    if not uploads:
        raise HTTPException(
            400,
            f"No supported images. Use: {', '.join(sorted(SUPPORTED))}",
        )

    with tempfile.TemporaryDirectory(prefix="droptag_") as tmp:
        tmp_path = Path(tmp)
        in_dir = tmp_path / "in"
        out_dir = tmp_path / "out"
        in_dir.mkdir()
        out_dir.mkdir()

        used_names: set[str] = set()
        outputs: list[Path] = []

        for upload in uploads:
            original_name = upload.filename or "image.png"
            # sanitize upload name for temp disk
            safe = re.sub(r"[^\w.\-]+", "_", original_name)
            src = in_dir / safe
            data = await upload.read()
            if not data:
                continue
            src.write_bytes(data)

            stem = make_seo_filename(title, keyword_list, src.stem)
            dest = unique_dest(out_dir, stem, used_names)
            try:
                process_image(src, dest, keyword_list, title, description, rating)
                outputs.append(dest)
            except Exception as exc:
                raise HTTPException(
                    500, f"Failed on {original_name}: {exc}"
                ) from exc

        if not outputs:
            raise HTTPException(400, "No images could be processed.")

        if len(outputs) == 1:
            content = outputs[0].read_bytes()
            filename = outputs[0].name
            return StreamingResponse(
                io.BytesIO(content),
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                },
            )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in outputs:
                zf.write(path, arcname=path.name)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="droptag-images.zip"'
            },
        )
