# RP2350 FULL CODE

# core libs
import time
import os
import json

# circuitpython libs
import board
import busio
import digitalio
import terminalio
import displayio
import neopixel
import sdcardio
import storage
import adafruit_logging as logging
import adafruit_requests
import supervisor

# wifi
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

# LoRa
from adafruit_rfm9x import RFM9x

import adafruit_uc8151d
from fourwire import FourWire
from helpers import *

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)

logger.info("have imports")

# === USER INPUT ===

LORA_FREQ = 915.0  # MHz
TIMEZONE = "America/Chicago"  # see https://worldtimeapi.org/api/timezone/
RX_EXPECTED_TIMING = 6  # minutes

# === END USER INPUT ===

# this releases the SPI, so it has to go here (solves reboot problems)
displayio.release_displays()

# AirLift
esp32_cs = digitalio.DigitalInOut(board.D13)
esp32_reset = digitalio.DigitalInOut(board.D12)
esp32_ready = digitalio.DigitalInOut(board.D11)

secrets = {
    'ssid' : os.getenv("CIRCUITPY_WIFI_SSID"),
    'password' : os.getenv("CIRCUITPY_WIFI_PASSWORD"),
}

spi = board.SPI()
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

logger.info("have airlift")

aio_un, aio_key = os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY")

# Create an instance of the Adafruit IO HTTP client
io = IO_HTTP(os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY"), wifi)

# LoRa

TIME_URL = f"https://io.adafruit.com/api/v2/{aio_un}/integrations/time/strftime?x-aio-key={aio_key}&tz={TIMEZONE}"  # to pull human-readable time from AIO
TIME_FORMAT = "&fmt=%25I%3A%25M+%25P"
TIME_URL += TIME_FORMAT

logger.info("connected to io")

# SD

sd_cs = board.D5

sdcard = sdcardio.SDCard(spi, sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# LoRa

rfm_cs = digitalio.DigitalInOut(board.D25)
rfm_reset = digitalio.DigitalInOut(board.D24)

lora = RFM9x(spi, rfm_cs, rfm_reset, LORA_FREQ)
lora.tx_power = 23
lora.spreading_factor = 11

symbolDuration = 1000 / ( lora.signal_bandwidth / (1 << lora.spreading_factor) )
if symbolDuration > 16:
    lora.low_datarate_optimize = 1
    logger.debug("low datarate on")
else:
    lora.low_datarate_optimize = 0
    logger.debug("low datarate off")
    
lora.xmit_timeout = 10

logger.debug("got lora")

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
logger.debug("getting feeds")

scale_feed = get_feed("hm-scale")
batt_feed = get_feed("hm-batt")
temp_feed = get_feed("hm-temp")
hum_feed = get_feed("hm-humid")
chg_feed = get_feed("hm-chg-rate")
ttd_feed = get_feed("hm-time-to-discharge")
cpu_feed = get_feed("hm-cpu-temp")
therm_feed = get_feed("hm-thermo")

logger.debug("got feeds")

feed_keys = {
    "Battery %": batt_feed,  # for decoding when we rx data
    "Scale RAW": scale_feed,
    "Temp F": temp_feed,
    "Humidity": hum_feed,
    "Batt Chg Rate": chg_feed,
    "CPU T F": cpu_feed,
    "Thermo T F": therm_feed,
}
    
def grab_datas():
    TIMEOUT = 15
    """
    Recieve a data update from the outside unit.
    Returns [list of data], bool of successful RX
    """

    logger.info("RXing data")
    datas = []
    data = ""
    rx_time = time.time()

    while (data != "data done") and ((time.time() - rx_time) < TIMEOUT):
        data = lora.receive(timeout=TIMEOUT)
        if data:
            try:
                data = data.decode()
            except UnicodeError:
                logger.warning(f"got bad data: {data}")
                continue  # throw out this iteration, keep looping
            logger.debug(f"LoRa decoded: {data}")

            rx_time = time.time()
            datas.append(data)
            time.sleep(0.1)
            logger.debug(f"LoRa sending ack")
            lora.send(data)

    lora.send("data done")  # Won't hurt to send this, even on a timeout fail.

    return datas[:-1], ((time.time() - rx_time) < TIMEOUT)


def aio_tx(datas):
    """
    TX data to AIO.
    Needs a list of data.
    """

    logger.info("TXing to Adafruit IO")

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
    io.send_data(ttd_feed["key"], ttd)
    
def get_time():
    """
    Grab a human-readable time string.
    """

    logger.debug("attempting to get time from AIO")
    time_request = wifi.get(TIME_URL)
    return time_request.text

logger.debug("doing crash recovery")

try:
    with open('/sd/reload.json', "r") as f:
        crashed = json.load(f)
except (OSError, ValueError):
    crashed = {'needs_retransmit': False}

if crashed['needs_retransmit']:
    try:
        aio_tx(crashed['datas'])
    except:
        supervisor.reload()
    last_good_rx_txt = crashed['last_good_rx_txt']
    data = {'needs_retransmit': False}
    with open('/sd/reload.json', 'w') as f:
        json.dump(data, f)
else:
    logger.debug("no recovery needed")
    last_good_rx_txt = "N/A"


logger.info(f"Mainloop start time from AIO: {get_time()}")

last_good_refresh = 0  # force display refresh on start
last_good_rx = 0
have_new_data = False

while True:
    data = lora.receive(timeout=5)
    if data is not None:
        try:
            data = data.decode()
        except UnicodeError:
            logger.warning(f"got bad data: {data}")
            continue  # throw out this iteration, keep looping
        logger.debug(f"LoRa decoded: {data}")

    if data == 'data ready':
        time.sleep(0.1)
        lora.send('data ready')
        datas, have_new_data = grab_datas()
        logger.debug(f'latest datas: {datas}')
    
    if have_new_data:
        try:
            aio_tx(datas)
            have_new_data = False
        except (MemoryError, OSError):
            logger.critical("AIO Error, reloading")
            
            data = {'datas': datas, 'last_good_rx_txt': last_good_rx_txt, 'needs_retransmit': True}
            with open('/sd/reload.json', 'w') as f:
                json.dump(data, f)
            
            supervisor.reload()