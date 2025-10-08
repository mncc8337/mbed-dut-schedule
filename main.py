import builtins
import helper
import time
import json
import network
import ntptime
from machine import RTC, SPI, PWM
from machine import Pin, TouchPad
import machine
import _thread
import neopixel

from scraper import Scraper
from ST7735 import TFT
from sysfont import sysfont
import vietnamese

import asyncio
import aioble
import bluetooth


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
RST_PIN = Pin(4)
DC_PIN = Pin(5)
CS_PIN = Pin(6)
BLK_PIN = Pin(7, mode=Pin.OUT)

RGB_LED_PIN = Pin(48)

TOUCH_INCREASE_PIN = Pin(8)
TOUCH_DECREASE_PIN = Pin(9)
TOUCH_THRESHOLD = 300000

MAX_TEXT_LEN = 26

BLE_SERVICE_UUID = bluetooth.UUID('cebcf692-9250-4457-86eb-556ab41ca932')
BLE_LED_UUID = bluetooth.UUID('8fff00d0-f1c4-437f-a369-e99227720b6c')
ADV_INTERVAL_MS = 250_000

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
        self.tft = TFT(self.spi, DC_PIN, RST_PIN, CS_PIN)
        self.tft.initg()
        self.tft.rgb(True)
        self.tft.rotation(1)

        # setup screen led pwm
        self.led_pwm = PWM(BLK_PIN, freq=5000, duty_u16=0)
        self.set_backlight_output(100)

        self.tft.fill(TFT.WHITE)
        self.tft.text(
            (1, 1),
            "initializing, please wait ...",
            TFT.BLACK,
            sysfont,
            1
        )

        print("screen initialized")

        # read config
        self.privates = {}
        with open("config.json", "r") as f:
            self.privates = json.load(f)
        print("config loaded")

        # connect to an AP
        self.wlan = network.WLAN()
        self.wlan.active(True)
        self.wlan.connect(
            self.privates["ssid"],
            self.privates["ssid_password"]
        )
        while not self.wlan.isconnected():
            time.sleep_ms(100)
        print("connected to AP", self.privates["ssid"])

        # sync time
        while True:
            try:
                self.sync_rtc(7)
                break
            except Exception as e:
                print(f"failed to sync time due to {e}, retrying", log_type="ERROR")
                time.sleep_ms(100)
        print("time synced")

        self.neopixel = neopixel.NeoPixel(RGB_LED_PIN, 1)
        print("rgb led initialized")

        self.calculate_current_week()
        print("current week", self.current_week)

        print("trying to scraping ...")
        self.scraper = Scraper(
            self.privates["user"],
            self.privates["password"]
        )
        self.scraper.login()
        self.schedule = self.scraper.get_schedule()
        print("schedule retrieved")

        self.wlan.active(False)

        # bluetooth stuffs

        # register GATT server, the service and characteristics
        self.ble_service = aioble.Service(BLE_SERVICE_UUID)
        self.led_characteristic = aioble.Characteristic(
            self.ble_service,
            BLE_LED_UUID,
            read=True,
            write=True,
            notify=True,
            capture=True
        )

        # register service
        aioble.register_services(self.ble_service)
        print("bluetooth services registered")

        self.bluetooth_on = False
        self.bluetooth_started = False

        # start the control thread
        _thread.start_new_thread(self.second_thread, ())
        print("control thread started")

    def set_backlight_output(self, duty_cycle):
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

    def set_led_color(self, color):
        self.neopixel[0] = color
        self.neopixel.write()

    def calculate_current_week(self):
        current_time = helper.get_time()
        self.current_week = int(
            (current_time - self.privates["starting_date_ts"]) // 604800
        ) + self.privates["starting_week"]

    async def bluetooth_peripheral_task(self):
        while self.bluetooth_on:
            try:
                async with await aioble.advertise(
                    ADV_INTERVAL_MS,
                    name="dut clock",
                    services=[BLE_SERVICE_UUID],
                ) as connection:
                    print("connection from", connection.device)
                    await connection.disconnected()
            except asyncio.CancelledError:
                print("peripheral task cancelled")
            except Exception as e:
                print("error in peripheral_task:", e, log_type="ERROR")
            finally:
                await asyncio.sleep_ms(100)

    async def bluetooth_wait_for_command(self):
        while self.bluetooth_on:
            try:
                try:
                    # wait for data for 5 secs
                    connection, data = await asyncio.wait_for(
                        self.led_characteristic.written(),
                        5
                    )
                except asyncio.TimeoutError:
                    continue
                print("got data from", connection, ":", data)
                data = helper.decode_data(data)
                data = data.split(" ")
                if data[0] == "led":
                    self.set_led_color([int(v) for v in data[1].split(",")])
                elif data[0] == "backlight":
                    self.set_backlight_output(int(data[1]))
                else:
                    print("unknown command", log_type="ERROR")
            except asyncio.CancelledError:
                print("Peripheral task cancelled")
            except Exception as e:
                print("Error in peripheral_task:", e)
            finally:
                await asyncio.sleep_ms(100)

    def second_thread(self):
        # this thread is used to poll inputs
        # and control bluetooth services

        async def backlight():
            touch1 = TouchPad(TOUCH_INCREASE_PIN)
            touch2 = TouchPad(TOUCH_DECREASE_PIN)
            screen_brightness = 100
            while True:
                v1 = touch1.read()
                v2 = touch2.read()
                if v1 > TOUCH_THRESHOLD and v2 > TOUCH_THRESHOLD:
                    self.bluetooth_on = not self.bluetooth_on
                    await asyncio.sleep(5)
                elif v1 > TOUCH_THRESHOLD:
                    screen_brightness += 1
                elif v2 > TOUCH_THRESHOLD:
                    screen_brightness -= 1

                if screen_brightness > 100:
                    screen_brightness = 100
                if screen_brightness < 2:
                    screen_brightness = 2
                self.set_backlight_output(screen_brightness)
                await asyncio.sleep_ms(10)

        async def main():
            asyncio.create_task(backlight())
            ble_tasks = []
            while True:
                if self.bluetooth_on and not self.bluetooth_started:
                    self.bluetooth_started = True
                    t1 = asyncio.create_task(app.bluetooth_peripheral_task())
                    t2 = asyncio.create_task(app.bluetooth_wait_for_command())
                    ble_tasks = [t1, t2]
                    print("bluetooth started")
                if not self.bluetooth_on and self.bluetooth_started:
                    for t in ble_tasks:
                        t.cancel()
                        ble_tasks.remove(t)
                    await asyncio.sleep(0)
                    self.bluetooth_started = False
                    print("bluetooth stopped")
                await asyncio.sleep_ms(100)

        asyncio.run(main())

    def get_schedule(self, week=None, weekday=None):
        available = []

        if week is None:
            week = self.current_week
        if weekday is None:
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
today_schedule = app.get_schedule()
decorate_text = "Today"
tft = app.tft


