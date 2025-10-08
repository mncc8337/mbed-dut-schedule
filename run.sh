#!/bin/sh

mpremote cp -r config.json main.py requests.py helper.py scraper.py ST7735.py sysfont.py vietnamese.py aioble :
mpremote reset
mpremote repl
