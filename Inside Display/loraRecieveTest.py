# Import Libraries

import time

import board
import busio
import digitalio

from adafruit_rfm9x import RFM9x

# LoRa

spi = busio.SPI(board.GP18, board.GP19, board.GP16)
rfm_cs = digitalio.DigitalInOut(board.GP21)
rfm_reset = digitalio.DigitalInOut(board.GP20)

lora = RFM9x(spi, rfm_cs, rfm_reset, 915.0)

# --- end peripherals ---

while True:
    msg = ""
    msg = lora.receive(timeout=3)
    print(f"Got: <{msg}>")
    if msg:
        lora.send(msg)
