# import libraries
# settings in settings.toml

import os
import time
import ssl
import wifi
import socketpool
import board
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_rfm9x import RFM9x
import busio
import digitalio
import adafruit_uc8151d
from fourwire import FourWire

# connect to wifi and aio

wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

aio_username = os.getenv('ADAFRUIT_AIO_USERNAME')
aio_key = os.getenv('ADAFRUIT_AIO_KEY')

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)
print("connected to io")

# LoRa

spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)
rfm_cs = digitalio.DigitalInOut(board.GP21)
rfm_reset = digitalio.DigitalInOut(board.GP20)

lora = RFM9x(spi, rfm_cs, rfm_reset, 915.0)

# display
displayio.release_displays()

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

def get_feed(feed_id):
    try:
        feed = io.get_feed(feed_id)
    except AdafruitIO_RequestError:
    # if no feed exists, create one
        feed = io.create_new_feed(feed_id)

    return feed

scale_val = get_feed("hm-scale")
batt_percent = get_feed("hm-batt")
hive_temp = get_feed("hm-temp")
hive_humidity = get_feed("hm-humid")

feed_keys = {"Battery %": batt_percent,
            "Scale RAW": scale_val,
            "Temp F": hive_temp,
            "Relative Humidity": hive_humidity}

print("got feeds")

while True:
    # if at top of loop, ready for rx
    print('set display idle')
    
    msg = ''
    while msg != "data ready":
        msg = lora.receive(timeout=5)
        if msg:
            msg = msg.decode()
        print(f'Got: <{msg}>')
        
    lora.send('data ready')
    
    data = ''
    datas = []
    while data != 'data done':
        # get data
        data = ''
        while not data:
            data = lora.receive(timeout=5)
            data = data.decode()
            print(f'Got: <{data}>')
            
        # and add to list
        datas.append(data)
        lora.send(data)
        
    lora.send('data done')
    
    # start aio tx
    print('starting aio tx')
    
    # parse datas
    datas = datas[:-1] 
    for data in datas:
        k, v  = data.split(": ")
        feed_key = feed_keys[k]["key"]
        print(f'Sending data {v} to feed {feed_key}')
        io.send_data(feed_key, float(v))
        
        