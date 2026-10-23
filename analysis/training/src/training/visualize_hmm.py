# Copyright (c) 2026 Chris Lee and contributors.
# Licensed under the MIT license. See LICENSE file in the project root for details.

import argparse
import json
import math
import sys
from pathlib import Path

# State styling theme
STATE_COLORS = {
    "open_car": {
        "border": "#059669",
        "bg": "#ecfdf5",
        "text": "#065f46",
        "badge": "#10b981",
        "label": "OPEN + CAR",
    },
    "open_empty": {
        "border": "#0284c7",
        "bg": "#f0f9ff",
        "text": "#0369a1",
        "badge": "#0ea5e9",
        "label": "OPEN + EMPTY",
    },
    "closed_car": {
        "border": "#d97706",
        "bg": "#fffbeb",
        "text": "#b45309",
        "badge": "#f59e0b",
        "label": "CLOSED + CAR",
    },
    "closed_empty": {
        "border": "#7c3aed",
        "bg": "#f5f3ff",
        "text": "#6d28d9",
        "badge": "#8b5cf6",
        "label": "CLOSED + EMPTY",
    },
    "open": {
        "border": "#059669",
        "bg": "#ecfdf5",
        "text": "#065f46",
        "badge": "#10b981",
        "label": "OPEN",
    },
}

DEFAULT_STATE_COLOR = {
    "border": "#64748b",
    "bg": "#f8fafc",
    "text": "#1e293b",
    "badge": "#94a3b8",
    "label": "STATE",
}


def get_bucket_range_label(bucket_idx: int, boundaries: list[float]) -> str:
    """Returns human-readable range string for a bucket index."""
    if bucket_idx == 0:
        return f"0-{int(boundaries[0])} cm"
    if bucket_idx >= len(boundaries):
        return f">{int(boundaries[-1])} cm (Far)"
    return f"{int(boundaries[bucket_idx - 1])}-{int(boundaries[bucket_idx])} cm"


def svg_rect(
    x: float,
    y: float,
    w: float,
    h: float,
    rx: float | None = None,
    fill: str | None = None,
    stroke: str | None = None,
    stroke_width: float | None = None,
    opacity: float | None = None,
    filter_url: str | None = None,
) -> str:
    parts = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"']
    if rx is not None:
        parts.append(f'rx="{rx}"')
    if fill:
        parts.append(f'fill="{fill}"')
    if stroke:
        parts.append(f'stroke="{stroke}"')
    if stroke_width:
        parts.append(f'stroke-width="{stroke_width}"')
    if opacity is not None:
        parts.append(f'opacity="{opacity}"')
    if filter_url:
        parts.append(f'filter="{filter_url}"')
    return " ".join(parts) + "/>"


