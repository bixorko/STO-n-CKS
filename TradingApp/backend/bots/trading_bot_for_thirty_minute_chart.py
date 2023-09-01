import json
import socket
import logging
import time
import ssl
import yfinance as yf
import talib as ta
import pause

DEBUG = False
DEFAULT_XAPI_ADDRESS = 'xapi.xtb.com'
DEFAULT_XAPI_PORT = 5124
DEFUALT_XAPI_STREAMING_PORT = 5125
WRAPPER_NAME = 'python'
WRAPPER_VERSION = '2.5.0'
API_SEND_TIMEOUT = 100
API_MAX_CONN_TRIES = 3

logger = logging.getLogger("jsonSocket")
FORMAT = '[%(asctime)-15s][%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(format=FORMAT)
logger.setLevel(logging.DEBUG if DEBUG else logging.CRITICAL)

class TransactionSide:
    BUY, SELL, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP = range(6)

class TransactionType:
    ORDER_OPEN, ORDER_CLOSE, ORDER_MODIFY, ORDER_DELETE = range(4)

class JsonSocket:
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

def baseCommand(commandName, arguments=None):
    if arguments==None:
        arguments = dict()
    return dict([('command', commandName), ('arguments', arguments)])

def loginCommand(userId, password, appName=''):
    return baseCommand('login', dict(userId=userId, password=password, appName=appName))

