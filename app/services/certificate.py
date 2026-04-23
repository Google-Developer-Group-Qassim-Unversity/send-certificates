import enum
import logging
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from app.config import ASSETS_DIR, FONTCONFIG_FILE

logger = logging.getLogger(__name__)

SVG_NS = "http://www.w3.org/2000/svg"
CENTER_X = 800
EVENT_NAME_CHAR_THRESHOLD = 80

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


class CertificateLanguage(str, enum.Enum):
    ARABIC = "ar"
    ENGLISH = "en"


class MembersGender(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"


def _render_env():
    return {**os.environ, "FONTCONFIG_FILE": str(FONTCONFIG_FILE)}


def svg_to_png(svg_path, output_png_path=None, width=1440, height=1024):
    if output_png_path is None:
        output_png_path = svg_path.replace(".svg", ".png")

    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        raise RuntimeError("rsvg-convert not found (install librsvg)")

    subprocess.run(
        [rsvg, "-w", str(width), "-h", str(height), "-f", "png", "-o", output_png_path, svg_path],
        check=True,
        env=_render_env(),
    )
    logger.info(f"PNG saved: {output_png_path}")
    return output_png_path


def replace_placeholder(root, element_id: str, value: str, lang: CertificateLanguage, center_x=CENTER_X):
    el = root.find(f'.//{{{SVG_NS}}}text[@id="{element_id}"]')
    if el is None:
        return False
    tspan = el.find(f"{{{SVG_NS}}}tspan")
    y = tspan.get("y") if tspan is not None else el.get("y")
    if tspan is not None:
        el.remove(tspan)
    if not center_x:
        el.set("x", str(float(root.get("width", 1440)) / 2))
    el.set("x", str(center_x))
    if y:
        el.set("y", y)
    el.set("text-anchor", "middle")
    if lang == CertificateLanguage.ARABIC:
        el.set("direction", "rtl")
    if element_id == "{{event_name}}" and len(value) > EVENT_NAME_CHAR_THRESHOLD:
        original_size = float(el.get("font-size", 32))
        el.set("font-size", str(original_size * EVENT_NAME_CHAR_THRESHOLD / len(value)))
    el.text = value
    return True


def generate_certificate(
    svg_certificate_file_path: str,
    name: str,
    event_name: str,
    date: str,
    gender: MembersGender,
    lang: CertificateLanguage,
    output_dir: str = "/tmp",
):
    if lang == CertificateLanguage.ENGLISH:
        event_name_text = f'Has attended "{event_name}"'
        date_text = f"On {date} We wish them continued success in their career journey."
        student_gendered = "The Student"
    elif lang == CertificateLanguage.ARABIC:
        event_name_text = f'قد حضر{"ت" if gender == MembersGender.FEMALE else ""} "{event_name}"'
        date_text = f"بتاريخ {date} نتمنى دوام التوفيق والنجاح في مسيرتهم المهنية."
        student_gendered = "الطالب" if gender == MembersGender.MALE else "الطالبة"
    else:
        raise ValueError("Unsupported language")

    replacements = {
        "{{name}}": name,
        "{{event_name}}": event_name_text,
        "{{date}}": date_text,
        "{{gender}}": student_gendered,
    }

    tree = ET.parse(svg_certificate_file_path)
    root = tree.getroot()
    for placeholder, value in replacements.items():
        replace_placeholder(root, placeholder, value, lang)

    os.makedirs(output_dir, exist_ok=True)
    output_svg = os.path.join(output_dir, f"{name}-{os.path.basename(svg_certificate_file_path)}")
    with open(output_svg, "w", encoding="utf-8") as f:
        f.write(ET.tostring(root, encoding="unicode"))

    output = svg_to_png(output_svg)
    os.remove(output_svg)
    logger.info(f"Certificate generated: {output}")
    return output


def resolve_template(lang: CertificateLanguage, official: bool) -> Path:
    kind = "official" if official else "unofficial"
    return ASSETS_DIR / f"{kind}-{lang.value}.svg"
