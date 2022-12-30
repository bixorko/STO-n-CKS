import json
import sys
import socket
import logging
from sys import argv
import time
import ssl
import yfinance as yf
import talib as ta

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
    
    trade(client)
    
    # gracefully close RR socket
    client.disconnect()

def trade(client):

    is_bearish = False
    is_bullish = False

    while True:
        # get symbol info
        symbol_info = client.commandExecute('getSymbol', {'symbol' : 'EURUSD'})
        spread = symbol_info["returnData"]["spreadRaw"]

        chart = get_chart(client, 30)

        open_price = get_open_price(chart)
        close_price = get_close_price(chart)

        ema_5, ema_10, macd, rsi = get_pair_indicators("EURUSD=X", "30m", "4d")

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
                close_trade(client, 0.04)     #close opened trade (if exists)
                if macd < 0 and rsi < 50: # check spread and MACD check
                    open_trade(client, 1, 0.04, open_price)   #open short position
                    print("OPENED SHORT POSITION!")

        elif ema_5 > ema_10: #bullish
            if  not is_bearish and not is_bullish: # decide if the trend is bullish or bearish after first launch
                is_bullish = True
            
            elif is_bearish:   #trend switched from bearish to bullish
                is_bearish = False      
                is_bullish = True
                close_trade(client, 0.04)     #close opened trade (if exists)
                if macd > 0 and rsi > 50: # check spread and MACD check
                    open_trade(client, 0, 0.04, open_price)   #open long position
                    print("OPENED LONG POSITION!")

        print("Is Bearish: ", is_bearish)
        print("Is Bullish: ", is_bullish, "\n")
        
        time.sleep(1800)


def close_trade(client, volume):
    trades = client.commandExecute('getTrades', {'openedOnly' : True})
    if(trades["returnData"]):
        client.commandExecute('tradeTransaction', {"tradeTransInfo": { "order": trades["returnData"][0]["order"],
                            "symbol": "EURUSD",
                            "type": 2,
                            "price": 1,
                            "volume": 0.04}})


def open_trade(client, command, volume, open_price):
    #calculate TP and SL based on tactic
    if command == 0:
        stoploss = open_price-0.002
        takeprofit = open_price+0.0027
    else:
        stoploss = open_price+0.002
        takeprofit = open_price-0.0027
    
    # open transaction - arguments based on http://developers.xstore.pro/documentation/#tradeTransaction
    return client.commandExecute('tradeTransaction', {"tradeTransInfo": { "cmd": command,
                                        "customComment": "Some text",
                                        "order": 0,
                                        "symbol": "EURUSD",
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


def get_chart(client, period):
    return client.commandExecute('getChartLastRequest', 
            {
                'info': 
                {
                    "period": period,
                    "start": int(time.time()-20000) * 1000,
                    "symbol": "EURUSD"
                }
            })


def get_open_price(chart):
    return chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["open"] / (10 ** chart["returnData"]["digits"])


def get_close_price(chart):
    return chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["open"] / (10 ** chart["returnData"]["digits"]) \
        + (chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["close"] / (10 ** chart["returnData"]["digits"]))


if __name__ == "__main__":
    if len(argv) != 5:
        print("Run script as: python trade_bot.py [--id <your account id>] [--password <your account password>]!", file=sys.stderr)
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