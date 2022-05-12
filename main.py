import pynput
import cv2
import numpy as np
import time
from mss import mss
import win32gui
import multiprocessing
import multiprocessing.shared_memory
import pickle
from tools import BoundingBox
from button_click import ButtonClicker
from fishing import Fisher
from avoidance import Avoidance


class Bot:
    """also known as: Brain. This is the storage/action center"""
    def __init__(self):
        self.bounds = {}
        self.shared_bounds = {}  # Used by renderer.
        self.views = {}  # All of the views that can be rendered. They must be requested in self.render_areas
        self.find_bounds()

        self.paused = multiprocessing.Value("B", 0)

        self.frame_rate = 40
        self.seconds_per_frame = 1 / self.frame_rate

        self.frame_times = []
        self.frame_time_memory = 5 * self.frame_rate
        self.frame_num = 0
        self.frames_slow = 0

        # Where on the screen to render next frame.
        # The whitespace default is done to force it to use a larger buffer, fit bigger words.
        self.render_areas = multiprocessing.shared_memory.ShareableList(["                   "]*5, name="render areas")
        # TODO: Pass render debug info to renderer
        self.render_speed = 1  # How regularly, in frames, the screen refreshes.
        self.render_times = []
        self.render_time_memory = self.frame_time_memory
        self.render_num = 0
        self.renders_slow = 0
        self.lock = multiprocessing.Lock()

        #self.current_task = ButtonClicker(self)
        self.current_task = Fisher(self)

        # limbs
        self.hands = Hands()

    def start(self):
        keyboard_listener = pynput.keyboard.Listener(on_press=self.debug_buttons)
        keyboard_listener.start()
        print("Press f1 to pause")

        # To get this working, I'm using both many forms of shared memory -
        # SharedMemory and ShareableList is used to communicate unknown or complex data
        # Value is used to communicate basic data, such as debugging values or the paused state.
        render_loop = multiprocessing.Process(target=render, args=(self.paused, self.lock), daemon=True)
        render_loop.start()
        self.update()

    def add_render_area(self, name):
        b = self.bounds[name]

        self.shared_bounds[name] = multiprocessing.shared_memory.SharedMemory(name=f"{name} area", create=True, size=4096 * 2)
        p = pickle.dumps(b)
        self.shared_bounds[name].buf[:len(p)] = p[:]

        size = b.width * b.height * 4
        self.views[name] = multiprocessing.shared_memory.SharedMemory(name=f"{name} render", create=True, size=size)

    def find_bounds(self):
        # Find the window.
        window_handle = win32gui.FindWindow(None, "Adobe Flash Player 9")
        if window_handle == 0:
            raise RuntimeError("Cannot find game window.")
        bounds = BoundingBox(*win32gui.GetWindowRect(window_handle))
        b = BoundingBox()
        mid = {"x": int((bounds.x1 + bounds.x2) / 2), "y": int((bounds.y1 + bounds.y2) / 2)}
        if bounds.width > bounds.height:
            size = bounds.height
        else:
            size = bounds.width

        b.y1 = int(mid["y"] - (size/2))
        b.y2 = int(mid["y"] + (size/2))
        b.x1 = int(mid["x"] - (size/2))
        b.x2 = int(mid["x"] + (size/2))
        self.bounds["window"] = b
        self.add_render_area("window")

        # Find the minigame area.
        c = BoundingBox()
        c.x1 = int(b.x1 + (b.width * 0.03))
        c.x2 = int(b.x1 + (b.width * 0.776))
        c.y1 = int(b.y1 + (b.height * 0.14))
        c.y2 = int(b.y1 + (b.height * 0.67))
        self.bounds["minigame"] = c
        self.add_render_area("minigame")

        # canvas = take_screenshot(self.minigame_bounds)[0]
        # # cv2.rectangle(canvas,
        # #               (self.minigame_bounds.x1, self.minigame_bounds.y1),
        # #               (self.minigame_bounds.x2, self.minigame_bounds.y2),
        # #               (128, 128, 0))
        # # canvas = cv2.resize(canvas, (500, 500))
        # cv2.imshow("", canvas)
        # cv2.waitKey(0)

    def get_view(self, view_name) -> np.array:
        if view_name is None:
            return None
        w = self.bounds[view_name].width
        h = self.bounds[view_name].height
        buffered_array = np.ndarray((h, w, 4), dtype=np.uint8, buffer=self.views[view_name].buf)
        new = buffered_array.copy()
        return new

    def debug_buttons(self, key):
        if key == pynput.keyboard.Key.f1:
            self.paused.value = not self.paused.value
            print("paused" if self.paused.value else "unpaused")
            return
        elif key == pynput.keyboard.Key.f2:
            if len(self.frame_times) > 0:
                average_time = 0
                for time in self.frame_times:
                    average_time += time
                average_time = 1 / (average_time / len(self.frame_times))
                print(f"FPS: {average_time}")
                print(f"Frame times: {self.frame_times}")
                print(f"Frames slow: {self.frames_slow / max(self.frame_num, 1) * 100}%")
            if len(self.render_times) > 0:
                print(f"Render times: {self.render_times}")
                print(f"Renders slow: {self.renders_slow / max(self.render_num, 1) * 100}%")
            print()
        elif key == pynput.keyboard.Key.f3:
            for area in self.render_areas:
                view = self.get_view(area)
                if view is not None:
                    cv2.imshow(f"{area} view", view)
            cv2.waitKey(0)
        elif key == pynput.keyboard.Key.f4:
            # TODO: Print positions relative to minigame, window.
            x = self.hands.mouse_x
            y = self.hands.mouse_y
            print(f"Screen pos:\nx: {self.hands.mouse_x}\ny: {self.hands.mouse_y}")

            b = self.bounds["window"]
            w_percent = (x - b.x1) / b.width
            h_percent = (y - b.y1) / b.height
            print(f"Relative to window area:\nx: {w_percent}%\ny: {h_percent}%")

            b = self.bounds["minigame"]
            w_percent = (x - b.x1) / b.width
            h_percent = (y - b.y1) / b.height
            print(f"Relative to minigame area:\nx: {w_percent}%\ny: {h_percent}%")
            print()

    def get_views(self):
        #self.window_view, self.minigame_view = take_screenshot(self.window_bounds, self.minigame_bounds)
        #self.minigame_view = take_screenshot(self.minigame_bounds)
        self.minigame_view = take_screenshot(BoundingBox(0, 0, 100, 100))

    def update(self):
        while True:
            if self.paused.value:
                self.hands.clear()
                time.sleep(0.2)
                continue
            # We floor the start here to more accurately calculate the time passed.
            frame_start = time.perf_counter()

            # Update which frames should be displayed.
            with self.lock:
                l = [None] * 5
                gathered_data = self.current_task.desired_views()
                l[:len(gathered_data)] = gathered_data[:]
                areas = multiprocessing.shared_memory.ShareableList(name="render areas")
                for i in range(len(l)):
                    areas[i] = l[i]

            self.hands.update()

            if self.current_task is not None:
                #self.current_task.debug()
                self.current_task.update()

            # Wait for next frame
            frame_slow, frame_time = frame_lock(frame_start, self.seconds_per_frame)
            # Update debugging stats.
            self.frame_num += 1
            self.frames_slow += 1 if frame_slow else 0
            if len(self.frame_times) == self.frame_time_memory:
                self.frame_times.pop(0)
            self.frame_times.append(frame_time)


