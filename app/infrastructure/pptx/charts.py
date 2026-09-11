from math import sin, cos, radians
from typing import Dict, List, Tuple

from pptx.util import Inches, Pt
from pptx.enum.chart import XL_CHART_TYPE
from pptx.chart.data import CategoryChartData
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor


# Constants

WHITE = RGBColor(255, 255, 255)
BORDER = RGBColor(226, 232, 240)
BLACK = RGBColor(0, 0, 0)

TITLE_SIZE = Pt(11)
LABEL_SIZE = Pt(9.0)
LABEL_SIZE_SMALL = Pt(9.0)

FIRST_SLICE_ANGLE = 0


# Data helpers

def _sorted_items(
    data_dict: Dict[str, int],
) -> List[Tuple[str, int]]:
    return sorted(
        data_dict.items(),
        key=lambda item: item[1],
        reverse=True,
    )


def _calculate_percentages(
    items: List[Tuple[str, int]],
) -> List[float]:
    total = sum(
        max(0, int(value))
        for _, value in items
    )

    if total <= 0:
        return [0.0] * len(items)

    return [
        (max(0, int(value)) / total) * 100.0
        for _, value in items
    ]


def _calculate_mid_angles(
    items: List[Tuple[str, int]],
) -> List[float]:
    """
    0°   = top
    90°  = right
    180° = bottom
    270° = left
    """
    total = sum(
        max(0, int(value))
        for _, value in items
    )

    if total <= 0:
        return []

    angles = []
    current = FIRST_SLICE_ANGLE

    for _, value in items:
        sweep = (
            max(0, int(value))
            / total
        ) * 360.0

        midpoint = current + sweep / 2.0
        angles.append(midpoint)
        current += sweep

    return angles


def _direction(
    angle: float,
) -> Tuple[float, float]:
    a = radians(angle)

    return (
        sin(a),
        -cos(a),
    )


def _side_for_angle(angle: float) -> str:
    a = angle % 360.0

    if a >= 337.5 or a < 22.5:
        return "top"
    if 22.5 <= a < 67.5:
        return "top_right"
    if 67.5 <= a < 112.5:
        return "right"
    if 112.5 <= a < 157.5:
        return "bottom_right"
    if 157.5 <= a < 202.5:
        return "bottom"
    if 202.5 <= a < 247.5:
        return "bottom_left"
    if 247.5 <= a < 292.5:
        return "left"

    return "top_left"


# Text

def _add_label(
    slide,
    text: str,
    left,
    top,
    width,
    height,
    *,
    font_size,
    bold,
    alignment,
):
    box = slide.shapes.add_textbox(
        int(left),
        int(top),
        int(width),
        int(height),
    )

    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True

    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0

    p = tf.paragraphs[0]
    p.text = str(text)
    p.alignment = alignment

    p.font.name = "Arial"
    p.font.size = font_size
    p.font.bold = bold
    p.font.color.rgb = BLACK

    return box


# Connector

def _add_leader_line(
    slide,
    start_x,
    start_y,
    end_x,
    end_y,
):
    """Simple, thin black connector without arrows."""
    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        int(start_x),
        int(start_y),
        int(end_x),
        int(end_y),
    )

    line.line.color.rgb = BLACK
    line.line.width = Pt(0.35)

    return line


# Initial label position

def _initial_label(
    index: int,
    category: str,
    value: int,
    angle: float,
    center_x: int,
    center_y: int,
    radius: int,
    card_left: int,
    card_top: int,
    card_width: int,
    card_height: int,
):
    side = _side_for_angle(angle)
    dx, dy = _direction(angle)

    anchor_radius = radius + Inches(0.10)

    anchor_x = center_x + dx * anchor_radius
    anchor_y = center_y + dy * anchor_radius

    if side in ("top", "bottom"):
        width = Inches(1.30)
        height = Inches(0.52)
    else:
        width = Inches(1.24)
        height = Inches(0.52)

    if side in ("right", "top_right", "bottom_right"):
        left = int(anchor_x + Inches(0.06))
        top = int(anchor_y - height / 2)
        alignment = PP_ALIGN.LEFT

    elif side in ("left", "top_left", "bottom_left"):
        left = int(anchor_x - width - Inches(0.06))
        top = int(anchor_y - height / 2)
        alignment = PP_ALIGN.RIGHT

    elif side == "top":
        left = int(anchor_x - width / 2)
        top = int(anchor_y - height - Inches(0.06))
        alignment = PP_ALIGN.CENTER

    else:
        left = int(anchor_x - width / 2)
        top = int(anchor_y + Inches(0.06))
        alignment = PP_ALIGN.CENTER

    left = max(
        int(card_left + Inches(0.04)),
        left,
    )

    left = min(
        left,
        int(
            card_left
            + card_width
            - width
            - Inches(0.04)
        ),
    )

    top = max(
        int(card_top + Inches(0.52)),
        top,
    )

    top = min(
        top,
        int(
            card_top
            + card_height
            - height
            - Inches(0.05)
        ),
    )

    return {
        "index": index,
        "category": category,
        "value": value,
        "angle": angle,
        "side": side,
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height),
        "alignment": alignment,
    }


