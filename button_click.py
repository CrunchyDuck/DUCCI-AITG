import cv2
import numpy as np


class ButtonClicker:
    def __init__(self, bot):
        self.bot = bot
        self.frame = 0
        self.regularity = 7

    def desired_views(self):
        return ["minigame"]

    def update(self):
        if self.frame % self.regularity == 0:
            self.frame = 0
            self.click_button()
        self.frame += 1

    def click_button(self):
        img = cv2.cvtColor(self.bot.get_view("minigame"), cv2.COLOR_RGB2GRAY)
        circles = self.find_circles(img)
        if circles is not None:
            for (x, y, r) in circles:
                pixel = img[y][x]
                if np.equal(pixel, 81) or np.equal(pixel, 119):  # orange or blue button in greyscale
                    self.bot.hands.move(x + self.bot.bounds["minigame"].x1, y + self.bot.bounds["minigame"].y1)
                    self.bot.hands.click()
                    break
        else:
            # Check if the button is broken.
            pass

    def find_circles(self, image):
        # grey = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        # detect circles in the image
        circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, 1.3, 20, minRadius=1, maxRadius=150)
        if circles is not None:
            # convert the (x, y) coordinates and radius of the circles to integers
            circles = np.round(circles[0, :]).astype("int")
        return circles
