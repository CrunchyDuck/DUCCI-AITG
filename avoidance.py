import pynput
import numpy as np
import cv2
import math
import time
import threading


class Avoidance:
    def __init__(self, bot):
        self.bot = bot
        self.starting = True
        self.regions = 5
        self.region_margin = 2  # How many regions, at the top and bottom, act as padding.
        self.safety_area = 100  # Measured in pixels which is a little poor form, but it shouldn't matter for me.
        self.safety_spots = 10  # How many points x/y are checked in the safety area.
        self.pressing_key = 0
        self.test = True

        self.object_detector = cv2.createBackgroundSubtractorMOG2(history=30, varThreshold=40)
        self.update_views = threading.Thread(target=self.show_detect, daemon=True)
        self.update_views.start()

    def show_detect(self):
        while True:
            mask = self.object_detector.apply(self.bot.minigame_view)
            cv2.imshow("det", mask)
            cv2.waitKey(30)

    def update(self):
        pass

    def updatasde(self):
        bounds = self.bot.minigame_bounds
        view = self.bot.minigame_view

        if self.starting:
            self.starting = not self.starting
            self.bot.hands.move(bounds.x1 + bounds.width/2, bounds.y1 + bounds.height/2)

        # Is there a bonus that isn't in danger?
        pass

        # Are we currently moving?
        if self.pressing_key > 0:
            self.pressing_key -= 1
            return

        if not self.test:
            return
        start = time.perf_counter()
        # Check the danger of the field.
        #canvas = view.copy()
        interval_size_x = bounds.width / (self.regions + (self.region_margin * 2) - 1)
        interval_size_y = bounds.height / (self.regions + (self.region_margin * 2) - 1)
        i = 0
        danger_grid = []
        for x in range(self.regions):
            for y in range(self.regions):
                i += 1
                x_pos = math.floor((x + self.region_margin) * interval_size_x)
                y_pos = math.floor((y + self.region_margin) * interval_size_y)
                #cv2.rectangle(canvas, (x_pos - self.safety_area, y_pos - self.safety_area),(x_pos + self.safety_area, y_pos + self.safety_area), (50 + i * ((255-50) / self.regions**2), 255, 255), -1)

                danger = self.check_pixel_danger(x_pos, y_pos, bounds, view)
                dat = [danger, x_pos, y_pos]
                danger_grid.append(dat)
        #print(f"danger time: {time.perf_counter() - start}")

        start = time.perf_counter()
        # Find the least dangerous spot.
        safest = 999999999
        x_pos = 0
        y_pos = 0
        for spot in danger_grid:
            if spot[0] < safest:
                safest = spot[0]
                x_pos = spot[1]
                y_pos = spot[2]
        #print(f"sort time: {time.perf_counter() - start}")
        #self.test = False

        current_safety = self.check_pixel_danger(self.bot.hands.mouse_x - bounds.x1, self.bot.hands.mouse_y - bounds.y1, bounds, view)
        if safest < current_safety:
            self.bot.hands.press_key(pynput.keyboard.Key.shift, 2)
            self.bot.hands.move(bounds.x1 + x_pos, bounds.y1 + y_pos)
            self.pressing_key = 2
        return

        if not self.check_pixel_danger(x_pos, y_pos, bounds, view):
            self.bot.hands.press_key(pynput.keyboard.Key.shift, 1)
            self.bot.hands.move(bounds.x1 + x_pos, bounds.y1 + y_pos)
            self.pressing_key = 1
            cv2.rectangle(canvas, (x_pos - self.safety_area, y_pos - self.safety_area), (x_pos + self.safety_area, y_pos + self.safety_area), (255, 255, 255), 5)
            return
        else:
            pass
            cv2.rectangle(canvas, (x_pos - self.safety_area, y_pos - self.safety_area), (x_pos + self.safety_area, y_pos + self.safety_area), (0, 0, 0), 5)

    def check_pixel_danger(self, x, y, bounds, view):
        x1 = min(max(x - self.safety_area, 0), bounds.width - 1)
        y1 = min(max(y - self.safety_area, 0), bounds.height - 1)
        x2 = min(max(x + self.safety_area, 0), bounds.width - 1)
        y2 = min(max(y + self.safety_area, 0), bounds.height - 1)
        w = x2 - x1
        h = y2 - y1

        danger = 0
        middle = self.safety_spots / 2
        _square_size_x = w / self.regions
        _square_size_y = h / self.regions

        #canvas = view.copy()
        for x in range(self.safety_spots):
            for y in range(self.safety_spots):
                x_pos = min(max(math.floor(x * (w / self.regions) + x1), 0), bounds.width-1)
                y_pos = min(max(math.floor(y * (h / self.regions) + y1), 0), bounds.height-1)
                #y_pos = math.floor(y * (h / self.regions) + y1)

                # _color_intervals = 255 // middle
                # danger_level = abs(middle - distance_from_middle)
                # color = _color_intervals * danger_level
                # cv2.rectangle(canvas,
                #               (int(x_pos - _square_size_x), int(y_pos - _square_size_y)),
                #               (int(x_pos + _square_size_x), int(y_pos + _square_size_y)),
                #               (color, color, color, 255), -1)
                if np.array_equal(view[y_pos][x_pos], (9, 22, 216, 255)):
                    # Spots further from the center are less dangerous.
                    a = (x - middle) ** 2
                    b = (y - middle) ** 2
                    c = math.sqrt(a + b)
                    distance_from_middle = c
                    danger += abs(middle - distance_from_middle)

        #cv2.imshow("", canvas)
        #cv2.waitKey(0)
        return danger