while True:
    datetime = time.localtime()
    schedule_weekday = datetime[6]
    schedule_week = app.current_week
    update_schedule_flag = False

    if datetime[2] != prev_day:
        app.calculate_current_week()
        prev_day = datetime[2]
        decorate_text = "Today"
        update_schedule_flag = True

    if decorate_text == "Today":
        # get next day's schedule if today schedule is done
        last_class = today_schedule[-1]
        last_class_end_period = PERIOD[last_class["end_period"]]
        year, month, day, _, _, _, _, _ = datetime
        t = time.mktime((
            year,
            month,
            day,
            last_class_end_period[1][0],
            last_class_end_period[1][1],
            0,
            0,
            0
        ))
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
            class_name = vietnamese.to_ascii(sub["class_name"])
            if len(class_name) > 26:
                class_name = class_name[:23] + "..."

            tft.text((2, v), class_name, TFT.BLUE, sysfont, 1, nowrap=True)
            v += sysfont["Height"]
            tft.text(
                (2, v),
                vietnamese.to_ascii(sub["room"]),
                TFT.BLACK,
                sysfont,
                1
            )
            tft.text(
                (sysfont["Width"] * 5 + 7, v),
                f"{PERIOD[sub["start_period"]][0][0]:02d}:{PERIOD[sub["start_period"]][0][1]:02d} - {PERIOD[sub["end_period"]][1][0]:02d}:{PERIOD[sub["end_period"]][1][1]:02d}",
                TFT.BLACK,
                sysfont,
                1
            )
            v += sysfont["Height"] + 1

    v = 2
    tft.fillrect((2, 2), (
        sysfont["Width"] * 4 * 5 + 4,
        2 + sysfont["Height"] * 4
    ), TFT.WHITE)
    tft.text(
        (2, v),
        f"{datetime[3]:02d}:{datetime[4]:02d}",
        TFT.BLACK,
        sysfont,
        4
    )
    tft.text((109, 3), f"{datetime[2]:02d}", TFT.BLACK, sysfont, 2)
    tft.text((137, 3), f"{datetime[1]:02d}", TFT.BLACK, sysfont, 2)
    tft.text((109, 20), f"{datetime[0]:04d}", TFT.BLACK, sysfont, 1)
    v += sysfont["Height"] * 4 + 5

    time.sleep(30)