# Collision handling

def _resolve_side_collisions(
    labels,
    card_left,
    card_top,
    card_width,
    card_height,
):
    groups = {
        "left": [],
        "right": [],
        "top": [],
        "bottom": [],
    }

    for label in labels:
        side = label["side"]

        if side in ("left", "top_left", "bottom_left"):
            groups["left"].append(label)

        elif side in ("right", "top_right", "bottom_right"):
            groups["right"].append(label)

        elif side == "top":
            groups["top"].append(label)

        else:
            groups["bottom"].append(label)

    for group_name in ("left", "right"):
        group = groups[group_name]

        if len(group) <= 1:
            continue

        group.sort(
            key=lambda item: (
                item["top"],
                item["index"],
            )
        )

        minimum_gap = Inches(0.055)

        for i in range(1, len(group)):
            previous = group[i - 1]
            current = group[i]

            minimum_top = (
                previous["top"]
                + previous["height"]
                + minimum_gap
            )

            if current["top"] < minimum_top:
                current["top"] = int(minimum_top)

        bottom_limit = (
            card_top
            + card_height
            - Inches(0.06)
        )

        last = group[-1]

        overflow = (
            last["top"]
            + last["height"]
            - bottom_limit
        )

        if overflow > 0:
            for label in group:
                label["top"] = int(
                    label["top"] - overflow
                )

        top_limit = card_top + Inches(0.52)

        if group[0]["top"] < top_limit:
            delta = (
                top_limit
                - group[0]["top"]
            )

            for label in group:
                label["top"] = int(
                    label["top"] + delta
                )

    for group_name in ("top", "bottom"):
        group = groups[group_name]

        if len(group) <= 1:
            continue

        group.sort(
            key=lambda item: (
                item["left"],
                item["index"],
            )
        )

        minimum_gap = Inches(0.06)

        for i in range(1, len(group)):
            previous = group[i - 1]
            current = group[i]

            minimum_left = (
                previous["left"]
                + previous["width"]
                + minimum_gap
            )

            if current["left"] < minimum_left:
                current["left"] = int(minimum_left)

        right_limit = (
            card_left
            + card_width
            - Inches(0.04)
        )

        last = group[-1]

        overflow = (
            last["left"]
            + last["width"]
            - right_limit
        )

        if overflow > 0:
            for label in group:
                label["left"] = int(
                    label["left"] - overflow
                )

        left_limit = card_left + Inches(0.04)

        if group[0]["left"] < left_limit:
            delta = (
                left_limit
                - group[0]["left"]
            )

            for label in group:
                label["left"] = int(
                    label["left"] + delta
                )

    return labels


# Safety

def _push_labels_away_from_pie(
    labels,
    center_x,
    center_y,
    radius,
):
    for label in labels:
        box_center_x = (
            label["left"]
            + label["width"] / 2
        )

        box_center_y = (
            label["top"]
            + label["height"] / 2
        )

        dx = box_center_x - center_x
        dy = box_center_y - center_y

        distance_sq = (
            dx * dx
            + dy * dy
        )

        label_radius = max(
            label["width"],
            label["height"],
        ) / 2

        min_distance = (
            radius
            + label_radius
            + Inches(0.04)
        )

        if distance_sq <= min_distance ** 2:
            length = (
                distance_sq ** 0.5
                if distance_sq > 0
                else 1
            )

            nx = dx / length
            ny = dy / length

            move = (
                min_distance
                - length
            )

            label["left"] = int(
                label["left"] + nx * move
            )

            label["top"] = int(
                label["top"] + ny * move
            )

    return labels


# True textbox intersection

def _connector_target(
    label,
    start_x,
    start_y,
):
    """
    Calculate the actual intersection between the line and the
    final textbox rectangle.
    """
    left = float(label["left"])
    right = float(
        label["left"]
        + label["width"]
    )

    top = float(label["top"])
    bottom = float(
        label["top"]
        + label["height"]
    )

    center_x = (left + right) / 2.0
    center_y = (top + bottom) / 2.0

    dx = center_x - float(start_x)
    dy = center_y - float(start_y)

    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return int(center_x), int(center_y)

    intersections = []

    # Left edge
    if abs(dx) > 1e-9:
        t = (
            left - float(start_x)
        ) / dx

        if t > 0:
            y = (
                float(start_y)
                + t * dy
            )

            if top <= y <= bottom:
                intersections.append(
                    (t, left, y)
                )

    # Right edge
    if abs(dx) > 1e-9:
        t = (
            right - float(start_x)
        ) / dx

        if t > 0:
            y = (
                float(start_y)
                + t * dy
            )

            if top <= y <= bottom:
                intersections.append(
                    (t, right, y)
                )

    # Top edge
    if abs(dy) > 1e-9:
        t = (
            top - float(start_y)
        ) / dy

        if t > 0:
            x = (
                float(start_x)
                + t * dx
            )

            if left <= x <= right:
                intersections.append(
                    (t, x, top)
                )

    # Bottom edge
    if abs(dy) > 1e-9:
        t = (
            bottom - float(start_y)
        ) / dy

        if t > 0:
            x = (
                float(start_x)
                + t * dx
            )

            if left <= x <= right:
                intersections.append(
                    (t, x, bottom)
                )

    if not intersections:
        return (
            int(center_x),
            int(center_y),
        )

    intersections.sort(
        key=lambda item: item[0]
    )

    _, target_x, target_y = intersections[0]

    return (
        int(target_x),
        int(target_y),
    )


