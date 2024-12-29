import time
import board
import busio
import neopixel
import os

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from digitalio import DigitalInOut

# AirLift FeatherWing
esp32_cs = DigitalInOut(board.D13)
esp32_reset = DigitalInOut(board.D12)
esp32_ready = DigitalInOut(board.D11)

secrets = {
    "ssid": os.getenv("CIRCUITPY_WIFI_SSID"),
    "password": os.getenv("CIRCUITPY_WIFI_PASSWORD"),
}

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Create an instance of the Adafruit IO HTTP client
io = IO_HTTP(os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY"), wifi)


def get_feed(feed_id):
    try:
        feed = io.get_feed(feed_id)
    except AdafruitIO_RequestError:
        # if no feed exists, create one
        feed = io.create_new_feed(feed_id)
    return feed


print("trying to get feed")
test_feed = get_feed("test-feed")
print("got feed")
print(test_feed)

io.send_data(test_feed["key"], 12345)
