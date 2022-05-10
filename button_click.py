import cv2
import numpy as np
import tools


class ButtonClicker(tools.WorkerBase):
    def __init__(self, bot):
        self.bot = bot
        self.regularity = 2
        self.circle_edge_tolerance = 7  # How wide of an area to check for the edge of a circle.
        self.failed_to_find_button = 0  # How many times we've failed to find the button in a row.
        self.try_repair_after_fails = 5  # When to try to fix the button.
        self.current_task = "clicking button"
        # BGRA colours
        self.button_orange = (0, 100, 200, 255)
        self.button_blue = (200, 100, 0, 255)
        self.button_orange_edge = (0, 0, 153, 255)
        self.button_blue_edge = (153, 0, 0, 255)
        self.repair_yellow = (47, 175, 175, 255)
        b = self.bot.bounds["minigame"]
        x = int(b.width * 0.04)
        y = int(b.height * 0.95)
        self.repair_button_pos = tools.Vect2(x, y)

        # Debug data
        self.clicked_this_frame = False
        self.click_frame = None
        self.found_circles = None  # Array of circles
        self.found_button = False
        self.button_circle = None  # Circle identified as the button.
        self.button_edges = {}
        self.button_middle = None  # Vect2
        self.debug_open = False  # Only show one image at a time.

    def desired_views(self):
        return ["minigame"]

    def update(self):
        # TODO: Maybe try to calculate the "line" that the button moves along, based on the angle of the slider.
        # TODO: Track the speed of the button so I can predict where it will be next frame to click perfectly.
        #  This could be done by figuring our the gradient of the button area,
        #  the speed of the button, and the position of the button.
        self.clicked_this_frame = False
        if self.failed_to_find_button >= self.try_repair_after_fails:
            self.current_task = "fixing button"
            self.failed_to_find_button = 0
        if self.current_task == "clicking button":
            if self.bot.frame_num % self.regularity == 0:
                pos = self.find_button()
                if pos.x == -1:
                    # Failed to find button
                    self.found_button = False
                    self.failed_to_find_button += 1
                    return
                self.found_button = True
                self.button_middle = pos
                self.bot.hands.move(pos.x + self.bot.bounds["minigame"].x1, pos.y + self.bot.bounds["minigame"].y1)
                self.bot.hands.click()
                self.clicked_this_frame = True
                self.failed_to_find_button = 0
        elif self.current_task == "fixing button":
            img = self.bot.get_view("minigame")
            b = self.bot.bounds["minigame"]
            x = self.repair_button_pos.x
            y = self.repair_button_pos.y
            pixel = img[y][x]
            col = self.repair_yellow
            print(pixel, col)
            if not all(c1 >= c2 for c1, c2 in zip(pixel, col)):
                self.current_task = "clicking button"
                return
            real_x = b.x1 + x
            real_y = b.y1 + y
            self.bot.hands.move(real_x, real_y)
            if self.bot.hands.click(duration=3):
                self.current_task = "clicking button"
        else:
            print(f"Invalid task {self.current_task} for ButtonClicker.")
            self.current_task = "clicking button"

    def debug(self):
        if self.clicked_this_frame and not self.debug_open:
            purple = (255, 0, 255, 255)
            black = (0, 0, 0, 255)
            white = (255, 255, 255, 255)
            self.debug_open = True
            if self.found_circles is not None:
                found_circles_img = self.click_frame.copy()
                for circle in self.found_circles:
                    if self.button_circle is not None and np.array_equal(circle, self.button_circle):
                        continue
                    else:
                        col = white
                    x, y, r = circle
                    cv2.circle(found_circles_img, (x, y), r, col, 2)
                # Draw the button we found
                if self.button_circle is not None:
                    b_x, b_y, b_r = self.button_circle
                    cv2.circle(found_circles_img, (b_x, b_y), b_r, purple, 1)
                cv2.imshow("button debug circles", found_circles_img)
            if self.found_button:
                button_pos_img = self.click_frame.copy()
                b_x = int(self.button_middle.x)
                b_y = int(self.button_middle.y)
                c_len = 40

                # Draw left edge
                x = self.button_edges["l"]
                cv2.line(button_pos_img, (x, b_y - c_len), (x, b_y + c_len), purple, 1)
                # Draw right edge
                x = self.button_edges["r"]
                cv2.line(button_pos_img, (x, b_y - c_len), (x, b_y + c_len), purple, 1)
                # Draw top edge
                y = self.button_edges["t"]
                cv2.line(button_pos_img, (b_x - c_len, y), (b_x + c_len, y), purple, 1)
                # Draw bottom edge
                y = self.button_edges["b"]
                cv2.line(button_pos_img, (b_x - c_len, y), (b_x + c_len, y), purple, 1)

                # middle pixel horizontal line
                p1 = (b_x-c_len, b_y)
                p2 = (b_x+c_len, b_y)
                cv2.line(button_pos_img, p1, p2, black, 1)
                # middle pixel vertical line
                p1 = (b_x, b_y-c_len)
                p2 = (b_x, b_y+c_len)
                cv2.line(button_pos_img, p1, p2, black, 1)

                cv2.imshow("button debug position", button_pos_img)
            cv2.waitKey(0)
            self.debug_open = False

    def find_button(self):
        img = self.bot.get_view("minigame")
        self.click_frame = img
        img_grey = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        circles = self.find_circles(img_grey)
        pos = self.find_center_of_button(circles, img)
        return pos

    def find_circles(self, image_greyscale) -> np.ndarray:
        """
        Returns:
            Array of circles, described as (x, y, radius)
        """
        circles = cv2.HoughCircles(image_greyscale, cv2.HOUGH_GRADIENT, 1.3, 20, minRadius=1, maxRadius=150)
        if circles is not None:
            # convert the (x, y) coordinates and radius of the circles to integers
            circles = np.round(circles[0, :]).astype("int")
        return circles

    def find_center_of_button(self, circles: np.ndarray, image) -> tools.Vect2:
        if circles is None:
            return tools.Vect2(-1, -1)
        self.found_circles = circles
        for circle in circles:
            c_x, c_y, c_r = circle
            # is this circle even near the button?
            middle_pixel = image[c_y][c_x]
            if not np.array_equal(middle_pixel, self.button_orange) and \
                    not np.array_equal(middle_pixel, self.button_blue):
                continue

            # Find edges of circle
            tol = self.circle_edge_tolerance
            circle_left_bounds = range(
                max(c_x - c_r - tol, 0),
                min(c_x - c_r + tol, image.shape[1])
            )
            circle_top_bounds = range(
                max(c_y - c_r - tol, 0),
                min(c_y - c_r + tol, image.shape[0])
            )
            circle_right_bounds = range(
                min(c_x + c_r + tol, image.shape[1]),
                max(c_x + c_r - tol, 0),
                -1
            )
            circle_bottom_bounds = range(
                min(c_y + c_r + tol, image.shape[0]),
                max(c_y + c_r - tol, 0),
                -1
            )

            left_x = right_x = top_y = bottom_y = -1

            for x in circle_left_bounds:
                pixel = image[c_y][x]
                if np.array_equal(pixel, self.button_orange) or np.array_equal(pixel, self.button_blue):
                    left_x = x
                    break
            for x in circle_right_bounds:
                pixel = image[c_y][x]
                if np.array_equal(pixel, self.button_orange) or np.array_equal(pixel, self.button_blue):
                    right_x = x
                    break
            for y in circle_top_bounds:
                pixel = image[y][c_x]
                if np.array_equal(pixel, self.button_orange) or np.array_equal(pixel, self.button_blue):
                    top_y = y
                    break
            for y in circle_bottom_bounds:
                pixel = image[y][c_x]
                if np.array_equal(pixel, self.button_orange) or np.array_equal(pixel, self.button_blue):
                    bottom_y = y
                    break

            if left_x == -1 or right_x == -1 or top_y == -1 or bottom_y == -1:
                continue
            else:
                self.button_circle = circle
                self.button_edges = {"l": left_x, "t": top_y, "r": right_x, "b": bottom_y}
                x = (left_x + right_x) / 2
                y = (top_y + bottom_y) / 2
                return tools.Vect2(x, y)
        return tools.Vect2(-1, -1)
