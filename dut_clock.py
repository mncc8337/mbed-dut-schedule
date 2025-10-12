import sys
import select
import helper
import time
import json
import network
import ntptime
from machine import SPI, PWM
from machine import TouchPad
import _thread
import neopixel

from scraper import Scraper
from ST7735 import TFT
from sysfont import sysfont
import iconfont
import vietnamese

import asyncio
import aioble
import bluetooth


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
    def __init__(
        self,
        spi_id,
        rst_pin,
        dc_pin,
        cs_pin,
        blk_pin,
        rgb_led_pin,
        touch_increase_pin,
        touch_decrease_pin,
        touch_threshold,
        ble_service_uuid,
        ble_led_uuid,
        adv_interval_ms,
        rtc,
    ):
        self.spi = SPI(spi_id, baudrate=20000000)

        # init screen
        self.tft = TFT(self.spi, dc_pin, rst_pin, cs_pin)
        self.tft.initg()
        self.tft.rgb(True)
        self.tft.rotation(1)

        # setup screen led pwm
        self.led_pwm = PWM(blk_pin, freq=5000, duty_u16=0)
        self.screen_brightness = 100
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
        self.wifi_active()

        # sync time
        self.rtc = rtc
        while True:
            try:
                self.sync_rtc(7)
                break
            except Exception as e:
                print(f"failed to sync time due to {e}, retrying", log_type="ERROR")
                time.sleep_ms(100)
        print("time synced")

        self.neopixel = neopixel.NeoPixel(rgb_led_pin, 1)
        print("rgb led initialized")

        self.touch1 = TouchPad(touch_increase_pin)
        self.touch2 = TouchPad(touch_decrease_pin)
        self.touch_threshold = touch_threshold
        print("touch sensor initialized")

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

        # turn off wifi to save power
        self.wlan.active(False)

        # bluetooth stuffs

        # register GATT server, the service and characteristics
        self.adv_interval_ms = adv_interval_ms
        self.ble_service_uuid = bluetooth.UUID(ble_service_uuid)
        self.ble_service = aioble.Service(self.ble_service_uuid)
        self.led_characteristic = aioble.Characteristic(
            self.ble_service,
            bluetooth.UUID(ble_led_uuid),
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
        self.bluetooth_paired = False

        # start the control thread
        _thread.start_new_thread(self.second_thread, ())
        print("control thread started")

    def set_backlight_output(self, duty_cycle):
        if type(duty_cycle) is str:
            sign = duty_cycle[0]
            delta = int(duty_cycle[1:])
            if sign == '+':
                self.screen_brightness += delta
            elif sign == '-':
                self.screen_brightness -= delta
        elif type(duty_cycle) is int:
            self.screen_brightness = duty_cycle
        self.screen_brightness = max(0, min(100, self.screen_brightness))
        self.led_pwm.duty_u16(int(self.screen_brightness/100 * (2 << 15 - 1)))

    def wifi_active(self):
        self.wlan.active(True)
        self.wlan.connect(
            self.privates["ssid"],
            self.privates["ssid_password"]
        )
        while not self.wlan.isconnected():
            time.sleep_ms(100)
        print("connected to AP", self.privates["ssid"])

    def wifi_deactive(self):
        self.wlan.active(False)

    def sync_rtc(self, tz_offset_hours):
        ntptime.settime()

        year, month, day, weekday, hour, minute, second, _ = self.rtc.datetime()

        # apply offset
        t = time.mktime((year, month, day, hour, minute, second, 0, 0))
        t += tz_offset_hours * 3600  # adjust for timezone

        # convert back to datetime tuple and update RTC
        tm = time.localtime(t)
        self.rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))

    def set_led_color(self, color):
        self.neopixel[0] = color
        self.neopixel.write()

    def calculate_current_week(self):
        current_time = helper.get_time()
        self.current_week = int(
            (current_time - self.privates["starting_date_ts"]) // 604800
        ) + self.privates["starting_week"] - 1

    async def command_handler(self, data):
        if data[0] == "led":
            self.set_led_color([int(v) for v in data[1].split(",")])
        elif data[0] == "backlight":
            self.set_backlight_output(int(data[1]))
        elif data[0] == "ble":
            if data[1] == "on":
                self.bluetooth_start()
            elif data[1] == "off":
                self.bluetooth_stop()
            elif data[1] == "toggle":
                self.bluetooth_toggle()
            else:
                print("unknown option", log_type="ERROR")
            self.draw_bluetooth_icon()
        elif data[0] == "watch":
            duration = 5
            if len(data) > 2:
                duration = int(data[2])

            if data[1] == "touch":
                while duration > 0:
                    print(self.touch1.read(), self.touch2.read(), not_log=True)
                    await asyncio.sleep(1)
                    duration -= 1
            elif data[1] == "backlight":
                while duration > 0:
                    print(self.screen_brightness, not_log=True)
                    await asyncio.sleep(1)
                    duration -= 1
            else:
                print("unknown option", log_type="ERROR")
        else:
            print("unknown command", log_type="ERROR")

    async def bluetooth_peripheral_task(self):
        while self.bluetooth_on:
            try:
                async with await aioble.advertise(
                    self.adv_interval_ms,
                    name="dut clock",
                    services=[self.ble_service_uuid],
                ) as connection:
                    print("connection from", connection.device)
                    self.bluetooth_paired = True
                    self.draw_bluetooth_paired_icon()
                    await connection.disconnected()
                    self.bluetooth_paired = False
                    self.draw_bluetooth_paired_icon()
                    print("bluetooth device disconnected")
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
                    connection, data = await self.led_characteristic.written()
                except asyncio.TimeoutError:
                    continue
                print("got ble data from", connection, ":", data)
                data = helper.decode_data(data)
                data = data.split(" ")
                await self.command_handler(data)
            except asyncio.CancelledError:
                print("Peripheral task cancelled")
            except Exception as e:
                print("Error in peripheral_task:", e)
            finally:
                await asyncio.sleep_ms(100)

    def bluetooth_start(self):
        self.bluetooth_on = True

    def bluetooth_stop(self):
        self.bluetooth_on = False
        self.bluetooth_paired = False

    def bluetooth_toggle(self):
        self.bluetooth_on = not self.bluetooth_on
        if not self.bluetooth_on:
            self.bluetooth_paired = False

    async def input_handler_task(self):
        while True:
            v1 = self.touch1.read()
            v2 = self.touch2.read()

            if v1 > self.touch_threshold and v2 > self.touch_threshold:
                self.bluetooth_toggle()
                self.draw_bluetooth_icon()
                await asyncio.sleep(2)
            elif v1 > self.touch_threshold:
                self.set_backlight_output("+1")
            elif v2 > self.touch_threshold:
                self.set_backlight_output("-1")

            await asyncio.sleep_ms(10)

    async def serial_wait_for_command(self):
        print("serial command task started, you can now send commands")

        poll = select.poll()
        poll.register(sys.stdin, select.POLLIN)
        buffer = ""
        while True:
            await asyncio.sleep_ms(10)

            res = poll.poll(0)
            if not res:
                continue

            data = sys.stdin.read(1)

            if data not in ['\n', '\r']:
                if data not in ['\b', chr(127)]:
                    buffer += data
                elif len(buffer) > 1:
                    buffer = buffer[:-1]
            else:
                data = buffer.strip()
                buffer = ""
                if not data:
                    continue

                print(">>>", data, not_log=True)
                await self.command_handler(data.split(" "))

    def second_thread(self):
        # this thread is used to poll inputs
        # and control bluetooth services

        async def main():
            asyncio.create_task(self.input_handler_task())
            asyncio.create_task(self.serial_wait_for_command())
            ble_tasks = []

            while True:
                if self.bluetooth_on and not self.bluetooth_started:
                    self.bluetooth_started = True
                    ble_tasks = [
                        asyncio.create_task(self.bluetooth_peripheral_task()),
                        asyncio.create_task(self.bluetooth_wait_for_command()),
                    ]
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

    def draw_bluetooth_icon(self):
        if self.bluetooth_on:
            self.tft.text(
                (137, 20),
                iconfont.BLUETOOTH,
                TFT.BLUE,
                iconfont.iconfont,
                1
            )
        else:
            self.tft.text(
                (137, 20),
                iconfont.BLUETOOTH,
                TFT.WHITE,
                iconfont.iconfont,
                1
            )

    def draw_bluetooth_paired_icon(self):
        if self.bluetooth_paired:
            self.tft.text(
                (143, 20),
                iconfont.TICK,
                TFT.GREEN,
                iconfont.iconfont,
                1
            )
        else:
            self.tft.text(
                (143, 20),
                iconfont.TICK,
                TFT.WHITE,
                iconfont.iconfont,
                1
            )

    def draw_datetime(self, datetime):
        v = 2
        self.tft.fillrect(
            (2, 2),
            (156, 2 + sysfont["Height"] * 4),
            TFT.WHITE
        )
        self.tft.text(
            (2, v),
            f"{datetime[3]:02d}:{datetime[4]:02d}",
            TFT.BLACK,
            sysfont,
            4
        )
        self.tft.text((109, 3), f"{datetime[2]:02d}", TFT.BLACK, sysfont, 2)
        self.tft.text((137, 3), f"{datetime[1]:02d}", TFT.BLACK, sysfont, 2)
        self.tft.text((109, 20), f"{datetime[0]:04d}", TFT.BLACK, sysfont, 1)
        v += sysfont["Height"] * 4 + 5

    def draw_schedule(self, schedule, decorate_text):
        v = 2 + sysfont["Height"] * 4 + 1
        self.tft.fillrect((0, v), (160, 93), TFT.WHITE)
        if len(schedule) == 0:
            self.tft.text((2, v), "there is nothing to show", TFT.GRAY, sysfont, 1)
            return

        self.tft.text((2, v), decorate_text, TFT.GRAY, sysfont, 1)
        v += sysfont["Height"]
        for sub in schedule:
            class_name = vietnamese.to_ascii(sub["class_name"])
            if len(class_name) > 26:
                class_name = class_name[:23] + "..."

            self.tft.text((2, v), class_name, TFT.BLUE, sysfont, 1, nowrap=True)
            v += sysfont["Height"]
            self.tft.text(
                (2, v),
                vietnamese.to_ascii(sub["room"]),
                TFT.BLACK,
                sysfont,
                1
            )
            self.tft.text(
                (sysfont["Width"] * 5 + 13, v),
                f"{PERIOD[sub["start_period"]][0][0]:02d}:{PERIOD[sub["start_period"]][0][1]:02d} - {PERIOD[sub["end_period"]][1][0]:02d}:{PERIOD[sub["end_period"]][1][1]:02d}",
                TFT.BLACK,
                sysfont,
                1
            )
            v += sysfont["Height"] + 1
