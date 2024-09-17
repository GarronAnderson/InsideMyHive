# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Simple test script for Adafruit 2.9" 296x128 tri-color display
Supported products:
  * Adafruit 2.9" Tri-Color Display Breakout
  * https://www.adafruit.com/product/1028
"""

import time
import board
import displayio
import busio
import adafruit_uc8151d
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.arc import Arc
from adafruit_display_shapes.roundrect import RoundRect
import terminalio
from adafruit_display_text import label


# For 8.x.x and 9.x.x. When 8.x.x is discontinued as a stable release, change this.
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

# Used to ensure the display is free in CircuitPython
displayio.release_displays()

# Define the pins needed for display use
# This pinout is for a Feather M4 and may be different for other boards
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)
epd_cs = board.GP12
epd_dc = board.GP13


# Create the displayio connection to the display pins
display_bus = FourWire(
    spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000
)
time.sleep(1)  # Wait a bit

# Create the display object - the third color is red (0xff0000)
display = adafruit_uc8151d.UC8151D(
    display_bus,
    width=296,
    height=128,
    rotation=270,
    highlight_color=0xFF0000,
)

g = displayio.Group()

text = "HELLO WORLD"
font = terminalio.FONT
color = 0x000000

# Create the text label
text_area = label.Label(font, text=text, color=color, background_color=0xFFFFFF)

# Set the location
text_area.x = 100
text_area.y = 80

g.append(text_area)

# Show it
display.root_group = g

# Refresh the display to have it actually show the image
# NOTE: Do not refresh eInk displays sooner than 180 seconds
input("Press enter to refresh")
display.refresh()
print("refreshed")

time.sleep(180)

