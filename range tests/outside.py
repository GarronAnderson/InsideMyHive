"""
Outside range test.

Responds to messages sent from inside.
"""

import time

import board
import busio
import digitalio

from adafruit_rfm9x import RFM9x

from helpers import StatusLED

# fmt: off
lora_tx    = StatusLED(board.A3)
lora_rx    = StatusLED(board.D24)
lora_good  = StatusLED(board.A2)
# fmt: on

print("init lora")
spi = board.SPI()
rfm_cs = digitalio.DigitalInOut(board.D6)
rfm_reset = digitalio.DigitalInOut(board.D9)

lora = RFM9x(spi, rfm_cs, rfm_reset, LORA_FREQ)
lora.tx_power = 23
lora.spreading_factor = 11

symbolDuration = 1000 / (lora.signal_bandwidth / (1 << lora.spreading_factor))
if symbolDuration > 16:
    lora.low_datarate_optimize = 1
    print("low datarate on")
else:
    lora.low_datarate_optimize = 0
    print("low datarate off")

lora.xmit_timeout = 10

lora_good.on()

while True:
    lora_good.blink(1)
    lora_good.on()
    msg = lora.receive(timeout=5)
    
    if msg is not None:
        msg = msg.decode()
        lora_tx.on()
        time.sleep(0.1)
        lora.send(msg)
        lora_tx.off()
    