class TradingBotForThirtyMinuteChart:
    def __init__(self, bot_id, user_id, password, xtb_pair, yahoo_pair, chart_interval, chart_history, period, volume):
        self.running = True
        self.bot_id = bot_id
        self.user_id = user_id
        self.password = password
        self.xtb_pair = xtb_pair
        self.yahoo_pair = yahoo_pair
        self.chart_interval = chart_interval
        self.open_price = 0.0
        self.close_price = 0.0
        self.ema_5 = 0.0
        self.ema_10 = 0.0
        self.macd = 0.0
        self.rsi = 0.0
        self.spread = 0.0
        self.is_bearish = False
        self.is_bullish = False
        self.start_time = int(time.time())
        self.volume = volume
        self.chart_history = chart_history
        self.period = period

    def get_bot_info(self):
        return {
            "bot_id": self.bot_id,
            "user_id": self.user_id,
            "xtb_pair": self.xtb_pair,
            "yahoo_pair": self.yahoo_pair,
            "chart_interval": self.chart_interval,
            "ema_5": self.ema_5,
            "ema_10": self.ema_10,
            "macd": self.macd,
            "rsi": self.rsi,
            "spread": self.spread,
            "trend": "Bullish" if self.is_bullish else "Bearish" if self.is_bearish else "neutral"
        }

    def renewConnection(self):
        client = APIClient()
        loginResponse = client.execute(loginCommand(userId=self.user_id, password=self.password))

        if not loginResponse['status']:
            print('Login failed. Error code: {0}'.format(loginResponse['errorCode']))
            return

        return client

    def stop(self):
        self.running = False

    def trade(self):
        while self.running:
            client = self.renewConnection()

            symbol_info = client.commandExecute('getSymbol', {'symbol' : self.xtb_pair})
            self.spread = (symbol_info["returnData"]["spreadRaw"]) * 10**4

            chart = self.get_chart(client)

            self.set_open_price(chart)
            self.set_close_price(chart)

            self.set_pair_indicators()

            print("OPEN Price: ", self.open_price)
            print("CLOSE Price: ", self.close_price)
            print("EMA5: ", self.ema_5)
            print("EMA10: ", self.ema_10)
            print("Spread: ", self.spread)
            print("MACD: ", self.macd)
            print("RSI: ", self.rsi)

            if self.ema_5 < self.ema_10:
                if not self.is_bearish and not self.is_bullish:
                    self.is_bearish = True
                
                elif self.is_bullish:  
                    self.is_bullish = False      
                    self.is_bearish = True
                    self.close_trade(client)   
                    if self.macd < 0 and self.rsi < 50:
                        time.sleep(3)
                        self.open_trade(client, 1, False)  
                        time.sleep(3)
                        self.open_trade(client, 1, True)   
                        print("OPENED SHORT POSITION!")

            elif self.ema_5 > self.ema_10:
                if not self.is_bearish and not self.is_bullish:
                    self.is_bullish = True
                
                elif self.is_bearish:
                    self.is_bearish = False      
                    self.is_bullish = True
                    self.close_trade(client)
                    if self.macd > 0 and self.rsi > 50:
                        time.sleep(3)
                        self.open_trade(client, 0, False)
                        time.sleep(3)
                        self.open_trade(client, 0, True)
                        print("OPENED LONG POSITION!")

            print("Is Bearish: ", self.is_bearish)
            print("Is Bullish: ", self.is_bullish, "\n")
            
            self.keep_alive(client)
            client.disconnect()

    def keep_alive(self, client):
        hit_take_profit = False
        
        for _ in range(30):
            self.start_time += 60
            pause.until(self.start_time)
            active_trades = client.commandExecute('getTrades', {'openedOnly': True})['returnData']
            if (len(active_trades) == 1) and not hit_take_profit:
                active_trade = active_trades[0]
                new_sl = active_trade['open_price']
                order = active_trade['order']
                client.commandExecute('tradeTransaction', {"tradeTransInfo": {"order": order,
                                            "price": 1,
                                            "sl": new_sl,
                                            "tp": 0,
                                            "symbol": self.xtb_pair,
                                            "type": 3,
                                            "volume": self.volume}})
                hit_take_profit = True


    def close_trade(self, client):
        trades = client.commandExecute('getTrades', {'openedOnly' : True})
        if(trades["returnData"]):
            try:
                client.commandExecute('tradeTransaction', {"tradeTransInfo": { "order": trades["returnData"][0]["order"],
                                    "symbol": self.xtb_pair,
                                    "type": 2,
                                    "price": 1,
                                    "volume": self.volume}})
            except:
                return
            try:
                client.commandExecute('tradeTransaction', {"tradeTransInfo": { "order": trades["returnData"][1]["order"],
                        "symbol": self.xtb_pair,
                        "type": 2,
                        "price": 1,
                        "volume": self.volume}})
            except:
                pass

    def open_trade(self, client, command, without_tp):
        # calculate TP and SL based on tactic
        if command == 0:
            price = client.commandExecute('getSymbol', {"symbol": self.xtb_pair})["returnData"]["ask"]
            stoploss = round(price-0.0025, 5)
            takeprofit = round(price+0.0030, 5)
        else:
            price = client.commandExecute('getSymbol', {"symbol": self.xtb_pair})["returnData"]["bid"]
            stoploss = round(price+0.0025, 5)
            takeprofit = round(price-0.0030, 5)
            
        if without_tp:
            takeprofit = 0
        
        # open transaction - arguments based on http://developers.xstore.pro/documentation/#tradeTransaction
        client.commandExecute('tradeTransaction', {"tradeTransInfo": { "cmd": command,
                                        "customComment": "Some text",
                                        "order": 0,
                                        "symbol": self.xtb_pair,
                                        "price": 1,
                                        "tp": takeprofit,
                                        "sl": stoploss,
                                        "offset": 0,
                                        "type": 0,
                                        "volume": self.volume}})

    def set_pair_indicators(self):
        df = yf.Ticker(self.yahoo_pair).history(period=self.chart_history, interval=self.chart_interval)
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

        self.ema_5 = indicators['ema_5']
        self.ema_10 = indicators['ema_10']
        self.macd = indicators['macd_h']
        self.rsi = indicators['rsi']

    def get_chart(self, client):
        return client.commandExecute('getChartLastRequest', 
                {
                    'info': 
                    {
                        "period": self.period,
                        "start": int(time.time()-200000) * 1000,
                        "symbol": self.xtb_pair
                    }
                })

    def set_open_price(self, chart):
        self.open_price = chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["open"] / (10 ** chart["returnData"]["digits"])

    def set_close_price(self, chart):
        self.close_price = chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["open"] / (10 ** chart["returnData"]["digits"]) \
            + (chart["returnData"]["rateInfos"][len(chart["returnData"]["rateInfos"])-2]["close"] / (10 ** chart["returnData"]["digits"]))