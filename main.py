import builtins
import helper
from scraper import Scraper
import time
import json
import network
import requests
import ntptime 
from machine import RTC, SPI, PWM
from machine import Pin
from ST7735 import TFT
from sysfont import sysfont
import vietnamese


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

rtc = RTC()
def log(*args, log_type="INFO", not_log=False, **kwargs):
    if not_log:
        builtins.print(*args, **kwargs)
        return

    dt = rtc.datetime()
    timestamp = f"{dt[0]:04d}-{dt[1]:02d}-{dt[2]:02d} {dt[4]:02d}:{dt[5]:02d}:{dt[6]:02d}"
    builtins.print(f"[{timestamp}] [{log_type}]", *args, **kwargs)
builtins.print = log

PERIOD = [
    # start    end
    ((0, 0),   (0, 0)),
    ((7, 0),   (7, 50)),
    ((8, 0),   (8, 50)),
    ((9, 0),   (9, 50)),
    ((10, 0),  (10, 50)),
    ((11, 0),  (11, 50)),
    ((12, 30), (13, 20)),
    ((13, 30), (14, 20)),
    ((14, 30), (15, 20)),
    ((15, 30), (16, 20)),
    ((16, 30), (17, 20)),
    ((17, 30), (18, 15)),
    ((18, 15), (19, 0)),
    ((19, 10), (19, 55)),
    ((19, 55), (20, 40))
]

WEEKDAY = [
    "Thứ 2",
    "Thứ 3",
    "Thứ 4",
    "Thứ 5",
    "Thứ 6",
    "Thứ 7",
    "Chủ Nhật"
]


class App:

    def __init__(self):
        self.spi = SPI(SPI_ID, baudrate=20000000)

        # init screen
        self.tft = TFT(self.spi, DC, RST, CS)
        self.tft.initg()
        self.tft.rgb(True)
        self.tft.rotation(1)

        # setup screen led pwm
        self.led_pwm = PWM(BLK, freq=5000, duty_u16=0)
        self.set_led_output(100)

        self.tft.fill(TFT.WHITE)
        self.tft.text((1, 1), "initializing, please wait ...", TFT.BLACK, sysfont, 1)

        print("screen initialized")

        # read config
        self.privates = {}
        with open("config.json", "r") as f:
            self.privates = json.load(f)
        print("config loaded")

        # connect to an AP
        self.wlan = network.WLAN()
        self.wlan.active(True)
        self.wlan.connect(self.privates["ssid"], self.privates["ssid_password"])
        while not self.wlan.isconnected():
            time.sleep_ms(100)
        print("connected to AP", self.privates["ssid"])

        # sync time
        while True:
            try:
                self.sync_rtc(7)
                break
            except:
                print("failed to sync time, retrying")
                time.sleep_ms(100)
        print("time synced")

        self.calculate_current_week()
        print("current week", self.current_week)

        print("trying to scraping ...")
        self.scraper = Scraper(self.privates["user"], self.privates["password"])
        self.scraper.login()
        self.schedule = self.scraper.get_schedule()
        print("schedule retrieved")

        self.wlan.active(False)

    def set_led_output(self, duty_cycle):
        self.led_pwm.duty_u16(int(duty_cycle/100 * (2 << 15 - 1)))

    def sync_rtc(self, tz_offset_hours):
        ntptime.settime()

        year, month, day, weekday, hour, minute, second, _ = rtc.datetime()

        # apply offset
        t = time.mktime((year, month, day, hour, minute, second, 0, 0))
        t += tz_offset_hours * 3600  # adjust for timezone

        # convert back to datetime tuple and update RTC
        tm = time.localtime(t)
        rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))

    def calculate_current_week(self):
        current_time = helper.get_time()
        self.current_week = int((current_time - self.privates["starting_date_ts"]) // 604800) + self.privates["starting_week"]

    def get_schedule(self, week=None, weekday=None):
        available = []

        if week == None:
            week = self.current_week
        if weekday == None:
            weekday = time.localtime()[6]

        for sub in self.schedule:
            # compare week
            week_flag = False
            for w in sub["weeks"]:
                week_flag = week >= w[0] and week <= w[1]
                if week_flag:
                    break
            if not week_flag:
                continue

            # compare week day
            if WEEKDAY[weekday] == sub["weekday"]:
                available.append(sub)

        # sort in period order
        def sort_func(v):
            return v["start_period"]
        available.sort(key=sort_func)
        return available


app = App()
prev_day = -1
today_schedule = None
tft = app.tft

# def serial_handler():
#     pass
#
# _thread.start_new_thread(serial_handler, ())

while True:
    datetime = time.localtime()
    schedule_weekday = datetime[6]
    schedule_week = app.current_week
    decorate_text = "Today"
    update_schedule_flag = False

    if datetime[2] != prev_day:
        app.calculate_current_week()
        prev_day = datetime[2]
        update_schedule_flag = True
    else:
        # get next day's schedule if today schedule is done
        last_class = today_schedule[-1]
        last_class_end_period = PERIOD[last_class["end_period"]]
        year, month, day, weekday, _, _, _, _ = datetime
        t = time.mktime((year, month, day, last_class_end_period[1][0], last_class_end_period[1][1], 0, 0, 0))
        if time.time() >= t:
            schedule_weekday += 1
            if schedule_weekday >= 7:
                schedule_weekday = 0
                schedule_week += 1
            decorate_text = "Tomorrow"
            update_schedule_flag = True

    if update_schedule_flag:
        today_schedule = app.get_schedule(schedule_week, schedule_weekday)

        tft.fill(TFT.WHITE)
        v = 2 + sysfont["Height"] * 4 + 1
        tft.text((2, v), decorate_text, TFT.GRAY, sysfont, 1)
        v += sysfont["Height"]
        for sub in today_schedule:
            tft.text((2, v), vietnamese.to_ascii(sub["class_name"]), TFT.BLUE, sysfont, 1, nowrap=True)
            v += sysfont["Height"]
            tft.text((2, v), vietnamese.to_ascii(sub["room"]), TFT.BLACK, sysfont, 1)
            tft.text(
                (sysfont["Width"] * 5 + 7, v),
                f"{PERIOD[sub["start_period"]][0][0]:02d}:{PERIOD[sub["start_period"]][0][1]:02d} - {PERIOD[sub["end_period"]][1][0]:02d}:{PERIOD[sub["end_period"]][1][1]:02d}",
                TFT.BLACK,
                sysfont,
                1
            )
            v += sysfont["Height"] + 1

    v = 2
    tft.fillrect((2, 2), (sysfont["Width"] * 4 * 5 + 4, 2 + sysfont["Height"] * 4), TFT.WHITE)
    tft.text((2, v), f"{datetime[3]:02d}:{datetime[4]:02d}", TFT.BLACK, sysfont, 4)
    tft.text((109, 3), f"{datetime[2]:02d}", TFT.BLACK, sysfont, 2)
    tft.text((137, 3), f"{datetime[1]:02d}", TFT.BLACK, sysfont, 2)
    tft.text((109, 20), f"{datetime[0]:04d}", TFT.BLACK, sysfont, 1)
    v += sysfont["Height"] * 4 + 5


    time.sleep(60)

