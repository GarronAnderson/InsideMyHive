"""
Bee Box Monitor v1.2
By Garron Anderson, 2024
"""

# --- USER INPUT ---


# DATA_SEND_INTERVAL = 20  # seconds
# AVERAGE_UPDATE_INTERVAL = 2  # seconds

# real values, uncomment for actual run
DATA_SEND_INTERVAL = 120  # seconds, update every 5 minutes
AVERAGE_UPDATE_INTERVAL = 10  # seconds
LORA_FREQ = 915.0

# --- END USER INPUT ---

print("Bee Box Monitor")

# Import Libraries
print("import libraries")
import time

import board
import busio
import digitalio
import microcontroller

from adafruit_rfm9x import RFM9x
from cedargrove_nau7802 import NAU7802
from adafruit_htu21d import HTU21D

from helpers import RunningAverage, StatusLED


# --- Set up peripherals ---

# status leds
# fmt: off
batt_low   = StatusLED(board.A0)
sens_good  = StatusLED(board.A1)
lora_good  = StatusLED(board.A2)
lora_tx    = StatusLED(board.A3)
lora_rx    = StatusLED(board.D24)
# fmt: on

# start setup

print("init sensors")
sens_good.off()
i2c = board.STEMMA_I2C()

# sensors

scale = NAU7802(i2c)
temp = HTU21D(i2c)

# --- reset scale ---
print("calibrate scale, remove weights")
scale.channel = 1
scale.calibrate("INTERNAL")
scale.calibrate("OFFSET")

scale_avg = RunningAverage()

sens_good.on()

# LoRa
print("init lora")
spi = board.SPI()
rfm_cs = digitalio.DigitalInOut(board.D6)
rfm_reset = digitalio.DigitalInOut(board.D9)

lora = RFM9x(spi, rfm_cs, rfm_reset, LORA_FREQ)
lora.tx_power = 23
lora.spreading_factor = 11

lora_good.on()

# --- end peripherals ---


def c_to_f(deg):
    """
    Convert degrees Celsius to Fahrenheit.
    """

    return (deg * (9 / 5)) + 32


def send(msg):
    """
    Send a message via LoRa.

    Doesn't do anything fancy. Just sets the NeoPixel and prints to shell for debug.
    """
    lora_tx.on()
    time.sleep(0.1)
    print(f"Sending <{msg}>")
    lora.send(msg)
    lora_tx.off()


def send_w_ack(msg, timeout=2, max_fails=3):
    """
    Try to send a message with ack via LoRa. Wants the message back as ack.

    Returns a boolean of whether or not the transmission succeeded.

    Max timeout can be calculated as (timeout + 2) * max_fails.

    Default timeout 12 sec. (3 fails @ 4 secs per fail).
    """

    ack = ""
    fails = 0
    while fails < max_fails:
        time.sleep(0.1)
        send(msg)
        lora_rx.on()
        print("waiting for ack")
        ack = lora.receive(timeout=timeout)
        lora_rx.off()
        if ack == msg:
            print("good ack")
            return True

        fails = fails + 1

        print(f"bad ack or got nothing: <{ack}>")
        print(f"fails: {fails}")
        print()
        # alert user and retry
        lora_rx.blink(2)

    print("transmit failed, reached max fails with no good ack")
    print()

    lora_tx.blink(2)
    return False


def send_data():
    """
    Send the sensor data. Waits until the main box is ready.

    Updates last_good_tx if transmit good.

    Returns last_good_tx.
    If tx is bad, returns 0.
    """
    good_sends = [False]
    last_good_tx = 0

    for i in range(3):  # wait for inside ready
        good_hail = send_w_ack("data ready")
        if good_hail:  # inside ready
            print("good hail")
            break

        print(f"failed hails: {i+1}")
        time.sleep(10)  # wait and retry

    if not good_hail:  # couldn't hail inside, flash led and exit
        print("couldn't hail inside box, retrying")
        lora_rx.blink(4)
        return last_good_tx

    # if here, got inside box

    # so send data
    good_sends = []
    good_sends.append(send_w_ack(f"Scale RAW: {scale_avg.avg}"))
    good_sends.append(send_w_ack(f"Temp F: {c_to_f(temp.temperature)}"))
    good_sends.append(send_w_ack(f"Humidity: {temp.relative_humidity}"))
    good_sends.append(send_w_ack(f"CPU T F: {c_to_f(microcontroller.cpu.temperature}"))

    send_w_ack("data done")

    if all(
        good_sends
    ):  # if all sends were good, update last_good_tx and reset scale avg
        scale_avg.reset()
        last_good_tx = time.time()
    else:  # missed a send
        lora_tx.blink(4)

    return last_good_tx


# program mainloop

last_good_tx = time.time() - DATA_SEND_INTERVAL

while True:
    # update scale avg
    scale_val = scale.read()
    if scale_val > -500000:  # only update if reasonable
        print(f"update average: {scale_val}")
        scale_avg.update(scale_val)
        print(f"new avg: {scale_avg.avg}")
    else:
        print(f"unreasonable reading: {scale_val}")

    print(f"time since last tx: {(time.time() - last_good_tx)}")
    # try to tx data
    if (time.time() - last_good_tx) > DATA_SEND_INTERVAL:
        print("attempting data tx")
        last_good_tx = send_data()

    print("loop wait")
    time.sleep(AVERAGE_UPDATE_INTERVAL)  # don't "flood" average
