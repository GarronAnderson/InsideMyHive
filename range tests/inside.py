"""
Inside Range Tester

Sends msg to outside box.

Prints RSSI.
"""

import time
import board
import digitalio

import sdcardio
import storage

import sys

import circuitpython_csv as csv

# LoRa
from adafruit_rfm9x import RFM9x

from helpers import StatusLED

# fmt: off
rx_led    = StatusLED(board.A3)
tx_led    = StatusLED(board.D10)
# fmt: on

# LoRa

spi = board.SPI()

rfm_cs = digitalio.DigitalInOut(board.D25)
rfm_reset = digitalio.DigitalInOut(board.D24)

lora = RFM9x(spi, rfm_cs, rfm_reset, 915.0)
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

sd_cs = board.D5

sdcard = sdcardio.SDCard(spi, sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

print("got lora")

print("mainloop start")

test_msg = "range test"

f = open("/sd/rangeData.csv", "w")
writer = csv.writer(f)

writer.writerow(["time", "rssi", "snr"])

try:
    while True:
        print("sending msg")
        tx_led.on()
        lora.send(test_msg)
        tx_led.off()
        rx_led.on()
        msg = lora.receive(timeout=5)
        rx_led.off()

        if msg is None:
            print("no ack")
        else:
            msg = msg.decode()

        if msg == test_msg:
            print("got good ack")
            print(f"RSSI: {lora.last_rssi} dBm")
            print(f"SNR:  {lora.last_snr} dB\n")
            writer.writerow([time.time(), lora.last_rssi, lora.last_snr])
        else:
            print("bad ack")

        time.sleep(5)
except:
    print("caught")
    f.close()
    sys.exit()
