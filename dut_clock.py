import sys
import select
import helper
import time
import json
import ntptime
import network
from machine import SPI, PWM, RTC
from machine import TouchPad
import _thread
import neopixel

import scraper
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


class Tab:
    SCHEDULE = 0
    CLASS_NOTICES = 1
    GENENAL_NOTICES = 2
    MAX = 3


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
        touch_tab_change_pin,
        touch_threshold,
        ble_service_uuid,
        ble_led_uuid,
        adv_interval_ms,
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

        self.neopixel = neopixel.NeoPixel(rgb_led_pin, 1)
        print("rgb led initialized")

        self.current_tab = Tab.SCHEDULE
        self.prev_tab = -1

        self.touch1 = TouchPad(touch_increase_pin)
        self.touch2 = TouchPad(touch_decrease_pin)
        self.touch_tab = TouchPad(touch_tab_change_pin)
        self.touch_threshold = touch_threshold
        print("touch sensor initialized")

        # connect to an AP
        self.wlan = network.WLAN()
        self.wifi_active()
        time.sleep(1)

        # sync time
        while True:
            try:
                self.sync_rtc(7)
                break
            except Exception as e:
                print(f"failed to sync time due to error {e}, retrying", log_type="ERROR")
                time.sleep_ms(100)
        print("time synced")

        self.calculate_current_week()
        print("current week", self.current_week)

        print("trying to scraping ...")
        self.scraper = scraper.Scraper(
            self.privates["user"],
            self.privates["password"]
        )
        self.scraper.login()
        self.schedule = self.scraper.get_schedule()
        print("schedule retrieved")

        self.schedule_tab_schedule = None
        self.schedule_tab_decorate_text = None

        self.general_notices_tab_notices = None

        self.class_notices_tab_notices = []

        # turn off wifi to save power
        self.wifi_deactive()

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
        if self.wlan.isconnected():
            return

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
        t = ntptime.time()
        t += tz_offset_hours * 3600
        tm = time.gmtime(t)
        RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

    def set_led_color(self, color):
        self.neopixel[0] = color
        self.neopixel.write()

    def calculate_current_week(self):
        current_time = helper.get_time()
        self.current_week = int(
            (current_time - self.privates["starting_date_ts"]) // 604800
        ) + self.privates["starting_week"]

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
            vtab = self.touch_tab.read()

            if vtab > self.touch_threshold:
                self.current_tab += 1
                if self.current_tab >= Tab.MAX:
                    self.current_tab = 0
                print("tab changed to", self.current_tab)
                self.draw_tab()

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
        poll = select.poll()
        poll.register(sys.stdin, select.POLLIN)
        buffer = ""

        print("serial command task started, you can now send commands")

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

    def draw_date(self, date):
        self.tft.fillrect((109, 2), (49, 16), TFT.WHITE)
        self.tft.text((109, 2), f"{date[2]:02d}", TFT.BLACK, sysfont, 2)
        self.tft.text((137, 2), f"{date[1]:02d}", TFT.BLACK, sysfont, 2)
        self.tft.fillrect((109, 20), (23, 8), TFT.WHITE)
        self.tft.text((109, 20), f"{date[0]:04d}", TFT.BLACK, sysfont, 1)

    def draw_time(self, time):
        self.tft.fillrect((2, 2), (104, 32), TFT.WHITE)
        self.tft.text(
            (2, 2),
            f"{time[0]:02d}:{time[1]:02d}",
            TFT.BLACK,
            sysfont,
            4
        )
        self.draw_bluetooth_icon()
        self.draw_bluetooth_paired_icon()

    def update_schedule_tab(self, schedule, decorate_text):
        self.schedule_tab_schedule = schedule
        self.schedule_tab_decorate_text = decorate_text
        if self.current_tab == Tab.SCHEDULE:
            self.prev_tab = -1

    def draw_schedule_tab(self):
        v = 35
        self.tft.fillrect((2, v), (156, 93), TFT.WHITE)
        self.tft.text((2, v), self.schedule_tab_decorate_text, TFT.GRAY, sysfont, 1)
        v += sysfont["Height"] + 1
        if len(self.schedule_tab_schedule) == 0:
            self.tft.text((2, v), "there is nothing to show", TFT.GRAY, sysfont, 1)
            return

        for sub in self.schedule_tab_schedule:
            class_name = vietnamese.to_ascii(sub["class_name"])
            if len(class_name) > 26:
                class_name = class_name[:23] + "..."

            self.tft.text((2, v), class_name, TFT.BLUE, sysfont, 1)
            v += sysfont["Height"] + 1
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
            v += sysfont["Height"] + 2

    def update_general_notices_tab(self):
        self.general_notices_tab_notices = self.scraper.get_notices("", scraper.Tab.DAO_TAO)
        if self.current_tab == Tab.GENENAL_NOTICES:
            self.prev_tab = -1

    def draw_general_notices_tab(self):
        v = 35
        self.tft.fillrect((2, v), (156, 93), TFT.WHITE)
        self.tft.text((2, v), "Dao tao", TFT.GRAY, sysfont, 1)
        v += sysfont["Height"] + 1
        if len(self.general_notices_tab_notices) == 0:
            self.tft.text((2, v), "there is nothing to show", TFT.GRAY, sysfont, 1)
            return

        for date, cap in zip(self.general_notices_tab_notices[0], self.general_notices_tab_notices[1]):
            self.tft.text((2, v), date, TFT.RED, sysfont, 1)
            v += self.tft.text(
                (67, v),
                vietnamese.to_ascii(cap),
                TFT.BLACK,
                sysfont,
                1
            )
            v += sysfont["Height"] + 2
            if v > 128:
                return

    def update_class_notices_tab(self):
        notices = self.scraper.get_notices(self.privates["class_code"], scraper.Tab.LOP_HOC_PHAN)
        notices = scraper.Scraper.parse_class_notices(notices[1], notices[2], notices[0])

        # remove outdated notices
        self.class_notices_tab_notices.clear()
        self.class_notices_tab_notices = []
        today = time.localtime()
        today = f"{today[0]:04d}:{today[1]:02d}:{today[2]:02d}"

        for cancelled in notices[0]:
            if cancelled["cancelled_date"] >= today:
                self.class_notices_tab_notices.append(cancelled)
        for make_up in notices[1]:
            if make_up["make_up_date"] >= today:
                self.class_notices_tab_notices.append(make_up)

        self.class_notices_tab_notices.sort(key=lambda x: x["cancelled_date"] if "cancelled_date" in x.keys() else x["make_up_date"], reverse=True)

        if self.current_tab == Tab.CLASS_NOTICES:
            self.prev_tab = -1

    def draw_class_notices_tab(self):
        v = 35
        self.tft.fillrect((2, v), (156, 93), TFT.WHITE)
        self.tft.text((2, v), "Lop hoc phan", TFT.GRAY, sysfont, 1)
        v += sysfont["Height"] + 1
        if len(self.class_notices_tab_notices) == 0:
            self.tft.text((2, v), "there is nothing to show", TFT.GRAY, sysfont, 1)
            return

        for note in self.class_notices_tab_notices:
            if "cancelled_date" in note.keys():
                self.tft.text((2, v), "Nghi hoc", TFT.GREEN, sysfont, 1)
                self.tft.text(
                    (47, v),
                    " " + helper.reverse_date(note["cancelled_date"])[:-5],
                    TFT.BLACK,
                    sysfont,
                    1,
                )
                v += sysfont["Height"] + 1
                self.tft.text(
                    (2, v),
                    vietnamese.to_ascii(note["class_name"]),
                    TFT.BLACK,
                    sysfont,
                    1,
                    nowrap=True,
                )
                v += sysfont["Height"] + 2
            else:
                self.tft.text(
                    (2, v),
                    "Hoc bu",
                    TFT.RED,
                    sysfont,
                    1,
                )
                self.tft.text(
                    (41, v),
                    " " + helper.reverse_date(note["make_up_date"])[:-5] + ", tiet " + note["start_period"] + '-' + note["end_period"],
                    TFT.BLACK,
                    sysfont,
                    1,
                )
                v += sysfont["Height"] + 1
                self.tft.text(
                    (2, v),
                    "Mon " + vietnamese.to_ascii(note["class_name"]),
                    TFT.BLACK,
                    sysfont,
                    1,
                    nowrap=True,
                )
                v += sysfont["Height"] + 2
            if v > 128:
                return

    def draw_tab(self):
        if self.prev_tab == self.current_tab:
            return

        if self.current_tab == Tab.SCHEDULE:
            self.draw_schedule_tab()
        elif self.current_tab == Tab.CLASS_NOTICES:
            self.draw_class_notices_tab()
        elif self.current_tab == Tab.GENENAL_NOTICES:
            self.draw_general_notices_tab()

        self.prev_tab = self.current_tab
