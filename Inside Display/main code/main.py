# bee box monitor inside with eink

# import everything

import os
import time

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

import adafruit_uc8151d
from fourwire import FourWire
import terminalio

from helpers import Gauge, DisplayBox, BatteryIndicator

import gc

print("have imports")

# === USER INPUT ===

LORA_FREQ = 915.0
TIMEZONE = "America/Chicago"

# === END USER INPUT ===

# connect to WiFi

ssid, password = os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")

wifi.radio.connect(ssid, password)

print("wifi conn")

aio_un, aio_key = os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_un, aio_key, requests)

TIME_URL = f"https://io.adafruit.com/api/v2/{aio_un}/integrations/time/strftime?x-aio-key={aio_key}&tz={TIMEZONE}"
TIME_FORMAT = "&fmt=%25I%3A%25M+%25P"
TIME_URL += TIME_FORMAT

print("connected to io")

# this releases the SPI, so it has to go here (solves reboot problems)
displayio.release_displays()

# LoRa
spi = busio.SPI(board.GP18, board.GP19, board.GP16)
rfm_cs = digitalio.DigitalInOut(board.GP21)
rfm_reset = digitalio.DigitalInOut(board.GP20)

lora = RFM9x(spi, rfm_cs, rfm_reset, LORA_FREQ)

print("got lora")

# display
epd_cs = board.GP12
epd_dc = board.GP13

# Create the displayio connection to the display pins
display_bus = FourWire(spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000)
time.sleep(1)  # let bus init

# Create the display object - the third color is red (0xff0000)
display = adafruit_uc8151d.UC8151D(
    display_bus,
    width=296,
    height=128,
    rotation=270,
    highlight_color=0xFF0000,
)

# display widgets

weight_gauge = Gauge(x=50, y=80)
hum_gauge = Gauge(x=148, y=80)
temp_gauge = Gauge(x=246, y=80)

batt_ind = BatteryIndicator(x=205, y=6, scale=4)

data_stale_ind = DisplayBox(x=5, y=5)

last_rx_box = DisplayBox(x=90, y=5, width=110)
last_rx_time = "no rx yet"

display_elems = [
    weight_gauge,
    hum_gauge,
    temp_gauge,
    batt_ind,
    data_stale_ind,
    last_rx_box,
]

print("grabbing feeds")


def get_feed(feed_id):
    try:
        feed = io.get_feed(feed_id)
    except AdafruitIO_RequestError:
        # if no feed exists, create one
        feed = io.create_new_feed(feed_id)

    return feed


scale_feed = get_feed("hm-scale")
batt_feed = get_feed("hm-batt")
hive_feed = get_feed("hm-temp")
hive_feed = get_feed("hm-humid")

feed_keys = {
    "Battery %": batt_feed,
    "Scale RAW": scale_feed,
    "Temp F": hive_feed,
    "Relative Humidity": hive_feed,
}

print("got feeds")


def render_display():
    gc.collect()
    print(f"GC Free mem: {gc.mem_free()}")

    g = displayio.Group()
    gc.collect()

    print(f"group free mem: {gc.mem_free()}")
    # Set everything white
    white_bitmap = displayio.Bitmap(display.width, display.height, 1)

    print(f"bitmap Free mem: {gc.mem_free()}")

    # Create a two color palette
    white = displayio.Palette(1)
    white[0] = 0xFFFFFF
    white_tilegrid = displayio.TileGrid(white_bitmap, pixel_shader=white)

    # Add the TileGrid to the Group
    g.append(white_tilegrid)
    del white_tilegrid
    del white_bitmap
    gc.collect()

    print(f"GC Free mem after collect: {gc.mem_free()}")

    for elem in display_elems:
        rendered = elem.render()
        g.append(rendered)
        del rendered
        gc.collect()

    display.root_group = g
    display.refresh()

    return time.time()


def parse_to_display_elems(datas):
    for data in datas:
        k, v = data.split(": ")
        v = float(v)
        if k == "Battery %":
            batt_ind.update(v)
        elif k == "Scale RAW":
            weight_gauge.update(v)
        elif k == "Temp F":
            temp_gauge.update(v)
        elif k == "Relative Humidity":
            hum_gauge.update(v)


def update_indicator_boxes(last_good_rx, last_good_rx_txt):
    if (time.time() - last_good_rx) >= 6:
        data_stale_ind.alert("Data Stale")
    else:
        data_stale_ind.display("Data Good")

    last_rx_box.display(last_good_rx_txt)


def grab_datas():
    print("attempting data rx")
    datas = []
    data = ""
    rx_time = time.time()

    while (data != "data done") and ((time.time() - rx_time) < 10):
        data = lora.receive(timeout=10)
        if data:
            data = data.decode()
            print(data)
            rx_time = time.time()
            datas.append(data)
            lora.send(data)

    lora.send("data done")  # Won't hurt to send this, even on a timeout fail.

    return datas[:-1], ((time.time() - rx_time) < 10)


def aio_tx(datas):
    print("running aio tx")
    for data in datas:
        k, v = data.split(": ")
        feed_key = feed_keys[k]["key"]
        print(f"Sending data {v} to feed {feed_key}")
        io.send_data(feed_key, float(v))


def get_time():
    time_request = requests.get(TIME_URL)
    return time_request.text


print(f"Mainloop start time from AIO: {get_time()}")

last_good_refresh = 0  # force display refresh on start
last_good_rx = 0
last_good_rx_txt = "N/A"
have_new_data = False

gc.collect()

while True:  # mainloop
    print("run rx cycle")

    data = lora.receive(timeout=6)  # allow 2 tx attempts
    if data:
        data = data.decode()
    if data:
        print(f"LoRa got: {data}")

    if data == "data ready":  # drop everything else and grab latest update
        print("grabbing update")
        lora.send("data ready")
        datas, have_new_data = grab_datas()
        print(f"Latest datas: {datas}")
        last_rx_time = get_time()
        if not have_new_data:
            last_good_rx_txt = "RX Timeout"

        if have_new_data:
            aio_tx(datas)

    # do we need to refresh display?
    time_since_refresh = time.time() - last_good_refresh
    if (time_since_refresh >= 6 * 60) or have_new_data:
        if have_new_data:
            parse_to_display_elems(datas)
        update_indicator_boxes(last_good_rx, last_good_rx_txt)
        gc.collect()
        print(f"GC Free mem: {gc.mem_free()}")
        render_display()
        have_new_data = False