def svg_text(
    x: float,
    y: float,
    content: str,
    font_size: float = 12,
    font_weight: str | int | None = None,
    fill: str = "#0f172a",
    anchor: str | None = None,
) -> str:
    parts = [f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" fill="{fill}"']
    if font_weight:
        parts.append(f'font-weight="{font_weight}"')
    if anchor:
        parts.append(f'text-anchor="{anchor}"')
    return " ".join(parts) + f">{content}</text>"


def svg_path(
    d: str,
    stroke: str = "#64748b",
    stroke_width: float = 1.8,
    marker_end: str | None = None,
    fill: str = "none",
) -> str:
    parts = [f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"']
    if marker_end:
        parts.append(f'marker-end="{marker_end}"')
    return " ".join(parts) + "/>"


def generate_hmm_svg(model_data: dict) -> str:
    """Generates an SVG string visualizing an HMM model (topology & emissions)."""
    side = model_data.get("side", "model").upper()
    states = model_data.get("states", ["open", "closed_car", "closed_empty"])
    num_states = len(states)
    A = model_data.get("A", [])
    B = model_data.get("B", [])
    pi = model_data.get("pi", [1.0 / num_states] * num_states)
    boundaries = model_data.get("boundaries", [])
    num_buckets = len(boundaries) + 1

    has_sonar2 = "B2" in model_data and model_data["B2"] is not None
    B2 = model_data.get("B2") if has_sonar2 else None
    boundaries2 = model_data.get("boundaries2", boundaries) if has_sonar2 else boundaries

    # Canvas dimensions
    svg_w = 1260
    card_h = 135
    margin_top = 110
    svg_h = max(720, margin_top + num_states * card_h + 30)

    # State positions in topology diagram
    node_w, node_h = 160, 68
    node_coords = {}

    if num_states == 4:
        node_coords[0] = (90, 160)  # open_car
        node_coords[1] = (330, 160)  # open_empty
        node_coords[2] = (90, 470)  # closed_car
        node_coords[3] = (330, 470)  # closed_empty
    elif num_states == 3:
        node_coords[0] = (210, 160)  # open
        node_coords[1] = (90, 460)  # closed_car
        node_coords[2] = (330, 460)  # closed_empty
    else:
        for idx in range(num_states):
            angle = (2 * math.pi * idx) / num_states - math.pi / 2
            cx = 280 + 170 * math.cos(angle) - node_w / 2
            cy = 340 + 170 * math.sin(angle) - node_h / 2
            node_coords[idx] = (cx, cy)

    lines = []

    # SVG Root and Styles
    font_stack = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    )
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}" style="background-color: #f8fafc; '
        f'font-family: {font_stack};">'
    )

    # Definitions
    lines.append("<defs>")
    lines.append('  <filter id="shadow" x="-5%" y="-5%" width="115%" height="115%">')
    lines.append('    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.08"/>')
    lines.append("  </filter>")
    lines.append(
        '  <marker id="arrow" viewBox="0 0 10 10" refX="7" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
    )
    lines.append('    <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b"/>')
    lines.append("  </marker>")
    lines.append("</defs>")

    # Header Card
    lines.append(
        svg_rect(
            25,
            20,
            svg_w - 50,
            70,
            rx=12,
            fill="#ffffff",
            stroke="#e2e8f0",
            filter_url="url(#shadow)",
        )
    )
    lines.append(
        svg_text(
            50,
            52,
            f"GARAGE133 HMM MODEL — {side} SIDE",
            font_size=20,
            font_weight=700,
            fill="#0f172a",
        )
    )

    max_dist = int(boundaries[-1]) if boundaries else 400
    sensor_txt = "Dual Sonar (Sonar 1 & 2)" if has_sonar2 else "Single Sonar (Sonar 1)"
    subtitle = (
        f"Topology: {num_states} States | Buckets: {num_buckets} | "
        f"Max Dist: {max_dist}cm | Sensors: {sensor_txt}"
    )
    lines.append(svg_text(50, 73, subtitle, font_size=12, fill="#64748b"))

    # Legend in header right
    leg_x = svg_w - 380
    lines.append(f'<g transform="translate({leg_x}, 38)">')
    lines.append(svg_rect(0, 5, 14, 14, rx=3, fill="#2563eb"))
    lines.append(svg_text(20, 17, "Sonar 1 (Front)", font_size=12, font_weight=600, fill="#334155"))
    if has_sonar2:
        lines.append(svg_rect(130, 5, 14, 14, rx=3, fill="#f97316"))
        lines.append(
            svg_text(150, 17, "Sonar 2 (Rear)", font_size=12, font_weight=600, fill="#334155")
        )
    lines.append("</g>")

    # Column 1: Topology Diagram Panel
    lines.append(
        svg_rect(
            25,
            105,
            530,
            590,
            rx=12,
            fill="#ffffff",
            stroke="#e2e8f0",
            filter_url="url(#shadow)",
        )
    )
    lines.append(
        svg_text(
            45,
            135,
            "1. State Transition Topology (A Matrix &amp; &pi;)",
            font_size=15,
            font_weight=700,
            fill="#1e293b",
        )
    )
    lines.append(
        svg_text(
            45,
            152,
            "Directed arrows show transition probabilities P(next | current)",
            font_size=11,
            fill="#64748b",
        )
    )

    # Transition Arrows (drawn behind nodes)
    lines.append('<g id="transitions">')

    def add_edge_badge(bx: float, by: float, prob_val: float):
        lines.append(
            svg_rect(bx, by, 44, 16, rx=4, fill="#ffffff", stroke="#cbd5e1", stroke_width=1)
        )
        lines.append(
            svg_text(
                bx + 22,
                by + 12,
                f"{prob_val:.4f}",
                font_size=9.5,
                font_weight=600,
                fill="#334155",
                anchor="middle",
            )
        )

    if num_states == 4:
        p01 = A[0][1] if len(A) > 0 and len(A[0]) > 1 else 0
        if p01 > 0:
            lines.append(
                svg_path(
                    "M 250 178 Q 290 160 326 178",
                    stroke="#64748b",
                    stroke_width=1.8,
                    marker_end="url(#arrow)",
                )
            )
            add_edge_badge(268, 153, p01)

        p10 = A[1][0] if len(A) > 1 and len(A[1]) > 0 else 0
        if p10 > 0:
            lines.append(
                svg_path(
                    "M 330 205 Q 290 223 254 205",
                    stroke="#64748b",
                    stroke_width=1.8,
                    marker_end="url(#arrow)",
                )
            )
            add_edge_badge(268, 212, p10)

        p02 = A[0][2] if len(A) > 0 and len(A[0]) > 2 else 0
        if p02 > 0:
            lines.append(
                svg_path(
                    "M 150 228 Q 130 350 150 466",
                    stroke="#64748b",
                    stroke_width=1.8,
                    marker_end="url(#arrow)",
                )
            )
            add_edge_badge(115, 342, p02)

        p20 = A[2][0] if len(A) > 2 and len(A[2]) > 0 else 0
        if p20 > 0:
            lines.append(
                svg_path(
                    "M 190 470 Q 210 350 190 232",
                    stroke="#64748b",
                    stroke_width=1.8,
                    marker_end="url(#arrow)",
                )
            )
            add_edge_badge(180, 342, p20)

        p13 = A[1][3] if len(A) > 1 and len(A[1]) > 3 else 0
        if p13 > 0:
            lines.append(
                svg_path(
                    "M 390 228 Q 370 350 390 466",
                    stroke="#64748b",
                    stroke_width=1.8,
                    marker_end="url(#arrow)",
                )
            )
            add_edge_badge(355, 342, p13)

        p31 = A[3][1] if len(A) > 3 and len(A[3]) > 1 else 0
        if p31 > 0:
            lines.append(
                svg_path(
                    "M 430 470 Q 450 350 430 232",
                    stroke="#64748b",
                    stroke_width=1.8,
                    marker_end="url(#arrow)",
                )
            )
            add_edge_badge(420, 342, p31)

        # Self-loops
        loop_style = {"stroke": "#94a3b8", "stroke_width": 1.6, "marker_end": "url(#arrow)"}
        lines.append(svg_path("M 120 160 C 80 110, 160 110, 140 156", **loop_style))
        lines.append(
            svg_text(
                120,
                106,
                f"Stay: {A[0][0]:.4f}",
                font_size=9,
                font_weight=600,
                fill="#64748b",
                anchor="middle",
            )
        )

        lines.append(svg_path("M 420 160 C 380 110, 460 110, 440 156", **loop_style))
        lines.append(
            svg_text(
                420,
                106,
                f"Stay: {A[1][1]:.4f}",
                font_size=9,
                font_weight=600,
                fill="#64748b",
                anchor="middle",
            )
        )

        lines.append(svg_path("M 120 538 C 80 588, 160 588, 140 542", **loop_style))
        lines.append(
            svg_text(
                120,
                605,
                f"Stay: {A[2][2]:.4f}",
                font_size=9,
                font_weight=600,
                fill="#64748b",
                anchor="middle",
            )
        )

        lines.append(svg_path("M 420 538 C 380 588, 460 588, 440 542", **loop_style))
        lines.append(
            svg_text(
                420,
                605,
                f"Stay: {A[3][3]:.4f}",
                font_size=9,
                font_weight=600,
                fill="#64748b",
                anchor="middle",
            )
        )

    elif num_states == 3:
        p_style = {"stroke": "#64748b", "stroke_width": 1.8, "marker_end": "url(#arrow)"}
        lines.append(svg_path("M 230 228 Q 150 320 170 456", **p_style))
        lines.append(svg_path("M 190 460 Q 220 340 250 232", **p_style))
        lines.append(svg_path("M 330 228 Q 410 320 390 456", **p_style))
        lines.append(svg_path("M 370 460 Q 340 340 310 232", **p_style))

        lines.append(
            svg_text(
                290,
                106,
                f"Stay: {A[0][0]:.4f}",
                font_size=9,
                font_weight=600,
                fill="#64748b",
                anchor="middle",
            )
        )
        lines.append(
            svg_text(
                120,
                595,
                f"Stay: {A[1][1]:.4f}",
                font_size=9,
                font_weight=600,
                fill="#64748b",
                anchor="middle",
            )
        )
        lines.append(
            svg_text(
                420,
                595,
                f"Stay: {A[2][2]:.4f}",
                font_size=9,
                font_weight=600,
                fill="#64748b",
                anchor="middle",
            )
        )

    lines.append("</g>")

    # Render State Nodes
    for idx, s_name in enumerate(states):
        nx, ny = node_coords[idx]
        style = STATE_COLORS.get(s_name, DEFAULT_STATE_COLOR)
        p_init = pi[idx] if idx < len(pi) else 0.0

        lines.append(f'<g id="node-{s_name}" transform="translate({nx}, {ny})">')
        lines.append(
            svg_rect(
                0,
                0,
                node_w,
                node_h,
                rx=10,
                fill=style["bg"],
                stroke=style["border"],
                stroke_width=2,
                filter_url="url(#shadow)",
            )
        )
        lines.append(svg_rect(12, 12, 8, 8, rx=4, fill=style["badge"]))
        lines.append(
            svg_text(
                26,
                20,
                s_name.upper(),
                font_size=12,
                font_weight=700,
                fill=style["text"],
            )
        )
        lines.append(svg_text(14, 42, f"State idx: {idx}", font_size=11, fill="#475569"))
        lines.append(
            svg_text(
                14,
                57,
                f"&pi; = {p_init:.3f} ({p_init * 100:.1f}%)",
                font_size=11,
                font_weight=600,
                fill="#0f172a",
            )
        )
        lines.append("</g>")

    # Column 2: Emission Profiles Panels
    col2_x = 575
    col2_w = svg_w - col2_x - 25

    lines.append(
        svg_rect(
            col2_x,
            105,
            col2_w,
            num_states * card_h + 50,
            rx=12,
            fill="#ffffff",
            stroke="#e2e8f0",
            filter_url="url(#shadow)",
        )
    )
    lines.append(
        svg_text(
            col2_x + 20,
            135,
            "2. Emission Profiles (Sensor Distance Histograms)",
            font_size=15,
            font_weight=700,
            fill="#1e293b",
        )
    )
    lines.append(
        svg_text(
            col2_x + 20,
            152,
            "Discrete bucket emission probabilities P(bucket | state). Range: 0cm &rarr; 400cm+",
            font_size=11,
            fill="#64748b",
        )
    )

    plot_w = col2_w - 90
    plot_h = 60

    for idx, s_name in enumerate(states):
        card_y = 170 + idx * card_h
        style = STATE_COLORS.get(s_name, DEFAULT_STATE_COLOR)

        b_row = B[idx] if idx < len(B) else [0] * num_buckets
        b2_row = B2[idx] if has_sonar2 and idx < len(B2) else None

        # Find peak bucket
        peak_idx1 = int(b_row.index(max(b_row))) if b_row else 0
        peak_lbl1 = get_bucket_range_label(peak_idx1, boundaries)
        peak_val1 = b_row[peak_idx1] if b_row else 0

        peak_str = f"S1 Peak: {peak_lbl1} ({peak_val1 * 100:.1f}%)"
        if has_sonar2 and b2_row:
            peak_idx2 = int(b2_row.index(max(b2_row)))
            peak_lbl2 = get_bucket_range_label(peak_idx2, boundaries2)
            peak_val2 = b2_row[peak_idx2]
            peak_str += f" | S2 Peak: {peak_lbl2} ({peak_val2 * 100:.1f}%)"

        lines.append(f'<g transform="translate({col2_x + 15}, {card_y})">')
        lines.append(
            svg_rect(
                0,
                0,
                col2_w - 30,
                card_h - 15,
                rx=8,
                fill="#f8fafc",
                stroke="#e2e8f0",
                stroke_width=1,
            )
        )
        lines.append(svg_rect(12, 10, 8, 8, rx=4, fill=style["badge"]))
        lines.append(
            svg_text(
                26,
                18,
                s_name.upper(),
                font_size=12,
                font_weight=700,
                fill=style["text"],
            )
        )
        lines.append(
            svg_text(
                col2_w - 45,
                18,
                peak_str,
                font_size=10.5,
                font_weight=500,
                fill="#64748b",
                anchor="end",
            )
        )

        # Chart Area
        lines.append('<g transform="translate(45, 28)">')
        # Axis lines and ticks
        lines.append(
            f'<line x1="0" y1="0" x2="{plot_w}" y2="0" stroke="#f1f5f9" stroke-width="1"/>'
        )
        lines.append(
            f'<line x1="0" y1="{plot_h / 2}" x2="{plot_w}" y2="{plot_h / 2}" '
            f'stroke="#f1f5f9" stroke-width="1"/>'
        )
        lines.append(
            f'<line x1="0" y1="{plot_h}" x2="{plot_w}" y2="{plot_h}" '
            f'stroke="#cbd5e1" stroke-width="1"/>'
        )

        lines.append(svg_text(-8, 5, "1.0", font_size=8.5, fill="#94a3b8", anchor="end"))
        lines.append(
            svg_text(
                -8,
                plot_h / 2 + 3,
                "0.5",
                font_size=8.5,
                fill="#94a3b8",
                anchor="end",
            )
        )
        lines.append(
            svg_text(
                -8,
                plot_h + 3,
                "0.0",
                font_size=8.5,
                fill="#94a3b8",
                anchor="end",
            )
        )

        # Bars
        bucket_w = plot_w / num_buckets
        bar_w = (bucket_w * 0.4) if has_sonar2 else (bucket_w * 0.75)

        for b_idx in range(num_buckets):
            bx = b_idx * bucket_w
            # Sonar 1
            p1 = b_row[b_idx] if b_idx < len(b_row) else 0.0
            bh1 = min(plot_h, p1 * plot_h)
            by1 = plot_h - bh1
            lines.append(
                svg_rect(
                    bx + 1,
                    by1,
                    bar_w,
                    bh1,
                    rx=1.5,
                    fill="#2563eb",
                    opacity=0.85,
                )
            )

            # Sonar 2
            if has_sonar2 and b2_row:
                p2 = b2_row[b_idx] if b_idx < len(b2_row) else 0.0
                bh2 = min(plot_h, p2 * plot_h)
                by2 = plot_h - bh2
                lines.append(
                    svg_rect(
                        bx + bar_w + 2,
                        by2,
                        bar_w,
                        bh2,
                        rx=1.5,
                        fill="#f97316",
                        opacity=0.85,
                    )
                )

        # X-axis distance labels
        lines.append(svg_text(0, plot_h + 14, "0cm", font_size=8.5, fill="#64748b"))
        lines.append(
            svg_text(
                plot_w * 0.25,
                plot_h + 14,
                "100cm",
                font_size=8.5,
                fill="#64748b",
                anchor="middle",
            )
        )
        lines.append(
            svg_text(
                plot_w * 0.50,
                plot_h + 14,
                "200cm",
                font_size=8.5,
                fill="#64748b",
                anchor="middle",
            )
        )
        lines.append(
            svg_text(
                plot_w * 0.75,
                plot_h + 14,
                "300cm",
                font_size=8.5,
                fill="#64748b",
                anchor="middle",
            )
        )
        lines.append(
            svg_text(
                plot_w,
                plot_h + 14,
                "400cm+",
                font_size=8.5,
                fill="#64748b",
                anchor="end",
            )
        )
        lines.append("</g>")  # chart area
        lines.append("</g>")  # state card

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate clean, scalable SVG visualization for Garage133 HMM models."
    )
    parser.add_argument(
        "model",
        type=str,
        nargs="?",
        default="hmm_left.json",
        help="Path to HMM model JSON file (default: hmm_left.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output SVG file path (default: <model_name>.svg)",
    )
    args = parser.parse_args()

    model_file = Path(args.model)
    if not model_file.exists():
        print(f"Error: Model file '{model_file}' not found.")
        sys.exit(1)

    with model_file.open("r") as f:
        data = json.load(f)

    svg_content = generate_hmm_svg(data)

    out_path = Path(args.output) if args.output else model_file.with_suffix(".svg")
    with out_path.open("w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"Successfully generated HMM visualization: {out_path.resolve()}")


if __name__ == "__main__":
    main()
