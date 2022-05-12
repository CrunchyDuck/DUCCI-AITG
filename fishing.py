import pynput
import numpy as np
from tools import BoundingBox, ColorRange
import cv2


class Fisher:
    def __init__(self, bot):
        self.bot = bot
        self.bar = None

        bounds = self.bot.bounds["minigame"]

        # Fishing bar bounds
        self.bar_bounds = BoundingBox(parent=bounds)
        # TODO: Make this a relative value rather than a set pixel value.
        self.bar_bounds.x1 = bounds.x2 - 340
        self.bar_bounds.y1 = bounds.y2 - 60
        self.bar_bounds.x2 = bounds.x2 - 40
        self.bar_bounds.y2 = bounds.y2 - 50
        self.bot.bounds["fishing bar"] = self.bar_bounds
        self.bot.add_render_area("fishing bar")

        # Close button bounds
        self.close_window_red = ColorRange((0, 0, 255, 255), (0, 102, 255, 255))
        x1 = bounds.x1 + bounds.width * 0.931
        y1 = bounds.y1 + bounds.height * 0.254
        x2 = bounds.x1 + bounds.width * 0.964
        y2 = bounds.y1 + bounds.width * 0.294
        self.close_button_bounds = BoundingBox(x1, y1, x2, y2)
        self.bot.bounds["fishing popup"] = self.close_button_bounds
        self.bot.add_render_area("fishing popup")

        self.current_task = "fishing"

        self.reticule_regularity = 1
        self.bar_top_y = None
        self.bar_middle_x = None

        self.try_catch_within = 6  # How many pixels the fish has to be within before I attempt to catch.
        self.catching_delay = self.bot.frame_rate * 3  # How many frames to wait after catching a fish
        self.catching = 0
        self.object_history_size = 50
        self.object_move_history = np.zeros(self.object_history_size)
        self.object_move_speed = 0

    def desired_views(self):
        return ["fishing bar", "fishing popup"]

    def update(self):
        # TODO: Make sure the window is in focus before clicking.
        # TODO: Auto close reward popups
        # Check if a reward has popped up
        if self.bot.frame_num == 5:
            cv2.imshow("", self.bot.get_view("fishing popup"))
            cv2.waitKey(0)
        if self.current_task == "fishing":
            self.bar = self.bot.get_view("fishing bar")
            self.catching -= 1
            if self.catching <= 0 and self.bar_middle_x is not None and self.is_fish_on_reticule():
                self.bot.hands.press_key(pynput.keyboard.Key.space, 2)
                self.catching = self.catching_delay
            if self.bot.frame_num % self.reticule_regularity == 0:
                self.find_bar_reticule()

    def debug(self):
        # TODO: create debug for this
        pass

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

    def is_fish_on_reticule(self):
        if self.bar_top_y:
            # Check four pixels to the left and right
            for i in range(3):
                off = i-1
                col = self.bar[self.bar_top_y][self.bar_middle_x + off]
                if col[2] > 200 and col[1] > 100 and col[0] < 50:  # orange
                    return True
