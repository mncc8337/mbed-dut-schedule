#!/bin/sh

mpremote cp -r config.json main.py dut_clock.py requests.py helper.py scraper.py ST7735.py sysfont.py iconfont.py vietnamese.py aioble :
mpremote reset
mpremote repl
