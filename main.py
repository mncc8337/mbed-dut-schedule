import helper
from scraper import Scraper
import time
import json
import network
import requests
import ntptime 
from machine import RTC, SPI, Pin
from ST7735 import TFT
from sysfont import sysfont


# WARNING:
# please check if machine.SPI(1) is supported
# else the board will just reset constantly
# and you will need to erase flash and install micropython again
# you can check it by running
# ```
# >>> import machine
# >>> machine.SPI(1)
# >>> machine.SPI(2)
# ```
# after a fresh micropython installation
# and choose the one without error/reset
# make sure to use the printed SCK and MOSI pin
SPI_ID = 1

# for these you can use any pin that isn't conflicted with internal stuffs
RST = Pin(4)
DC = Pin(5)
CS = Pin(6)
BLK = Pin(7, mode=Pin.OUT)

# init screen
spi = SPI(SPI_ID, baudrate=20000000)
tft=TFT(spi, DC, RST, CS)
tft.initr()
tft.rgb(True)

# turn on screen's LED
BLK.on()

# test screen
tft.fill(TFT.BLACK);
v = 30
tft.text((0, v), "Hello World!", TFT.RED, sysfont, 1, nowrap=True)
v += sysfont["Height"]
tft.text((0, v), "Hello World!", TFT.YELLOW, sysfont, 2, nowrap=True)
v += sysfont["Height"] * 2
tft.text((0, v), "Hello World!", TFT.GREEN, sysfont, 3, nowrap=True)
v += sysfont["Height"] * 3
tft.text((0, v), str(1234.567), TFT.BLUE, sysfont, 4, nowrap=True)

# read config
privates = {}
with open("config.json", "r") as f:
    privates = json.load(f)

# connect to an AP
wlan = network.WLAN()
wlan.active(True)
wlan.connect(privates["ssid"], privates["ssid_password"])
while not wlan.isconnected():
    time.sleep_ms(100)
print("connected to WiFi")

print("updating RTC")
ntptime.settime()
rtc = RTC()
print("RTC updated:", rtc.datetime())

current_time = helper.get_time()
print("current time", current_time)
# calculate current week
current_week = int((current_time - privates["starting_date_ts"]) // 604800) + privates["starting_week"]
print("current week:", current_week)

scraper = Scraper(privates["user"], privates["password"])
scraper.login()
scraper.get_schedule(True)
