# -*- coding: utf-8 -*-
from reportlab.graphics.barcode.code128 import Code128
from markupsafe import Markup


def generate_barcode_svg_string(value, max_width_mm=70.0, height_mm=8.0, show_text=False, font_size_pt=7.5):
    """
    Generate a pure vector SVG barcode string using Code128.
    Automatically scales barWidth to fit proportionally inside max_width_mm without overflowing or clipping.
    Outputs crisp vector rectangles with shape-rendering="crispEdges".
    """
    if not value:
        return None
    val_str = str(value).strip()
    if not val_str:
        return None

    try:
        val_str.encode('ascii')
    except UnicodeEncodeError:
        return None

    try:
        # 1. Compute total modules using unit barWidth=1.0 and quiet=0
        dummy = Code128(val_str, barWidth=1.0, quiet=0)
        dummy._calculate()
        total_modules = dummy._width or 100.0

        # 2. Determine target bar width in mm
        # Constrain between 0.16mm (high-density scanners) and 0.40mm
        avail_w = max(15.0, float(max_width_mm or 70.0) - 1.0)
        target_bar_w = max(0.16, min(0.40, avail_w / total_modules))

        # 3. Generate Code128 with calculated barWidth and quiet=0
        bc = Code128(val_str, barHeight=float(height_mm or 8.0), barWidth=target_bar_w, quiet=0)
        bc._calculate()
        raw_h = bc.barHeight

        oa, oA = ord('a') - 1, ord('A') - 1
        left = 0.0
        rect_parts = []
        for c in bc.decomposed:
            oc = ord(c)
            if 'a' <= c <= 'z':
                left += (oc - oa) * bc.barWidth
            elif 'A' <= c <= 'Z':
                w = (oc - oA) * bc.barWidth
                rect_parts.append(
                    f'<rect x="{left:.2f}" y="0" width="{w:.2f}" height="{raw_h:.2f}" fill="#000000" />'
                )
                left += w

        # Exact width of the drawn barcode bars (zero extraneous quiet margins)
        raw_w = max(left, 1.0)
        text_extra_h = 3.2 if show_text else 0.0
        total_h = raw_h + text_extra_h

        svg_parts = []
        svg_parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {raw_w:.2f} {total_h:.2f}" '
            f'width="{raw_w:.2f}mm" height="{total_h:.2f}mm" '
            f'style="max-width: 100%; height: {total_h:.2f}mm; display: inline-block; vertical-align: middle; shape-rendering: crispEdges;" '
            f'shape-rendering="crispEdges">'
        )
        svg_parts.extend(rect_parts)

        if show_text:
            text_y = raw_h + 2.8
            svg_parts.append(
                f'<text x="{raw_w / 2.0:.2f}" y="{text_y:.2f}" '
                f'text-anchor="middle" '
                f'font-family="Arial, Helvetica, sans-serif" '
                f'font-size="{font_size_pt:.1f}pt" '
                f'font-weight="bold" fill="#000000">{val_str}</text>'
            )

        svg_parts.append('</svg>')
        return Markup(''.join(svg_parts))
    except Exception:
        return None
