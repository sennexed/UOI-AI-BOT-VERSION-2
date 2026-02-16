"""Generate UOI identification card images."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


CARD_WIDTH = 1100
CARD_HEIGHT = 700


def _load_avatar(avatar_bytes: bytes | None) -> Image.Image:
    if avatar_bytes:
        try:
            return Image.open(BytesIO(avatar_bytes)).convert("RGBA")
        except (OSError, ValueError):
            pass
    return Image.new("RGBA", (512, 512), (52, 58, 64, 255))


def _circular_avatar(avatar: Image.Image, size: int = 250) -> Image.Image:
    avatar_fit = avatar.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(avatar_fit, (0, 0), mask)
    return result


def generate_id_card(record: dict[str, str], avatar_bytes: bytes | None = None) -> BytesIO:
    """Generate a styled ID card image and return it as a PNG buffer."""
    base = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (19, 24, 34, 255))
    draw = ImageDraw.Draw(base)

    # Watermark + background accents
    draw.rectangle((0, 0, CARD_WIDTH, 110), fill=(154, 24, 24, 255))
    draw.rectangle((0, 110, CARD_WIDTH, 125), fill=(206, 36, 36, 220))
    draw.text((760, 510), "UOI", fill=(120, 25, 25, 65), font=ImageFont.load_default())
    draw.text((800, 550), "IDENTITY", fill=(120, 25, 25, 55), font=ImageFont.load_default())

    # Typography
    title_font = ImageFont.load_default()
    text_font = ImageFont.load_default()

    draw.text((45, 35), "UNION OF INDIANS", fill=(255, 255, 255, 255), font=title_font)
    draw.text((45, 78), "Official Identification Card", fill=(224, 224, 224, 255), font=text_font)

    avatar = _load_avatar(avatar_bytes)
    avatar_circle = _circular_avatar(avatar, size=260)
    base.paste(avatar_circle, (50, 210), avatar_circle)

    # Accent lines
    draw.rounded_rectangle((340, 190, 1030, 590), radius=18, outline=(206, 36, 36, 255), width=4)

    full_name = record.get("full_name", "Unknown")
    uoi_id = record.get("uoi_id", "000000")
    role = record.get("role", "Member")
    status = record.get("status", "Active")
    date_joined = record.get("date_joined", "")
    internal_card_id = record.get("internal_card_id", "")

    lines = [
        f"Full Name : {full_name}",
        f"UOI ID    : {uoi_id}",
        f"Role      : {role}",
        f"Status    : {status}",
        f"Date Join : {date_joined}",
    ]

    y = 230
    for line in lines:
        draw.text((370, y), line, fill=(242, 245, 250, 255), font=text_font)
        y += 62

    draw.text((370, 555), f"Internal Card ID: {internal_card_id}", fill=(190, 190, 190, 255), font=text_font)

    output = BytesIO()
    base.convert("RGB").save(output, format="PNG")
    output.seek(0)
    return output
