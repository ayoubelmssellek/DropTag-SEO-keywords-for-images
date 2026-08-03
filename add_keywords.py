"""
Add SEO keywords (and optional title/description) into image metadata.

Easy use:
  1. Put images in the "images" folder
  2. Edit keywords.txt
  3. Double-click run.bat

Tagged images are saved as JPG in the "output" folder
(Windows shows Title / Tags reliably on JPG, not on PNG).
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

try:
    import piexif
    from iptcinfo3 import IPTCInfo
    from PIL import Image
except ImportError:
    print("Missing packages. Run this first:")
    print("  py -m pip install -r requirements.txt")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
IMAGES_DIR = ROOT / "images"
OUTPUT_DIR = ROOT / "output"
KEYWORDS_FILE = ROOT / "keywords.txt"

SUPPORTED = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".webp", ".bmp"}


def parse_keywords_file(path: Path) -> tuple[list[str], str, str, int]:
    """Read keywords.txt → (keywords, title, description, rating 1-5)."""
    if not path.exists():
        return [], "", "", 5

    title = ""
    description = ""
    rating = 5
    raw_parts: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            upper = line.lstrip("#").strip()
            if upper.upper().startswith("TITLE:"):
                title = upper.split(":", 1)[1].strip()
            elif upper.upper().startswith("DESCRIPTION:"):
                description = upper.split(":", 1)[1].strip()
            elif upper.upper().startswith("RATING:"):
                rating = _parse_rating(upper.split(":", 1)[1].strip())
            continue

        if line.upper().startswith("TITLE:"):
            title = line.split(":", 1)[1].strip()
            continue
        if line.upper().startswith("DESCRIPTION:"):
            description = line.split(":", 1)[1].strip()
            continue
        if line.upper().startswith("RATING:"):
            rating = _parse_rating(line.split(":", 1)[1].strip())
            continue

        raw_parts.append(line)

    keywords: list[str] = []
    for part in raw_parts:
        for piece in re.split(r"[,;]+", part):
            word = piece.strip()
            if word and word not in keywords:
                keywords.append(word)

    return keywords, title, description, rating


def _parse_rating(value: str) -> int:
    """Accept 1-5 (stars). Default 5."""
    try:
        n = int(float(value.strip()))
    except ValueError:
        return 5
    return max(1, min(5, n))


def make_seo_filename(title: str, keywords: list[str], original_stem: str) -> str:
    """
    Build an SEO-friendly file name from TITLE (preferred) or keywords.
    Example: 'Red running shoes product photo' → 'red-running-shoes-product-photo'
    """
    base = title.strip() if title.strip() else " ".join(keywords[:6])
    if not base:
        base = original_stem

    # Keep letters/numbers; turn other chars into dashes
    slug = base.lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")

    # Windows file name limit safety
    if len(slug) > 80:
        slug = slug[:80].rstrip("-")
    if not slug:
        slug = "image"
    return slug


def parse_keyword_list(text: str) -> list[str]:
    """Split a free-text keyword string into a clean list."""
    keywords: list[str] = []
    for piece in re.split(r"[,;\n]+", text or ""):
        word = piece.strip()
        if word and word not in keywords:
            keywords.append(word)
    return keywords


def unique_dest(folder: Path, stem: str, used: set[str] | None = None) -> Path:
    """Avoid overwriting: name.jpg, name-2.jpg, name-3.jpg..."""
    used = used if used is not None else set()
    candidate = folder / f"{stem}.jpg"
    n = 2
    while candidate.name.lower() in used or candidate.exists():
        candidate = folder / f"{stem}-{n}.jpg"
        n += 1
    used.add(candidate.name.lower())
    return candidate


def collect_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return [
        p
        for p in sorted(folder.iterdir())
        if p.is_file() and p.suffix.lower() in SUPPORTED
    ]


def _utf16le_null(text: str) -> bytes:
    return text.encode("utf-16le") + b"\x00\x00"


# Windows maps these % values to 1–5 stars
_RATING_PERCENT = {1: 1, 2: 25, 3: 50, 4: 75, 5: 99}


def build_exif(
    keywords: list[str], title: str, description: str, rating: int = 5
) -> bytes:
    exif_dict: dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    joined = "; ".join(keywords)
    exif_dict["0th"][piexif.ImageIFD.XPKeywords] = _utf16le_null(joined)
    if title:
        exif_dict["0th"][piexif.ImageIFD.XPTitle] = _utf16le_null(title)
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = title.encode("utf-8")
        # Subject (shown next to Title in Windows)
        exif_dict["0th"][piexif.ImageIFD.XPSubject] = _utf16le_null(title)
    if description:
        exif_dict["0th"][piexif.ImageIFD.XPComment] = _utf16le_null(description)

    rating = max(1, min(5, int(rating)))
    exif_dict["0th"][piexif.ImageIFD.Rating] = rating
    exif_dict["0th"][piexif.ImageIFD.RatingPercent] = _RATING_PERCENT[rating]
    return piexif.dump(exif_dict)


def write_iptc(path: Path, keywords: list[str], title: str, description: str) -> None:
    info = IPTCInfo(str(path), force=True)
    info["keywords"] = keywords
    if title:
        info["object name"] = title
        info["headline"] = title
    if description:
        info["caption/abstract"] = description
    info.save()


def process_image(
    src: Path,
    dest: Path,
    keywords: list[str],
    title: str,
    description: str,
    rating: int = 5,
) -> None:
    """
    Always save as JPG with IPTC + Windows EXIF tags.
    PNG text chunks do NOT show in Windows Properties → Details.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    exif_bytes = build_exif(keywords, title, description, rating)

    with Image.open(src) as im:
        # JPG needs RGB (no alpha)
        if im.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", im.size, (255, 255, 255))
            rgba = im.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            rgb = background
        else:
            rgb = im.convert("RGB")

        rgb.save(dest, format="JPEG", quality=95, exif=exif_bytes)

    write_iptc(dest, keywords, title, description)

    # Re-insert EXIF after IPTC save (iptcinfo can strip some EXIF)
    piexif.insert(exif_bytes, str(dest))

    # iptcinfo3 leaves a "file~" backup — remove it
    backup = Path(str(dest) + "~")
    if backup.exists():
        backup.unlink()


