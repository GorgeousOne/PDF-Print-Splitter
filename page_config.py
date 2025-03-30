from enum import Enum
from typing import List, Tuple

class Unit(Enum):
    Point = 1
    Inch = 72
    Millimeter = 72 / 25.4
    Centimeter = 72 / 2.54

    @property
    def abbreviation(self):
        return {
            Unit.Point: "pt",
            Unit.Inch: "in",
            Unit.Millimeter: "mm",
            Unit.Centimeter: "cm",
        }[self]

    def to(self, to_unit:"Unit", val:float):
        return val * (self.value / to_unit.value)

class PageSize(Enum):
    A4 = (Unit.Millimeter.to(Unit.Point, 210), Unit.Millimeter.to(Unit.Point, 297))
    A3 = (Unit.Millimeter.to(Unit.Point, 297), Unit.Millimeter.to(Unit.Point, 420))


class Orientation(Enum):
    PORTRAIT = 0
    LANDSCAPE = 1


def slice_area(area_w:float, area_h:float, page_w:float, page_h:float, crop_vert:float = 0, crop_horz:float = 0, bleed:float = 0) -> Tuple[List[float], List[float]]:
    """
    Computes the positions to cover a given area with pages.

    Args:
        area_width (float): Width of the area to be covered.
        area_height (float): Height of the area to be covered.

    Returns:
        Tuple[List[float], List[float]]: X and Y positions of the upper-left corners of pages.
    """
    effective_w =page_w - 2 * crop_vert
    effective_h = page_h - 2 * crop_vert
    if effective_w <= bleed or effective_h <= bleed:
        raise ValueError("Effective width or height is too small to accommodate bleed.")

    pos_xs, pos_ys = [], []
    x, y = 0, 0

    while x < area_w:
        if x > 0:
            x -= bleed
        pos_xs.append(x - crop_horz)
        x += effective_w

    while y < area_h:
        if y > 0:
            y -= bleed
        pos_ys.append(y - crop_vert)
        y += effective_h

    return pos_xs, pos_ys
