# bee box monitor inside code
# AIO transmit only v1.2

# import everything

import os
import time
import gc

import adafruit_logging as logging
import supervisor

import board
import busio
import digitalio
import displayio

import ssl
import wifi
import socketpool
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

from adafruit_rfm9x import RFM9x

from lcd import LCD
from i2c_pcf8574_interface import I2CPCF8574Interface

logger = logging.getLogger("test")

logger.setLevel(logging.DEBUG)

logger.info("have imports")

# === USER INPUT ===

LCD_DEBUG = True

LORA_FREQ = 915.0  # MHz
TIMEZONE = "America/Chicago"  # see https://worldtimeapi.org/api/timezone/
RX_EXPECTED_TIMING = 6  # minutes

# === END USER INPUT ===

# connect to WiFi

ssid, password = os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")

wifi.radio.connect(ssid, password)

logger.info("got wifi conn")

# and AIO

aio_un, aio_key = os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_un, aio_key, requests)

TIME_URL = f"https://io.adafruit.com/api/v2/{aio_un}/integrations/time/strftime?x-aio-key={aio_key}&tz={TIMEZONE}"  # to pull human-readable time from AIO
TIME_FORMAT = "&fmt=%25I%3A%25M+%25P"
TIME_URL += TIME_FORMAT

logger.info("connected to io")

# this releases the SPI, so it has to go here (solves reboot problems)
displayio.release_displays()

# LoRa
spi = busio.SPI(board.GP18, board.GP19, board.GP16)
rfm_cs = digitalio.DigitalInOut(board.GP21)
rfm_reset = digitalio.DigitalInOut(board.GP20)

lora = RFM9x(spi, rfm_cs, rfm_reset, LORA_FREQ)
lora.tx_power = 23
lora.spreading_factor = 11

# display
i2c = busio.I2C(board.GP1, board.GP0)
lcd = LCD(I2CPCF8574Interface(i2c, 0x27), num_rows=2, num_cols=16)
lcd.clear()
lcd.print("getting feeds")

logger.info("got lora")

logger.info("grabbing feeds")


def get_feed(feed_id):
    """
    Grab a feed off of Adafruit IO.
    Needs a feed id (no underscores)
    """

    try:
        feed = io.get_feed(feed_id)
    except AdafruitIO_RequestError:
        # if no feed exists, create one
        feed = io.create_new_feed(feed_id)

    return feed


# grab the feeds

scale_feed = get_feed("hm-scale")
batt_feed = get_feed("hm-batt")
temp_feed = get_feed("hm-temp")
hum_feed = get_feed("hm-humid")
chg_feed = get_feed("hm-chg-rate")
# ttd_feed = get_feed("hm-time-to-discharge")
cpu_feed = get_feed("hm-cpu-temp")

feed_keys = {
    "Battery %": batt_feed,  # for decoding when we rx data
    "Scale RAW": scale_feed,
    "Temp F": temp_feed,
    "Humidity": hum_feed,
    "Batt Chg Rate": chg_feed,
    "CPU T F": cpu_feed,
}

logger.info("got feeds")
lcd.clear()
lcd.print("got feeds")


def grab_datas():
    """
    Recieve a data update from the outside unit.
    Returns [list of data], bool of successful RX
    """
    lcd.set_cursor_pos(0, 0)
    lcd.print("                ")
    lcd.set_cursor_pos(0, 0)
    lcd.print("RXing data")

    logger.info("RXing data")
    datas = []
    data = ""
    rx_time = time.time()

    while (data != "data done") and ((time.time() - rx_time) < 10):
        data = lora.receive(timeout=10)
        if data:
            try:
                data = data.decode()
            except UnicodeError:
                logger.warning(f"got bad data: {data}")
                continue  # throw out this iteration, keep looping
            logger.debug(f"LoRa decoded: {data}")

            if LCD_DEBUG and data is not None:
                lcd.set_cursor_pos(1, 0)
                lcd.print("                ")
                lcd.set_cursor_pos(1, 0)
                lcd.print(data[:16])

            rx_time = time.time()
            datas.append(data)
            time.sleep(0.1)
            logger.debug(f"LoRa sending ack")
            lora.send(data)

    lora.send("data done")  # Won't hurt to send this, even on a timeout fail.

    return datas[:-1], ((time.time() - rx_time) < 10)


