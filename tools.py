from dataclasses import dataclass


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