class Hands:
    """The bot's hands, aka keyboard + mouse"""
    def __init__(self):
        self.mouse = pynput.mouse.Controller()
        self.keyboard = pynput.keyboard.Controller()

        self.click_command = {"duration": 0, "delay": 0}
        self.clicking_for = 0  # How many frames we are clicking for.
        self.is_clicking = False
        self.held_keys = dict()  # Keycode: {timing data}

    @property
    def mouse_x(self):
        return self.mouse.position[0]

    @property
    def mouse_y(self):
        return self.mouse.position[1]

    def update(self):
        if self.click_command["delay"] > 0:
            self.click_command["delay"] -= 1
            if self.click_command["delay"] == 0:
                self.mouse.press(pynput.mouse.Button.left)
        else:
            self.click_command["duration"] -= 1
            if self.click_command["duration"] == 0:
                self.mouse.release(pynput.mouse.Button.left)

        keys_to_remove = []
        for keycode, timings in self.held_keys.items():
            # Count down delay
            if timings["delay"] > 0:
                timings["delay"] -= 1
                if timings["delay"] == 0:
                    self.keyboard.press(keycode)
            # Count down held button
            else:
                timings["duration"] -= 1
                if timings["duration"] <= 0:
                    self.keyboard.release(keycode)
                    keys_to_remove.append(keycode)
        # Remove keys that finished.
        for k in keys_to_remove:
            del self.held_keys[k]

    def clear(self):
        if self.click_command["duration"] > 0 or self.click_command["delay"] > 0:
            self.mouse.release(pynput.mouse.Button.left)
            self.click_command["duration"] = 0
            self.click_command["delay"] = 0

        for keycode in self.held_keys:
            self.keyboard.release(keycode)
        self.held_keys = dict()

    def click(self, duration=1, delay=0) -> bool:
        """Click."""
        if self.click_command["duration"] >= 0:
            return False
        if delay == 0:
            self.mouse.press(pynput.mouse.Button.left)
        self.click_command["duration"] = duration
        self.click_command["delay"] = delay
        return True

    def is_clicking(self) -> bool:
        if self.click_command["duration"] <= 0:
            return False
        return True

    def move(self, x, y):
        """Move somewhere."""
        self.mouse.position = (x, y)

    def press_key(self, key, duration=1, delay=0) -> bool:
        if key in self.held_keys:
            return False
        if delay == 0:
            self.keyboard.press(key)
        self.held_keys[key] = {"duration": duration, "delay": delay}
        return True