def read_back(path: Path) -> None:
    """Print what Windows-style tags we wrote (for confirmation)."""
    try:
        exif = piexif.load(str(path))
        zeroth = exif.get("0th") or {}

        def xp(tag: int) -> str:
            raw = zeroth.get(tag)
            if not raw:
                return "(empty)"
            if isinstance(raw, tuple):
                raw = bytes(raw)
            return raw.decode("utf-16le", errors="ignore").rstrip("\x00")

        rating = zeroth.get(piexif.ImageIFD.Rating, "(empty)")
        print("  --- check ---")
        print(f"  Title   : {xp(piexif.ImageIFD.XPTitle)}")
        print(f"  Tags    : {xp(piexif.ImageIFD.XPKeywords)}")
        print(f"  Comment : {xp(piexif.ImageIFD.XPComment)}")
        print(f"  Rating  : {rating} star(s)")
    except Exception as exc:
        print(f"  (could not read back tags: {exc})")


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def main() -> None:
    print("=" * 50)
    print("  Add Keywords to Images (SEO helper)")
    print("=" * 50)
    print()

    IMAGES_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    keywords, title, description, rating = parse_keywords_file(KEYWORDS_FILE)

    print(f"Keywords file : {KEYWORDS_FILE.name}")
    if keywords:
        shown = ", ".join(keywords[:8]) + (" ..." if len(keywords) > 8 else "")
        print(f"Found {len(keywords)} keyword(s): {shown}")
    else:
        print("No keywords found in keywords.txt yet.")

    if title:
        print(f"Title         : {title}")
    if description:
        print(f"Description   : {description}")
    print(f"Rating        : {rating} star(s)")
    print()
    print("Note: output is always JPG so Windows shows Title/Tags.")
    print()

    images = collect_images(IMAGES_DIR)
    if images:
        print(f"Found {len(images)} image(s) in the 'images' folder.")
        use_folder = ask("Use the images folder? (y/n)", "y").lower().startswith("y")
    else:
        use_folder = False
        print("The 'images' folder is empty.")

    if use_folder:
        targets = images
    else:
        path_str = ask("Paste the full path to ONE image file")
        path = Path(path_str.strip().strip('"'))
        if not path.exists() or not path.is_file():
            print(f"File not found: {path}")
            sys.exit(1)
        if path.suffix.lower() not in SUPPORTED:
            print(f"Unsupported type. Use: {', '.join(sorted(SUPPORTED))}")
            sys.exit(1)
        targets = [path]

    if not keywords:
        typed = ask("Type keywords separated by commas")
        keywords = [k.strip() for k in re.split(r"[,;]+", typed) if k.strip()]

    if not keywords:
        print("No keywords given. Nothing to do.")
        sys.exit(1)

    if not title:
        title = ask("Title (optional, press Enter to skip)", "")
    if not description:
        description = ask("Description (optional, press Enter to skip)", "")

    print()
    print("Working...")
    ok = 0
    for src in targets:
        seo_stem = make_seo_filename(title, keywords, src.stem)
        dest = unique_dest(OUTPUT_DIR, seo_stem)
        try:
            process_image(src, dest, keywords, title, description, rating)
            print(f"  OK  {src.name}")
            print(f"   →  {dest.name}")
            read_back(dest)
            ok += 1
        except Exception as exc:
            print(f"  FAIL  {src.name}: {exc}")

    print()
    print(f"Done! {ok}/{len(targets)} image(s) saved in:")
    print(f"  {OUTPUT_DIR}")
    print()
    print("IMPORTANT: open the .jpg file inside the OUTPUT folder")
    print("(not the original PNG in images).")
    print("Right-click → Properties → Details → SCROLL DOWN")
    print("to see Title / Tags / Comments / Rating.")
    print()
    try:
        import os

        os.startfile(OUTPUT_DIR)
    except Exception:
        pass


if __name__ == "__main__":
    main()
