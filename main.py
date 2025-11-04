import builtins
import time
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
TOUCH_TAB_CHANGE_PIN = Pin(10)
TOUCH_THRESHOLD = 35000

MAX_TEXT_LEN = 26

BLE_SERVICE_UUID = 'cebcf692-9250-4457-86eb-556ab41ca932'
BLE_LED_UUID = '8fff00d0-f1c4-437f-a369-e99227720b6c'
ADV_INTERVAL_MS = 250_000


def log(*args, log_type="INFO", not_log=False, **kwargs):
    if not_log:
        builtins.print(*args, **kwargs)
        return
    dt = time.localtime()
    timestamp = f"{dt[0]:04d}-{dt[1]:02d}-{dt[2]:02d} {dt[3]:02d}:{dt[4]:02d}:{dt[5]:02d}"
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
    TOUCH_TAB_CHANGE_PIN,
    TOUCH_THRESHOLD,
    BLE_SERVICE_UUID,
    BLE_LED_UUID,
    ADV_INTERVAL_MS,
)
app.tft.fill(TFT.WHITE)
prev_day = -1
prev_hour = -1
today_schedule = app.get_schedule()
decorate_text = "Lịch học hôm nay"
dim_at_night = False


while True:
    datetime = time.localtime()
    schedule_weekday = datetime[6]
    schedule_date = f"{datetime[0]:04d}/{datetime[1]:02d}/{datetime[2]:02d}"
    schedule_week = app.current_week
    update_schedule_flag = False

    # dim display in nighttime
    if datetime[3] * 60 + datetime[4] > 22 * 60 + 30 and not dim_at_night:
        app.set_backlight_output(20)
        dim_at_night = True

    # sleep
    if datetime[3] >= 0 and datetime[3] < 5:
        datetime_copy = list(datetime)
        datetime_copy[3] = 5
        datetime_copy[4] = 0
        datetime_copy[5] = 0
        sleep_time = time.mktime(tuple(datetime_copy)) - time.mktime(datetime)
        app.set_backlight_output(0)
        app.stop_second_thread()
        time.sleep(sleep_time)
        app.start_second_thread()
        app.set_backlight_output(75)
        dim_at_night = False
        continue

    if datetime[2] != prev_day:
        print("updating schedule ...")
        app.calculate_current_week()
        prev_day = datetime[2]
        decorate_text = "Lịch học hôm nay"
        update_schedule_flag = True
        app.draw_date(datetime[0:3])

    # update notices every 2 hrs
    if datetime[3] >= prev_hour + 2:
        print("updating notices ...")
        app.wifi_active()
        app.update_general_notices_tab()
        app.update_class_notices_tab()
        app.wifi_deactive()
        prev_hour = datetime[3]

    if decorate_text == "Lịch học hôm nay":
        get_next_day = False

        # get next day's schedule if today schedule is done
        if len(today_schedule) > 0:
            last_class = today_schedule[-1]
            last_class_end_period = dut_clock.PERIOD[last_class["end_period"]][1]
            _, _, _, hour, min, sec, _, _ = datetime

            if f"{hour:02d}:{min:02d}:{sec:02d}" >= f"{last_class_end_period[0]:02d}:{last_class_end_period[1]:02d}:00":
                get_next_day = True
        else:
            get_next_day = True

        if get_next_day:
            curr_sec = time.mktime(datetime)
            nextdate = time.localtime(curr_sec + 86400)
            nextweekday = nextdate[6]
            if nextweekday < schedule_weekday:
                schedule_week += 1
            schedule_weekday = nextweekday
            schedule_date = f"{nextdate[0]:04d}/{nextdate[1]:02d}/{nextdate[2]:02d}"
            decorate_text = "Lịch học ngày mai"
            update_schedule_flag = True

    if update_schedule_flag:
        today_schedule = app.get_schedule(
            schedule_week,
            schedule_weekday,
            schedule_date
        )
        app.update_schedule_tab(
            today_schedule,
            decorate_text
        )

    app.draw_time(datetime[3:5])
    app.draw_tab()

    time.sleep(15)
