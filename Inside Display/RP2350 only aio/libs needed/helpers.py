from adafruit_display_shapes.arc import Arc
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.polygon import Polygon
import displayio
import terminalio
from adafruit_display_text import label
import gc


class Gauge:
    def __init__(
        self, radius=30, x=0, y=0, max_alarm_val=101, left=0, right=100, units=""
    ):
        self.radius = radius
        self.x = x
        self.y = y
        self.val = 0
        self.max_alarm_val = max_alarm_val
        self.left = left
        self.right = right
        self.units = units

    @staticmethod
    def _map(value, leftMin, leftMax, rightMin, rightMax):
        # Figure out how 'wide' each range is
        leftSpan = leftMax - leftMin
        rightSpan = rightMax - rightMin

        # Convert the left range into a 0-1 range (float)
        valueScaled = float(value - leftMin) / float(leftSpan)

        # Convert the 0-1 range into a value in the right range.
        return rightMin + (valueScaled * rightSpan)

    def update(self, val):
        self.val = val

    def render(self):
        outer_arc = Arc(
            self.radius,
            260,
            90,
            25,
            arc_width=10,
            outline=0x0,
            fill=0xFFFFFF,
            x=self.x,
            y=self.y,
        )

        arc_val = self._map(self.val, self.left, self.right, 0, 260)
        arc_angle = (-arc_val / 2) + 220

        alarm_ind_val = self._map(self.max_alarm_val, self.left, self.right, 0, 260)
        alarm_ind_angle = (-alarm_ind_val / 2) + 220

        alarm_arc = Arc(
            self.radius,
            alarm_ind_val,
            alarm_ind_angle,
            25,
            arc_width=10,
            outline=0x0,
            fill=0xFFFFFF,
            x=self.x,
            y=self.y,
        )

        alarming = self.val > self.max_alarm_val
        fill_color = 0xFF0000 if alarming else 0x000000

        inner_arc = Arc(
            self.radius,
            arc_val,
            arc_angle,
            25,
            arc_width=10,
            outline=0x0,
            fill=fill_color,
            x=self.x,
            y=self.y,
        )

        text_val = label.Label(
            terminalio.FONT, text=str(round(self.val, 0)), color=0x0, scale=2
        )
        text_val.anchor_point = (0.5, 0.5)
        text_val.anchored_position = (self.x, self.y)

        text_unit = label.Label(terminalio.FONT, text=self.units, color=0x0)
        text_unit.anchor_point = (0.5, 0.5)
        text_unit.anchored_position = (self.x, self.y + 20)

        text_lbl_left = label.Label(terminalio.FONT, text=str(self.left), color=0x0)
        text_lbl_left.anchor_point = (0.5, 0.5)
        text_lbl_left.anchored_position = (self.x - 20, self.y + 27)

        text_lbl_rgt = label.Label(terminalio.FONT, text=str(self.right), color=0x0)
        text_lbl_rgt.anchor_point = (0.5, 0.5)
        text_lbl_rgt.anchored_position = (self.x + 20, self.y + 27)

        g = displayio.Group()

        g.append(text_val)
        del text_val
        g.append(text_unit)
        del text_unit
        g.append(text_lbl_left)
        del text_lbl_left
        g.append(text_lbl_rgt)
        del text_lbl_rgt

        g.append(outer_arc)
        del outer_arc
        g.append(alarm_arc)
        del alarm_arc
        g.append(inner_arc)
        del inner_arc

        gc.collect()

        return g


class BatteryIndicator:
    def __init__(self, scale=2, x=0, y=0):
        self.scale = scale

        self.x = x
        self.y = y

        self._points = [(0, 0), (8, 0), (8, 1), (9, 1), (9, 3), (8, 3), (8, 4), (0, 4)]
        self._points_scaled = [
            (((point[0] * self.scale) + self.x), (point[1] * self.scale) + self.y)
            for point in self._points
        ]

        self.val = 0

    def update(self, val):
        self.val = val

    def render(self):
        g = displayio.Group()

        batt_low = self.val <= 20
        fill_color = 0xFF0000 if batt_low else 0x000000

        outer_poly = Polygon(points=self._points_scaled, close=True, outline=0x000000)

        if self.val < (8 / 9) * 100:  # value less than the tip of the battery
            rect_1 = Rect(
                x=self.x,
                y=self.y,
                height=self.scale * 4,
                width=int(round((self.val / 100) * (self.scale * 9), 0)) + 1,
                fill=fill_color,
            )
            g.append(rect_1)
            del rect_1
            g.append(outer_poly)
            del outer_poly

        else:  # value in tip of battery
            rect_1 = Rect(
                x=self.x,
                y=self.y,
                height=self.scale * 4,
                width=self.scale * 8,
                fill=fill_color,
            )
            rect_2 = Rect(
                x=self.x,
                y=self.y + self.scale,
                height=self.scale * 2,
                width=int(round((self.val / 100) * (self.scale * 9), 0)),
                fill=fill_color,
            )
            g.append(rect_1)
            del rect_1
            g.append(rect_2)
            del rect_2
            g.append(outer_poly)
            del outer_poly

        gc.collect()

        return g


class DisplayBox:
    def __init__(self, x=0, y=0, width=80, height=20, corner_r=4):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.corner_r = corner_r

        self.text = ""
        self.alarming = False

    def display(self, text):
        self.text = text
        self.alarming = False

    def alert(self, text):
        self.text = text
        self.alarming = True

    def render(self):
        text_color = 0xFF0000 if self.alarming else 0x000000

        roundrect = RoundRect(
            self.x,
            self.y,
            self.width,
            self.height,
            self.corner_r,
            fill=0xFFFFFF,
            outline=0x000000,
            stroke=2,
        )
        text_area = label.Label(
            terminalio.FONT, text=self.text, color=text_color, background_color=0xFFFFFF
        )

        text_area.x = self.x
        text_area.y = self.y

        g = displayio.Group()

        g.append(roundrect)
        del roundrect

        g.append(text_area)
        del text_area

        gc.collect()

        return g
