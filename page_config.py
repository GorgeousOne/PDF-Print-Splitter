from enum import Enum
from typing import List, Tuple

class Unit(Enum):
    Point = 1
    Inch = 72
    Millimeter = 2.8346456693
    Centimeter = 28.346456693

    @property
    def abbreviation(self):
        return {
            Unit.Point: "pt",
            Unit.Inch: "in",
            Unit.Millimeter: "mm",
            Unit.Centimeter: "cm",
        }[self]

    def to(self, val:float, to_unit:"Unit"):
        return val * self.value / to_unit.value

class MediaSize(Enum):
    A4 = (Unit.Millimeter.to(210, Unit.Point), Unit.Millimeter.to(297, Unit.Point))
    A3 = (Unit.Millimeter.to(297, Unit.Point), Unit.Millimeter.to(420, Unit.Point))


class Orientation(Enum):
    PORTRAIT = 0
    LANDSCAPE = 1


class PageConfig:
    def __init__(self, media_size:MediaSize = MediaSize.A4, orientation:Orientation = Orientation.PORTRAIT, 
                 crop_vert:float = 0, crop_horz:float = 0, bleed:float = 0):
        """
        Initializes the page configuration.

        Args:
            media_size (MediaSize): The size of the media (A4, A3, etc.).
            orientation (Orientation): Page orientation (Portrait or Landscape).
            crop_vert (float): Vertical crop amount.
            crop_horz (float): Horizontal crop amount.
            bleed (float): Bleed margin for slicing.
        """
        width, height = media_size.value
        if orientation == Orientation.LANDSCAPE:
            self.media_width, self.media_height = width, height
        else:
            self.media_width, self.media_height = height, width
        
        self.crop_vert = crop_vert
        self.crop_horz = crop_horz
        self.bleed = bleed

        self._validate_dimensions()

    def _validate_dimensions(self):
        effective_w = self.media_width - 2 * self.crop_horz
        effective_h = self.media_height - 2 * self.crop_vert
        if effective_w <= self.bleed or effective_w <= 0:
            raise ValueError(f"Invalid effective width: {effective_w}. Adjust crop_horz or media size.")
        if effective_h <= self.bleed or effective_h <= 0:
            raise ValueError(f"Invalid effective height: {effective_h}. Adjust crop_vert or media size.")

def slice_area(area_width: float, area_height: float, page_config: PageConfig) -> Tuple[List[float], List[float]]:
    """
    Computes the positions to cover a given area with pages.

    Args:
        area_width (float): Width of the area to be covered.
        area_height (float): Height of the area to be covered.
        page_config (PageConfig): Configuration of the page layout.

    Returns:
        Tuple[List[float], List[float]]: X and Y positions of the upper-left corners of pages.
    """
    effective_w = page_config.media_width - 2 * page_config.crop_horz
    effective_h = page_config.media_height - 2 * page_config.crop_vert
    
    if effective_w <= page_config.bleed or effective_h <= page_config.bleed:
        raise ValueError("Effective width or height is too small to accommodate bleed.")

    pos_xs, pos_ys = [], []
    x, y = 0, 0

    while x < area_width:
        if x > 0:
            x -= page_config.bleed
        pos_xs.append(x - page_config.crop_horz)
        x += effective_w

    while y < area_height:
        if y > 0:
            y -= page_config.bleed
        pos_ys.append(y - page_config.crop_vert)
        y += effective_h

    return pos_xs, pos_ys
