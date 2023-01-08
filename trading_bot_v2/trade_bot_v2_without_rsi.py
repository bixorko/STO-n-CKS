import json
import sys
import socket
import logging
from sys import argv
import time
import ssl
import yfinance as yf
import talib as ta
from display_resources.lib.waveshare_OLED import OLED_1in5
from PIL import Image, ImageDraw, ImageFont
from threading import Thread

# set to true on debug environment only
DEBUG = False

#default connection properites
DEFAULT_XAPI_ADDRESS        = 'xapi.xtb.com'
DEFAULT_XAPI_PORT           = 5124
DEFUALT_XAPI_STREAMING_PORT = 5125

# wrapper name and version
WRAPPER_NAME    = 'python'
WRAPPER_VERSION = '2.5.0'

# API inter-command timeout (in ms)
API_SEND_TIMEOUT = 100

# max connection tries
API_MAX_CONN_TRIES = 3

# logger properties
logger = logging.getLogger("jsonSocket")
FORMAT = '[%(asctime)-15s][%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(format=FORMAT)

if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.CRITICAL)


class TransactionSide(object):
    BUY = 0
    SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5
    
class TransactionType(object):
    ORDER_OPEN = 0
    ORDER_CLOSE = 2
    ORDER_MODIFY = 3
    ORDER_DELETE = 4

class JsonSocket(object):
    def __init__(self, address, port, encrypt = False):
        self._ssl = encrypt 
        if self._ssl != True:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = ssl.wrap_socket(sock)
        self.conn = self.socket
        self._timeout = None
        self._address = address
        self._port = port
        self._decoder = json.JSONDecoder()
        self._receivedData = ''

    def connect(self):
        for i in range(API_MAX_CONN_TRIES):
            try:
                self.socket.connect( (self.address, self.port) )
            except socket.error as msg:
                logger.error("SockThread Error: %s" % msg)
                time.sleep(0.25)
                continue
            logger.info("Socket connected")
            return True
        return False

    def _sendObj(self, obj):
        msg = json.dumps(obj)
        self._waitingSend(msg)

    def _waitingSend(self, msg):
        if self.socket:
            sent = 0
            msg = msg.encode('utf-8')
            while sent < len(msg):
                sent += self.conn.send(msg[sent:])
                logger.info('Sent: ' + str(msg))
                time.sleep(API_SEND_TIMEOUT/1000)

    def _read(self, bytesSize=4096):
        if not self.socket:
            raise RuntimeError("socket connection broken")
        while True:
            char = self.conn.recv(bytesSize).decode()
            self._receivedData += char
            try:
                (resp, size) = self._decoder.raw_decode(self._receivedData)
                if size == len(self._receivedData):
                    self._receivedData = ''
                    break
                elif size < len(self._receivedData):
                    self._receivedData = self._receivedData[size:].strip()
                    break
            except ValueError as e:
                continue
        logger.info('Received: ' + str(resp))
        return resp

    def _readObj(self):
        msg = self._read()
        return msg

    def close(self):
        logger.debug("Closing socket")
        self._closeSocket()
        if self.socket is not self.conn:
            logger.debug("Closing connection socket")
            self._closeConnection()

    def _closeSocket(self):
        self.socket.close()

    def _closeConnection(self):
        self.conn.close()

    def _get_timeout(self):
        return self._timeout

    def _set_timeout(self, timeout):
        self._timeout = timeout
        self.socket.settimeout(timeout)

    def _get_address(self):
        return self._address

    def _set_address(self, address):
        pass

    def _get_port(self):
        return self._port

    def _set_port(self, port):
        pass

    def _get_encrypt(self):
        return self._ssl

    def _set_encrypt(self, encrypt):
        pass

    timeout = property(_get_timeout, _set_timeout, doc='Get/set the socket timeout')
    address = property(_get_address, _set_address, doc='read only property socket address')
    port = property(_get_port, _set_port, doc='read only property socket port')
    encrypt = property(_get_encrypt, _set_encrypt, doc='read only property socket port')
    
    
class APIClient(JsonSocket):
    def __init__(self, address=DEFAULT_XAPI_ADDRESS, port=DEFAULT_XAPI_PORT, encrypt=True):
        super(APIClient, self).__init__(address, port, encrypt)
        if(not self.connect()):
            raise Exception("Cannot connect to " + address + ":" + str(port) + " after " + str(API_MAX_CONN_TRIES) + " retries")

    def execute(self, dictionary):
        self._sendObj(dictionary)
        return self._readObj()    

    def disconnect(self):
        self.close()
        
    def commandExecute(self,commandName, arguments=None):
        return self.execute(baseCommand(commandName, arguments))

# Command templates
def baseCommand(commandName, arguments=None):
    if arguments==None:
        arguments = dict()
    return dict([('command', commandName), ('arguments', arguments)])

