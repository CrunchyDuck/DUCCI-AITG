import pynput
import numpy as np
from tools import BoundingBox


class Fisher:
    def __init__(self, bot):
        self.bot = bot
        self.bar = None
        self.bar_bounds = BoundingBox(parent=self.bot.bounds["minigame"])
        # TODO: Make this a relative value rather than a set pixel value.
        bounds = self.bot.bounds["minigame"]
        self.bar_bounds.x1 = bounds.x2 - 340
        self.bar_bounds.y1 = bounds.y2 - 60
        self.bar_bounds.x2 = bounds.x2 - 40
        self.bar_bounds.y2 = bounds.y2 - 50
        self.bot.bounds["fishing bar"] = self.bar_bounds
        self.bot.add_render_area("fishing bar")

        self.reticule_regularity = 1
        self.bar_top_y = None
        self.bar_middle_x = None

        self.try_catch_within = 6  # How many pixels the fish has to be within before I attempt to catch.
        self.catching_delay = 120  # How many frames to wait after catching a fish
        self.catching = 0
        self.object_history_size = 50
        self.object_move_history = np.zeros(self.object_history_size)
        self.object_move_speed = 0

    def desired_views(self):
        return ["fishing bar"]

    def find_bar_reticule(self):
        s = self.bar.shape
        for y in range(s[0]):
            for x in range(s[1]):
                col = self.bar[y][x]
                # Red or cyan. This is done for the cursed fishing rod.
                if (col[0] < 20 and col[1] < 20 and col[2] > 250) or \
                        (col[0] > 250 and col[1] > 250 and col[2] < 20):
                    self.bar_top_y = y
                    self.bar_middle_x = x
                    return

    def track_fish(self):
        if self.bar_top_y:
            fish_pos = 0
            for x in range(self.bar_bounds.width):
                col = self.bar[self.bar_top_y][x]
                if col[2] > 200 and col[1] > 100 and col[0] < 50:  # orange
                    fish_pos = x
                    break

            self.object_move_history = np.roll(self.object_move_history, -1)
            self.object_move_history[-1] = fish_pos

    def is_fish_on_reticule(self):
        if self.bar_top_y:
            # Check four pixels to the left and right
            for i in range(3):
                off = i-1
                col = self.bar[self.bar_top_y][self.bar_middle_x + off]
                if col[2] > 200 and col[1] > 100 and col[0] < 50:  # orange
                    return True

    def update(self):
        self.bar = self.bot.get_view("fishing bar")
        if self.bar_middle_x is not None and self.is_fish_on_reticule():
            self.bot.hands.press_key(pynput.keyboard.Key.space, 4)
        if self.bot.frame_num % self.reticule_regularity == 0:
            self.find_bar_reticule()
        return
        self.track_fish()

        # Is fish close enough to prepare to catch?
        if self.catching >= 0\
                or not abs(self.object_move_history[-1] - self.bar_middle_x) <= self.try_catch_within:
            return

        # Calculate how many pixels the fish moves per frame.
        last_pos = -1
        fish_velocity = 0
        for pos in self.object_move_history:
            if pos == 0:
                # skipped += 1
                continue
            if last_pos == -1:
                last_pos = pos
                continue
            diff = abs(last_pos - pos)
            fish_velocity = (fish_velocity + diff) / 2
            last_pos = pos

        # When will the fish reach us?
        if fish_velocity == 0:
            return
        dist = abs(self.bar_middle_x - self.object_move_history[-1])
        frames_till = round(dist / fish_velocity)
        self.bot.hands.press_key(pynput.keyboard.Key.space, 4, frames_till)
        self.catching = self.catching_delay
