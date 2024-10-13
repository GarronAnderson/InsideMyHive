# bee box monitor i
# AIO transmit v1.0

# import everything

import os
import time
import adafruit_logging as logging

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

from lcd import CursorMode

import gc

logger = logging.getLogger('test')

logger.setLevel(logging.DEBUG)

logger.info("have imports")

# === USER INPUT ===

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

feed_keys = {
    "Battery %": batt_feed,  # for decoding when we rx data
    "Scale RAW": scale_feed,
    "Temp F": temp_feed,
    "Relative Humidity": hum_feed,
}

logger.info("got feeds")
lcd.clear()
lcd.print("got feeds")

def grab_datas():
    """
    Recieve a data update from the outside unit.
    Returns [list of data], bool of successful RX
    """
    lcd.set_cursor_pos(0,0)
    lcd.print("                ")
    lcd.set_cursor_pos(0,0)
    lcd.print("RXing data")

    logger.info("RXing data")
    datas = []
    data = ""
    rx_time = time.time()

    while (data != "data done") and ((time.time() - rx_time) < 10):
        data = lora.receive(timeout=10)
        logger.debug(f'LoRa raw: {data}')
        if data:
            try:
                data = data.decode()
            except UnicodeError:
                logger.warning(f'got bad data: {data}')
                continue # throw out this iteration, keep looping
            
            logger.debug(f'LoRa decoded: {data}')
            rx_time = time.time()
            datas.append(data)
            lora.send(data)

    lora.send("data done")  # Won't hurt to send this, even on a timeout fail.

    return datas[:-1], ((time.time() - rx_time) < 10)


def aio_tx(datas):
    """
    TX data to AIO.
    Needs a list of data.
    """

    logger.info("TXing to Adafruit IO")
    lcd.set_cursor_pos(0,0)
    lcd.print("                ")
    lcd.set_cursor_pos(0,0)
    lcd.print("TXing to aio")

    for data in datas:
        if ": " in data:
            k, v = data.split(": ")
            feed_key = feed_keys[k]["key"]
            logger.debug(f"Sending data {v} to feed {feed_key}")
            io.send_data(feed_key, float(v))


def get_time():
    """
    Grab a human-readable time string.
    """

    time_request = requests.get(TIME_URL)
    return time_request.text


logger.info(
    f"Mainloop start time from AIO: {get_time()}"
)  # this acts as a test of internet conn

last_good_rx_txt = "N/A"
have_new_data = False

lcd.set_cursor_pos(1,0)
lcd.print("                ")
lcd.set_cursor_pos(1,0)
lcd.print(f"Last RX {last_good_rx_txt}")
        

while True:  # mainloop
    logger.info("run rx cycle")
    
    lcd.set_cursor_pos(0,0)
    lcd.print("                ")
    lcd.set_cursor_pos(0,0)
    lcd.print("rx cycle")


    data = lora.receive(timeout=6)  # allow 2 tx attempts
    logger.debug(f'Lora raw: {data}')
    if data is not None:
        try:
            data = data.decode()
        except UnicodeError:
            logger.warning(f'got bad data: {data}')
            continue # throw out this iteration, keep looping
        logger.debug(f"LoRa decoded: {data}")

    if data == "data ready":  # drop everything else and grab latest update
        lora.send("data ready")
        datas, have_new_data = grab_datas()
        logger.debug(f"Latest datas: {datas}")
        gc.collect()
        last_good_rx_txt = get_time()
        
        if not have_new_data:
            last_good_rx_txt = "RX Timeout"
            
        if have_new_data:
            aio_tx(datas)
            have_new_data = False
            
        lcd.set_cursor_pos(1,0)
        lcd.print("                ")
        lcd.set_cursor_pos(1,0)
        lcd.print(f"Last RX {last_good_rx_txt}")

    logger.info(f"last good rx: {last_good_rx_txt}")
    logger.debug(f"gc mem free: {gc.mem_free()}")