def loginCommand(userId, password, appName=''):
    return baseCommand('login', dict(userId=userId, password=password, appName=appName))
    

def main():

    # enter your login credentials here
    userId = argv[2]
    password = argv[4]
    xtb_pair = argv[6]
    yahoo_pair = argv[8]
    chart_interval = argv[10]
    
    arg_display = argv[12]
    with_display = False
    if arg_display == "on":
        with_display = True

    # create & connect to RR socket
    client = APIClient()
    
    # connect to RR socket, login
    loginResponse = client.execute(loginCommand(userId=userId, password=password))
    logger.info(str(loginResponse)) 

    # check if user logged in correctly
    if(loginResponse['status'] == False):
        print('Login failed. Error code: {0}'.format(loginResponse['errorCode']))
        return

    # get ssId from login response
    ssid = loginResponse['streamSessionId']
    
    trade(client, xtb_pair, yahoo_pair, chart_interval, with_display)
    
    # gracefully close RR socket
    client.disconnect()
    
# global variables for spearate display thread
open_price = 0.0
close_price = 0.0
ema_5 = 0.0
ema_10 = 0.0
macd = 0.0
rsi = 0.0
spread = 0.0
is_bearish = False
is_bullish = False


def trade(client, xtb_pair, yahoo_pair, chart_interval, with_display):
    disp = OLED_1in5.OLED_1in5()
    disp.Init()
    font = ImageFont.truetype('./display_resources/pic/Font.ttc', 13)
    create_thread = True

    while True:
        # get symbol info
        symbol_info = client.commandExecute('getSymbol', {'symbol' : xtb_pair})
        spread = symbol_info["returnData"]["spreadRaw"]

        chart = get_chart(client, 30, xtb_pair)

        open_price = get_open_price(chart)
        close_price = get_close_price(chart)

        ema_5, ema_10, macd, rsi = get_pair_indicators(yahoo_pair, chart_interval, "4d")

        print("OPEN Price: ", open_price)
        print("CLOSE Price: ", close_price)
        print("EMA5: ", ema_5)
        print("EMA10: ", ema_10)
        print("Spread: ", spread * 10**4)
        print("MACD: ", macd)
        print("RSI: ", rsi)

        if ema_5 < ema_10:   #bearish
            if  not is_bearish and not is_bullish: # decide if the trend is bullish or bearish after first launch
                is_bearish = True
            
            elif is_bullish:   #trend switched from bullish to bearish
                is_bullish = False      
                is_bearish = True
                close_trade(client, 0.02, xtb_pair)     #close opened trade (if exists)
                close_trade(client, 0.02, xtb_pair)     #close opened trade (if exists)
                if macd < 0: # check spread and MACD check
                    open_trade(client, 1, 0.02, xtb_pair, False)   #open short position
                    open_trade(client, 1, 0.02, xtb_pair, True)   #open short position
                    print("OPENED SHORT POSITION!")

        elif ema_5 > ema_10: #bullish
            if  not is_bearish and not is_bullish: # decide if the trend is bullish or bearish after first launch
                is_bullish = True
            
            elif is_bearish:   #trend switched from bearish to bullish
                is_bearish = False      
                is_bullish = True
                close_trade(client, 0.02, xtb_pair)     #close opened trade (if exists)
                close_trade(client, 0.02, xtb_pair)     #close opened trade (if exists)
                if macd > 0: # check spread and MACD check
                    open_trade(client, 0, 0.02, xtb_pair, False)   #open long position
                    open_trade(client, 0, 0.02, xtb_pair, True)   #open long position
                    print("OPENED LONG POSITION!")

        print("Is Bearish: ", is_bearish)
        print("Is Bullish: ", is_bullish, "\n")
            
        if create_thread and with_display:
            thread = Thread(target=update_display, args=(disp, font), daemon=True)
            thread.start()
            create_thread = False
		
        keep_alive(client, xtb_pair)
        
        
def update_display(disp, font):
    while(True):
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
        time.sleep(1800)

# kazdy minutu sa spytat ci pocet tradov == 1, ak ano, tak to znamena, ze jeden trade je na take profit
# a musime editnut stoploss ostavajuceho tradu na 0e aby ten trade uz nikdy neprerobil
# toto nizsie fnuguje -> ale pozor treba takenut order z responsu getTrades a nie z toho co vrati ten resposne ked sa trade vytvori
# amen
        
# {
#     "command": "tradeTransaction",
#     "arguments": {
#         "tradeTransInfo": {
#             "order": 458056969,
#             "price": 1.4,
#             "sl": 0,
#             "tp": 17200,
#             "symbol": "BITCOIN",
#             "type": 3,
#             "volume": 0.1
#         }
#     }
# }