def render(paused, lock: multiprocessing.Lock):
    while True:
        if paused.value:
            time.sleep(0.1)
            continue
        render_start = time.perf_counter()
        with lock:
            names = multiprocessing.shared_memory.ShareableList(name="render areas")
            names = [x for x in names]
        render_areas = []
        for name in names:
            if name is None:
                continue
            try:
                render_area = multiprocessing.shared_memory.SharedMemory(name=f"{name} area")
            except FileNotFoundError:
                print(f"Could not find shared memory called: {name}")
                continue
            render_areas.append(pickle.loads(render_area.buf))  # Ignore this warning, it works.
            render_area.close()

        # render the areas
        renders = take_screenshot(*render_areas)

        for i in range(len(renders)):
            name = names[i]
            render = renders[i]
            out = multiprocessing.shared_memory.SharedMemory(name=f"{name} render")
            np_array = np.ndarray(render.shape, dtype=np.uint8, buffer=out.buf)
            np_array[:] = render[:]
            out.close()

        # Wait for next frame
        slow, time_taken = frame_lock(render_start, 0.025)
        #return
        # render_start = time.perf_counter()
        #
        # bot.get_views()
        #
        # # Wait for next frame
        # render_slow, render_time = bot.frame_lock(render_start, bot.seconds_per_frame * bot.render_speed)
        # # Update debugging stats.
        # bot.render_num += 1
        # bot.renders_slow += 1 if render_slow else 0
        # if len(bot.render_times) == bot.render_time_memory:
        #     bot.render_times.pop(0)
        # bot.render_times.append(render_time)


def take_screenshot(*args: BoundingBox) -> list[np.array]:
    ret = []
    with mss() as screenshot:
        for bounds in args:
            #image = ImageGrab.grab(bbox=(bounds.x1, bounds.y1, bounds.x2, bounds.y2))  # x, y, x2, y2
            area = {"top": bounds.y1, "left": bounds.x1, "width": bounds.width, "height": bounds.height}
            image = screenshot.grab(area)
            image_np = np.array(image)
            #image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
            ret.append(image_np)
    return ret


def until_multiple(value, multiple, min_size=0.0):
    # Distance between value and the next multiple of a number.
    assert multiple > 0

    past_multiple = value % multiple
    until = multiple - past_multiple
    slow = 0
    while until < min_size:
        until += multiple
        slow += 1
    return until, slow


def pass_cycles(number):
    # not accurate but nor is time.sleep so fuck you
    n = 0
    while n < number:
        n += 1
        pass


def frame_lock(frame_start, seconds_per_frame) -> (bool, float):
    """Waits until the next frame 'cycle'
    args:
        frame_start - The time this frame started
        seconds_per_frame - How long each frame is
    returns:
        tuple(frame_slow, total_frame_time)
        frame_slow - Whether this took too long
        total_frame_time - How long the whole frame took, in seconds
    """
    frame_slow = False

    # What cycle did this frame start on?
    frame_cycle = frame_start - (frame_start % seconds_per_frame)

    # Are we already late on this frame?
    frame_end = time.perf_counter()
    time_passed = frame_end - frame_cycle
    if time_passed >= seconds_per_frame:
        frame_slow = True

    # Wait till next frame window.
    time_since_cycle = time.perf_counter() - frame_cycle
    # LET ME TAKE YOU ON A JOURNEY. Imagine, say, you wish to wait for... 5ms. The start of the next frame.
    # A simple task for a computer, that runs at at the billions of clock cycles per seconds, no?
    # no.
    # Indeed it is not up to the cpu but the OS. Most operating systems are only accurate to about 13ms.
    # Anything below this, and you might as well have just put 13ms in the first place.
    # Okay so we can't use time.sleep, what if instead we schedule something to run every frame time, every 25ms?
    # Ahh, a great idea! However, no. What you will find is that there is no multiprocessing solution
    #  to repeatedly running a task at a set time. You'd think it'd be so simple
    # Every 25ms, check if a task has finished. If it has, restart it. If not, skip it.
    # Nope! Threads and processes are destroyed at their end, and there's only *one* way to temporarily suspend a thread.
    # Do you know what it is? That's right. TIME.SLEEP THAT INACCURATE BULLSHIT
    # In the end I found my solution in just using a shit tonne of `pass` calls to pass time
    #  without lagging my whole pc.
    while time_since_cycle < seconds_per_frame:
        if seconds_per_frame - time_since_cycle > 0.015:
            time.sleep(0.00001)  # stops it lagging my pc 24/7. waits up to 15ms
        else:
            pass_cycles(2000)  # More granular control over time.
        time_since_cycle = time.perf_counter() - frame_start

    frame_time = time.perf_counter() - frame_start
    return frame_slow, frame_time


def main():
    bot = Bot()
    # Enters the main loop.
    bot.start()


def winEnumHandler(hwnd, ctx):
    if win32gui.IsWindowVisible( hwnd ):
        print (hex(hwnd), win32gui.GetWindowText( hwnd ))
#win32gui.EnumWindows(winEnumHandler, None)


if __name__ == "__main__":
    main()
