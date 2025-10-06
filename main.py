import helper
from scraper import Scraper
import time
import json
import network
import requests
import ntptime 
from machine import RTC

privates = {}
with open("config.json", "r") as f:
    privates = json.load(f)

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