def aio_tx(datas):
    """
    TX data to AIO.
    Needs a list of data.
    """

    logger.info("TXing to Adafruit IO")
    lcd.set_cursor_pos(0, 0)
    lcd.print("                ")
    lcd.set_cursor_pos(0, 0)
    lcd.print("TXing to aio")

    batt_percent = 0
    chg_rate = 0

    for data in datas:
        if ": " in data:
            k, v = data.split(": ")
            feed_key = feed_keys[k]["key"]
            logger.debug(f"Sending data {v} to feed {feed_key}")
            io.send_data(feed_key, float(v))
            if k == "Battery %":
                batt_percent = float(v)
            if k == "Batt Chg Rate":
                chg_rate = float(v)

    if chg_rate > 0:
        ttd = (100 - batt_percent) / chg_rate
    elif chg_rate == 0:
        ttd = 0
    else:
        ttd = batt_percent / chg_rate

    logger.debug(f"Sending data {ttd} to feed hm-ttd")
    # io.send_data(ttd_feed["key"], ttd)  # as I have no battery monitor, this is useless


def get_time():
    """
    Grab a human-readable time string.
    """

    logger.debug("attempting to get time from AIO")
    time_request = requests.get(TIME_URL)
    return time_request.text


logger.info(
    f"Mainloop start time from AIO: {get_time()}"
)  # this acts as a test of internet conn

last_good_rx_txt = "N/A"
have_new_data = False

lcd.set_cursor_pos(1, 0)
lcd.print("                ")
lcd.set_cursor_pos(1, 0)
lcd.print(f"Last RX {last_good_rx_txt}")


def rotate_left(lst):
    return lst[1:] + lst[:1]


rx_cycle_str = "rx cycle    rx cycle    "

while True:  # mainloop
    try:
        logger.info("run rx cycle")

        lcd.set_cursor_pos(0, 0)
        rx_cycle_str = rotate_left(rx_cycle_str)
        lcd.print(rx_cycle_str[:16])

        data = lora.receive(timeout=0.7)
        if data is not None:
            try:
                data = data.decode()
            except UnicodeError:
                logger.warning(f"got bad data: {data}")
                continue  # throw out this iteration, keep looping
            logger.debug(f"LoRa decoded: {data}")

        if data == "data ready":  # drop everything else and grab latest update
            time.sleep(0.1)
            logger.debug("sending ack")
            lora.send("data ready")
            datas, have_new_data = grab_datas()
            logger.debug(f"Latest datas: {datas}")
            gc.collect()
            last_good_rx_txt = get_time()

            if not have_new_data:
                last_good_rx_txt = "Timedout"

            if have_new_data:
                aio_tx(datas)
                have_new_data = False

            lcd.set_cursor_pos(1, 0)
            lcd.print("                ")
            lcd.set_cursor_pos(1, 0)
            lcd.print(f"Last RX {last_good_rx_txt}")

        logger.info(f"last good rx: {last_good_rx_txt}")
        logger.debug(f"gc mem free: {gc.mem_free()}")

    except (MemoryError, OSError):  # catch Adafruit IO crashes with socket issues
        if LCD_DEBUG:
            lcd.clear()
            lcd.print("AIO Error\nReloading in 2s")

        logger.warning("Adafruit IO Error, reloading in 2 seconds")
        time.sleep(2)

        if LCD_DEBUG:
            lcd.clear()
            lcd.print("MemoryError\nReloading now")

        supervisor.reload()
