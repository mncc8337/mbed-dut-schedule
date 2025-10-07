#!/bin/sh

mpremote cp config.json main.py requests.py helper.py scraper.py ST7735.py sysfont.py :
mpremote reset
mpremote repl
