#!/usr/bin/env python3
"""
Generate the PyScotch SVG logo.

Uses italic serif text with a graph partition motif to the left —
6 nodes split into red (left triangle) and dark (right triangle),
with cross-edges: top-red → top-left-dark, bottom-right-red → bottom-dark.
"""

ACCENT = "#c83232"
DARK = "#1a1a1a"
LIGHT_ACCENT = "#e8d0d0"
NODE_R = 3.0


def graph_motif(cx, cy, scale=1.0):
    """Generate the partitioned graph motif.

    Red nodes: triangle pointing right (left side)
    Dark nodes: triangle pointing left (right side), rotated so that
      - top-dark is top-left (connects to top-red)
      - bottom-dark is bottom-center (connects to bottom-right-red)
    """
    s = scale

    # Red partition: triangle on the left
    #   0: top
    #   1: bottom-left
    #   2: bottom-right (closest to dark partition)
    # Italic shear: top row shifts right, bottom row shifts left
    shear = 2 * s

    red_nodes = [
        (cx - 12 * s + shear, cy - 10 * s),   # 0: top-left
        (cx + 12 * s + shear, cy - 10 * s),   # 1: top-right
        (cx - 12 * s,         cy + 0 * s),     # 2: middle-left
    ]

    dark_nodes = [
        (cx + 12 * s,         cy + 0 * s),     # 3: middle-right
        (cx - 12 * s - shear, cy + 10 * s),    # 4: bottom-left
        (cx + 12 * s - shear, cy + 10 * s),    # 5: bottom-right
    ]

    nodes = [
        (*red_nodes[0], ACCENT),
        (*red_nodes[1], ACCENT),
        (*red_nodes[2], ACCENT),
        (*dark_nodes[0], DARK),
        (*dark_nodes[1], DARK),
        (*dark_nodes[2], DARK),
    ]

    edges = [
        # Within red
        (0, 1),  # top-left ↔ top-right
        (0, 2),  # top-left ↔ middle-left
        (1, 2),  # top-right ↔ middle-left
        # Within dark
        (3, 5),  # middle-right ↔ bottom-right
        (4, 5),  # bottom-left ↔ bottom-right
        (3, 4),  # middle-right ↔ bottom-left
        # Single cross-partition cut:
        (2, 3),  # middle-left ↔ middle-right
    ]

    parts = []

    # Draw edges
    for i, j in edges:
        x1, y1, _ = nodes[i]
        x2, y2, _ = nodes[j]
        is_cut = (i < 3) != (j < 3)
        if is_cut:
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{LIGHT_ACCENT}" stroke-width="1.2" stroke-dasharray="2.5,2" />'
            )
        else:
            c = nodes[i][2]
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{c}" stroke-width="1.2" opacity="0.35" />'
            )

    # Draw nodes
    r = NODE_R * s
    for x, y, color in nodes:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" />'
        )

    return "\n    ".join(parts)


def generate_logo():
    """Generate the full logo SVG."""
    w, h = 212, 48
    text_y = 37
    # Motif to the left, text to the right
    motif = graph_motif(cx=35, cy=25, scale=1.1)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@1,700&amp;display=swap');
      .logo-text {{
        font-family: 'Playfair Display', 'Georgia', 'Times New Roman', serif;
        font-weight: 700;
        font-style: italic;
        font-size: 34px;
      }}
    </style>
  </defs>

  <!-- Graph partition motif -->
  <g opacity="0.9">
    {motif}
  </g>

  <!-- Text -->
  <text x="53" y="{text_y}" class="logo-text">
    <tspan fill="{ACCENT}">Py</tspan><tspan fill="{DARK}">Scotch</tspan>
  </text>
</svg>'''
    return svg


def generate_favicon():
    """Generate a small favicon-style SVG — just the graph motif."""
    motif = graph_motif(cx=16, cy=16, scale=1.1)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <g>{motif}</g>
</svg>'''


if __name__ == "__main__":
    from pathlib import Path

    out = Path(__file__).parent / "static"

    logo_path = out / "logo.svg"
    logo_path.write_text(generate_logo())
    print(f"  {logo_path}")

    favicon_path = out / "favicon.svg"
    favicon_path.write_text(generate_favicon())
    print(f"  {favicon_path}")
