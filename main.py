import builtins
import time
from machine import RTC
from machine import Pin
from ST7735 import TFT

import dut_clock


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
TOUCH_THRESHOLD = 35000

MAX_TEXT_LEN = 26

BLE_SERVICE_UUID = 'cebcf692-9250-4457-86eb-556ab41ca932'
BLE_LED_UUID = '8fff00d0-f1c4-437f-a369-e99227720b6c'
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

app = dut_clock.App(
    SPI_ID,
    RST_PIN,
    DC_PIN,
    CS_PIN,
    BLK_PIN,
    RGB_LED_PIN,
    TOUCH_INCREASE_PIN,
    TOUCH_DECREASE_PIN,
    TOUCH_THRESHOLD,
    BLE_SERVICE_UUID,
    BLE_LED_UUID,
    ADV_INTERVAL_MS,
    rtc,
)
app.tft.fill(TFT.WHITE)
prev_day = -1
today_schedule = app.get_schedule()
decorate_text = "Today"


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
        get_next_day = False

        # get next day's schedule if today schedule is done
        if len(today_schedule) > 0:
            last_class = today_schedule[-1]
            last_class_end_period = dut_clock.PERIOD[last_class["end_period"]]
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
                get_next_day = True
        else:
            get_next_day = True

        if get_next_day:
            schedule_weekday += 1
            if schedule_weekday >= 7:
                schedule_weekday = 0
                schedule_week += 1
            decorate_text = "Tomorrow"
            update_schedule_flag = True

    if update_schedule_flag:
        app.draw_schedule(
            app.get_schedule(schedule_week, schedule_weekday),
            decorate_text
        )

    app.draw_datetime(datetime)

    time.sleep(30)
