from dataclasses import dataclass
import numpy as np


@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int
    parent: 'BoundingBox'  # Useful for having nested boundaries.

    # A library like numpy might have some kind of coord/vector object that could replace this.
    def __init__(self, x1=None, y1=None, x2=None, y2=None, parent=None):
        self.x1 = int(x1) if x1 is not None else None
        self.y1 = int(y1) if y1 is not None else None
        self.x2 = int(x2) if x2 is not None else None
        self.y2 = int(y2) if y2 is not None else None
        self.parent = parent

    @property
    def middle(self):
        x = (self.x1 + self.x2) / 2
        y = (self.y1 + self.y2) / 2
        return x, y

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    @width.setter
    def width(self, value):
        self.x2 = self.x1 + value

    @height.setter
    def height(self, value):
        self.y2 = self.y1 + value

    def real_position(self) -> (int, int):
        x = self.x1
        y = self.y1
        parent = self.parent
        while parent is not None:
            x += parent.x1
            y += parent.y1
            parent = parent.parent

        return x, y


@dataclass
class Vect2:
    x: float
    y: float


class ColorRange:
    def __init__(self, color_low: tuple, color_high: tuple):
        assert len(color_low) == len(color_high)
        self.c1 = color_low
        self.c2 = color_high

    def is_within(self, color: tuple) -> bool:
        """
        Checks if color is within self.c1 and self.c2
        """
        if len(color) != len(self.c1):
            raise ValueError
        for i in range(len(color)):
            if not self.c1[i] <= color[i] <= self.c2[i]:
                return False
        return True

    def is_any(self, color: tuple) -> bool:
        if len(color) != len(self.c1):
            raise ValueError
        return np.array_equal(color, self.c1) or np.array_equal(color, self.c2)


class WorkerBase:
    """
    The basic object different AI functions inherit from

    """

    # def __init__(self, bot):
    #     self.bot = bot

    def desired_views(self) -> list[str]:
        """
        The views this worker wants rendered next frame.
        """
        return [""]

    def update(self):
        """
        Main loop that's called every frame.
        """

    def debug(self):
        """
        Called when set to debug mode, shows DUCCI's internal thoughts.
        Runs on its own thread, so as to allow blocking calls.
        Ran after update
        """