def keep_alive(client, xtb_pair):
    hit_take_profit = False
    for _ in range(30):
        if (len(client.commandExecute('getTrades', {'openedOnly': True})['returnData']) == 1) and not hit_take_profit:
            active_trade = client.commandExecute('getTrades', {'openedOnly': True})['returnData'][0]
            new_sl = active_trade['open_price']
            order = active_trade['order']
            client.commandExecute('tradeTransaction', {"tradeTransInfo": {"order": order,
                                        "price": 1,
                                        "sl": new_sl,
                                        "tp": 0,
                                        "symbol": xtb_pair,
                                        "type": 3,
                                        "volume": 0.02}})
            hit_take_profit = True
        client.commandExecute('ping')
        time.sleep(60)


def close_trade(client, volume, xtb_pair):
    trades = client.commandExecute('getTrades', {'openedOnly' : True})
    if(trades["returnData"]):
        client.commandExecute('tradeTransaction', {"tradeTransInfo": { "order": trades["returnData"][0]["order"],
                            "symbol": xtb_pair,
                            "type": 2,
                            "price": 1,
                            "volume": volume}})


def open_trade(client, command, volume, xtb_pair, without_tp):
    # calculate TP and SL based on tactic
    if command == 0:
        price = client.commandExecute('getSymbol', {"symbol": xtb_pair})["returnData"]["ask"]
        stoploss = round(price-0.0025, 5)
        takeprofit = round(price+0.0030, 5)
    else:
        price = client.commandExecute('getSymbol', {"symbol": xtb_pair})["returnData"]["bid"]
        stoploss = round(price+0.0025, 5)
        takeprofit = round(price-0.0030, 5)
        
    if without_tp:
        takeprofit = 0
    
    # open transaction - arguments based on http://developers.xstore.pro/documentation/#tradeTransaction
    return client.commandExecute('tradeTransaction', {"tradeTransInfo": { "cmd": command,
                                        "customComment": "Some text",
                                        "order": 0,
                                        "symbol": xtb_pair,
                                        "price": 1,
                                        "tp": takeprofit,
                                        "sl": stoploss,
                                        "offset": 0,
                                        "type": 0,
                                        "volume": volume}})


def get_pair_indicators(pair, chart_interval, chart_history):
    df = yf.Ticker(pair).history(period=chart_history, interval=chart_interval)
    df['ema_10'] = df['Open'].ewm(span=10, adjust=False, min_periods=10).mean()
    df['ema_5'] = df['Close'].ewm(span=5, adjust=False, min_periods=5).mean()

    k = df['Close'].ewm(span=8, adjust=False, min_periods=8).mean()
    d = df['Close'].ewm(span=20, adjust=False, min_periods=20).mean()
    macd = k - d
    macd_s = macd.ewm(span=9, adjust=False, min_periods=9).mean()
    macd_h = macd - macd_s

    df['macd'] = df.index.map(macd)
    df['macd_h'] = df.index.map(macd_h)
    df['macd_s'] = df.index.map(macd_s)

    df['rsi'] = ta.RSI(df['Close'], timeperiod=14)

    indicators = df.iloc[-2]
    return indicators['ema_5'], indicators['ema_10'], indicators['macd_h'], indicators['rsi']


def get_chart(client, period, xtb_pair):
    return client.commandExecute('getChartLastRequest', 
            {
                'info': 
                {
                    "period": period,
                    "start": int(time.time()-200000) * 1000,
                    "symbol": xtb_pair
                }
            })


def get_open_price(chart):
    return chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["open"] / (10 ** chart["returnData"]["digits"])


def get_close_price(chart):
    return chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["open"] / (10 ** chart["returnData"]["digits"]) \
        + (chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["close"] / (10 ** chart["returnData"]["digits"]))


if __name__ == "__main__":
    if len(argv) != 13:
        print("Run script as: python trade_bot.py [--id <your account id>] [--password <your account password>] [--xtb <xtb pair name>] [--yf <yahoo finance pair name] [--chart <X(m/h/d/y)] [--display (on/off)]", file=sys.stderr)
        exit(1)
    main()	


# import yfinance as yf
# import talib as ta

# df = yf.Ticker('EURUSD=X').history(period='2d', interval='5m')
# df['ema_10'] = df['Open'].ewm(span=10, adjust=False, min_periods=10).mean()
# df['ema_5'] = df['Close'].ewm(span=5, adjust=False, min_periods=5).mean()

# k = df['Close'].ewm(span=8, adjust=False, min_periods=8).mean()
# d = df['Close'].ewm(span=20, adjust=False, min_periods=20).mean()
# macd = k - d
# macd_s = macd.ewm(span=9, adjust=False, min_periods=9).mean()
# macd_h = macd - macd_s

# df['macd'] = df.index.map(macd)
# df['macd_h'] = df.index.map(macd_h)
# df['macd_s'] = df.index.map(macd_s)

# df['rsi'] = ta.RSI(df['Close'], timeperiod=14)

# print(df.iloc[-2]['rsi'])
