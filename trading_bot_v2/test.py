from time import sleep
from threading import Thread
from display_resources.lib.waveshare_OLED import OLED_1in5
from PIL import Image, ImageDraw, ImageFont

# global variables for spearate display thread
open_price = 0.0
close_price = 0.0
ema_5 = 0.0
ema_10 = 0.0
macd = 0.0
rsi = 0.0
spread = 0.0
is_bearish = False
is_bullish = True


def update_display(disp, font):
    if is_bearish:
        trend = 'Bearish'
    else:
        trend = 'Bullish'
        
    disp.clear()
    image1 = Image.new('L', (disp.width, disp.height), 0)
    draw = ImageDraw.Draw(image1)
    draw.line([(0,0),(127,0)], fill = 15)
    draw.line([(0,0),(0,127)], fill = 15)
    draw.line([(0,127),(127,127)], fill = 15)
    draw.line([(127,0),(127,127)], fill = 15)

    draw.text((2,0),   f'OPEN  Price: {round(open_price, 5)}', font = font, fill = 1)
    draw.text((2,16),  f'CLOSE Price: {round(close_price, 5)}', font = font, fill = 1)
    draw.text((2,32),  f'EMA5: {round(ema_5, 5)}', font = font, fill = 1)
    draw.text((2,48),  f'EMA10: {round(ema_10, 5)}', font = font, fill = 1)
    draw.text((2,64),  f'MACD: {round(macd, 5)}', font = font, fill = 1)
    draw.text((2,80),  f'RSI: {round(rsi, 5)}', font = font, fill = 1)
    draw.text((2,96),  f'Spread: {round(spread, 2)}', font = font, fill = 1)
    draw.text((2,112), f'Trend: {trend}', font = font, fill = 1)
    image1 = image1.rotate(180)
    disp.ShowImage(disp.getbuffer(image1))
    sleep(5)

 
disp = OLED_1in5.OLED_1in5()
disp.Init()
disp.clear()
font = ImageFont.truetype('./display_resources/pic/Font.ttc', 13)
# create a thread
thread = Thread(target=update_display, args=(disp, font), daemon=True)
# run the thread
thread.start()
# wait for the thread to finish
for _ in range(100):
    sleep(3)
    print("neheh")