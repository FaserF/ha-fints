#!/usr/bin/env python3
"""Generate official brand assets for FinTS Banking integration."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def draw_rounded_rectangle(draw, xy, radius, fill):
    """Draw a smooth rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def create_gradient_circle(size, start_color, end_color):
    """Create a vertical gradient inside a rounded squircle/circle."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    pad = size * 0.05
    radius = size * 0.24
    box = [pad, pad, size - pad, size - pad]

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(box, radius=radius, fill=255)

    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)

    r1, g1, b1 = start_color
    r2, g2, b2 = end_color

    for y in range(size):
        ratio = y / size
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        g_draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    img.paste(gradient, (0, 0), mask)
    return img


def draw_bank_symbol(draw, center_x, center_y, scale=1.0, color=(255, 255, 255, 255)):
    """Draw a stylized modern bank facade."""

    def t(x, y):
        return (center_x + (x - 1000) * scale, center_y + (y - 1000) * scale)

    # 1. Pediment (Roof triangle)
    draw.polygon([t(1000, 480), t(520, 720), t(1480, 720)], fill=color)

    # 2. Architrave beam
    draw.rounded_rectangle([t(500, 725), t(1500, 785)], radius=15 * scale, fill=color)

    # 3. Four Neoclassical Columns
    pillars_x = [(580, 680), (840, 940), (1060, 1160), (1320, 1420)]
    for px0, px1 in pillars_x:
        # Capital top
        draw.rounded_rectangle(
            [t(px0 - 15, 800), t(px1 + 15, 835)], radius=8 * scale, fill=color
        )
        # Column shaft
        draw.rounded_rectangle(
            [t(px0, 835), t(px1, 1315)], radius=10 * scale, fill=color
        )
        # Base bottom
        draw.rounded_rectangle(
            [t(px0 - 15, 1315), t(px1 + 15, 1350)], radius=8 * scale, fill=color
        )

    # 4. Stylobate Base podium steps
    draw.rounded_rectangle([t(480, 1360), t(1520, 1425)], radius=15 * scale, fill=color)
    draw.rounded_rectangle([t(430, 1435), t(1570, 1500)], radius=20 * scale, fill=color)

    # 5. Center Security / Digital Shield Star or Keyhole
    cx, cy = t(1000, 630)
    draw.ellipse(
        [cx - 35 * scale, cy - 35 * scale, cx + 35 * scale, cy + 35 * scale],
        fill=(13, 71, 161, 255),
    )


def generate_icon(size=2048):
    """Generate master icon at high resolution."""
    # Gradient: Deep Navy Blue (#0F172A) / Royal (#1E3A8A) to Vivid Cyan (#0284C7)
    base = create_gradient_circle(size, (15, 23, 42), (2, 132, 199))
    draw = ImageDraw.Draw(base)

    # Subtle inner border
    pad = size * 0.05
    radius = size * 0.24
    draw.rounded_rectangle(
        [pad + 8, pad + 8, size - pad - 8, size - pad - 8],
        radius=radius - 4,
        outline=(255, 255, 255, 50),
        width=int(size * 0.012),
    )

    # Bank symbol in center
    draw_bank_symbol(draw, size / 2, size / 2, scale=size / 2000.0)
    return base


def generate_logo(width=4096, height=1024):
    """Generate master horizontal logo at high resolution."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Left: Icon emblem
    icon_size = int(height * 0.88)
    icon_img = generate_icon(icon_size)
    offset_y = int((height - icon_size) / 2)
    offset_x = int(height * 0.08)
    img.paste(icon_img, (offset_x, offset_y), icon_img)

    # Right: Text typography
    text_x = offset_x + icon_size + int(height * 0.16)

    # Try system fonts or draw sleek geometric lettering
    font_bold = None
    font_sub = None
    for font_name in ["segoeui.ttf", "arial.ttf", "calibri.ttf"]:
        try:
            font_bold = ImageFont.truetype(font_name, size=int(height * 0.44))
            font_sub = ImageFont.truetype(font_name, size=int(height * 0.18))
            break
        except Exception:
            continue

    if font_bold is None:
        font_bold = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Draw "FinTS" in Navy / Cyan gradient or Deep White/Navy
    # Main title
    title_y = int(height * 0.18)
    draw.text((text_x, title_y), "FinTS", fill=(255, 255, 255, 255), font=font_bold)

    # Subtitle "BANKING" in accented Cyan
    sub_y = int(height * 0.62)
    draw.text(
        (text_x + 8, sub_y), "ONLINE BANKING", fill=(56, 189, 248, 255), font=font_sub
    )

    return img


def main():
    root = Path(__file__).resolve().parent.parent
    brand_comp_dir = root / "custom_components" / "fints" / "brand"
    brand_root_dir = root / "brand"

    brand_comp_dir.mkdir(parents=True, exist_ok=True)
    brand_root_dir.mkdir(parents=True, exist_ok=True)

    print("Generating FinTS branding assets...")

    # Master high-res
    icon_master = generate_icon(2048)
    logo_master = generate_logo(4096, 1024)

    # 1. icon@2x.png (512x512)
    icon_512 = icon_master.resize((512, 512), Image.Resampling.LANCZOS)
    icon_512.save(brand_comp_dir / "icon@2x.png", format="PNG", optimize=True)
    icon_512.save(brand_root_dir / "icon@2x.png", format="PNG", optimize=True)

    # 2. icon.png (256x256)
    icon_256 = icon_master.resize((256, 256), Image.Resampling.LANCZOS)
    icon_256.save(brand_comp_dir / "icon.png", format="PNG", optimize=True)
    icon_256.save(brand_root_dir / "icon.png", format="PNG", optimize=True)

    # 3. logo@2x.png (1024x256)
    logo_1024 = logo_master.resize((1024, 256), Image.Resampling.LANCZOS)
    logo_1024.save(brand_comp_dir / "logo@2x.png", format="PNG", optimize=True)
    logo_1024.save(brand_root_dir / "logo@2x.png", format="PNG", optimize=True)

    # 4. logo.png (512x128)
    logo_512 = logo_master.resize((512, 128), Image.Resampling.LANCZOS)
    logo_512.save(brand_comp_dir / "logo.png", format="PNG", optimize=True)
    logo_512.save(brand_root_dir / "logo.png", format="PNG", optimize=True)

    print("Successfully generated all brand assets:")
    for path in [
        brand_comp_dir / "icon.png",
        brand_comp_dir / "icon@2x.png",
        brand_comp_dir / "logo.png",
        brand_comp_dir / "logo@2x.png",
        brand_root_dir / "icon.png",
        brand_root_dir / "icon@2x.png",
        brand_root_dir / "logo.png",
        brand_root_dir / "logo@2x.png",
    ]:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
