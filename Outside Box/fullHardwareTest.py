# Import Libraries

import time

import board
import busio
import digitalio
import neopixel

from adafruit_rfm9x import RFM9x
from cedargrove_nau7802 import NAU7802
from adafruit_htu21d import HTU21D
from adafruit_max1704x import MAX17048

# --- Set up peripherals ---

i2c = board.STEMMA_I2C()

# sensors

scale = NAU7802(i2c)
temp = HTU21D(i2c)
battery = MAX17048(i2c)

# LoRa

spi = board.SPI()
rfm_cs = digitalio.DigitalInOut(board.D6)
rfm_reset = digitalio.DigitalInOut(board.D9)

lora = RFM9x(spi, rfm_cs, rfm_reset, 915.0)

# board neopixel

led = neopixel.NeoPixel(board.NEOPIXEL, 1)
led.brightness = 0.2

# --- end peripherals ---

# --- reset scale ---

scale.channel = 1
scale.calibrate("INTERNAL")
scale.calibrate("OFFSET")


def wait_for(msg):
    led[0] = (66, 245, 233)
    got = ""
    while got != msg:
        got = lora.receive(timeout=3)
    led[0] = (0, 255, 0)


def c_to_f(deg):
    return (deg * (9 / 5)) + 32


def send(msg):
    led[0] = (255, 0, 0)
    print(f"Sending {msg}")
    lora.send(msg)
    led[0] = (0, 255, 0)


while True:
    send(f"Battery V: {battery.cell_voltage}")
    wait_for("ack")
    time.sleep(1)
    send(f"Scale: {scale.read()}")
    wait_for("ack")
    time.sleep(1)
    send(f"Temp: {c_to_f(temp.temperature)}")
    wait_for("ack")
    time.sleep(1)
    send(f"Relative Humidity: {temp.relative_humidity}")
    wait_for("ack")
    time.sleep(1)