# Main

def add_pie_chart(
    slide,
    title: str,
    data_dict: dict,
    left,
    top,
    width,
    height,
):
    """
    Render a clean radial pie chart.

    Data is preserved exactly as received.
    No "Autres" grouping is performed.
    """

    # Card
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        int(left),
        int(top),
        int(width),
        int(height),
    )

    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = BORDER
    card.line.width = Pt(1)

    # Title
    _add_label(
        slide,
        title,
        left + Inches(0.08),
        top + Inches(0.08),
        width - Inches(0.16),
        Inches(0.42),
        bold=True,
        font_size=TITLE_SIZE,
        alignment=PP_ALIGN.CENTER,
    )

    # Data
    has_data = bool(
        data_dict
        and sum(data_dict.values()) > 0
    )

    if not has_data:
        _add_label(
            slide,
            "Aucune donnée",
            left + Inches(0.20),
            top + Inches(2.0),
            width - Inches(0.40),
            Inches(0.35),
            bold=False,
            font_size=Pt(9),
            alignment=PP_ALIGN.CENTER,
        )
        return None

    items = _sorted_items(data_dict)

    percentages = _calculate_percentages(
        items
    )

    angles = _calculate_mid_angles(
        items
    )

    # Pie size
    pie_size = int(
        min(
            width * 0.57,
            height * 0.62,
            Inches(2.58),
        )
    )

    pie_left = int(
        left
        + (width - pie_size) / 2
    )

    pie_top = int(
        top
        + Inches(0.84)
        + (
            (
                height
                - Inches(0.96)
                - pie_size
            ) / 2
        )
    )

    # PowerPoint pie
    chart_data = CategoryChartData()

    chart_data.categories = [
        str(category)
        for category, _ in items
    ]

    chart_data.add_series(
        "Répartition",
        tuple(
            int(value)
            for _, value in items
        ),
    )

    chart_shape = slide.shapes.add_chart(
        XL_CHART_TYPE.PIE,
        int(pie_left),
        int(pie_top),
        int(pie_size),
        int(pie_size),
        chart_data,
    )

    chart = chart_shape.chart

    chart.has_title = False
    chart.has_legend = False

    chart.plots[0].first_slice_angle = 0
    chart.plots[0].has_data_labels = False

    # Pie geometry
    center_x = int(
        pie_left
        + pie_size / 2
    )

    center_y = int(
        pie_top
        + pie_size / 2
    )

    radius = int(
        pie_size * 0.48
    )

    # Initial labels
    labels = []

    for index, (
        (category, value),
        angle,
    ) in enumerate(
        zip(items, angles)
    ):
        labels.append(
            _initial_label(
                index=index,
                category=str(category),
                value=int(value),
                angle=angle,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                card_left=left,
                card_top=top,
                card_width=width,
                card_height=height,
            )
        )

    # Collision resolution
    labels = _resolve_side_collisions(
        labels=labels,
        card_left=left,
        card_top=top,
        card_width=width,
        card_height=height,
    )

    labels = _push_labels_away_from_pie(
        labels=labels,
        center_x=center_x,
        center_y=center_y,
        radius=radius,
    )

    # Draw labels
    for index, label in enumerate(labels):
        category = label["category"]
        value = label["value"]
        pct = percentages[index]

        # Top 3 categories are bold.
        is_top3 = index < 3

        display_text = (
            f"{category}\n"
            f"{value} ; {pct:.0f}%"
        )

        font_size = (
            LABEL_SIZE
            if len(items) <= 6
            else LABEL_SIZE_SMALL
        )

        _add_label(
            slide,
            display_text,
            label["left"],
            label["top"],
            label["width"],
            label["height"],
            bold=is_top3,
            font_size=font_size,
            alignment=label["alignment"],
        )

    # Draw connectors AFTER final label positions.
    for label in labels:
        dx, dy = _direction(
            label["angle"]
        )

        start_distance = (
            radius
            + Inches(0.008)
        )

        start_x = int(
            center_x
            + dx * start_distance
        )

        start_y = int(
            center_y
            + dy * start_distance
        )

        target_x, target_y = _connector_target(
            label,
            start_x,
            start_y,
        )

        _add_leader_line(
            slide,
            start_x,
            start_y,
            target_x,
            target_y,
        )

    return chart