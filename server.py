
from datetime import date as D
from datetime import datetime as DT
from git import Repo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import socketserver
import sqlite3
import sys
import threading
import time
import traceback
import urllib.request
import requests

## CONFIG ## 
PORT = 8000
SENSOR_UPDATE_INTERVAL = 60  # seconds
GRAPH_UPDATE_INTERVAL = 900  # 900s = 15m
sensor1ip = 'http://192.168.4.20:42000'
indexfile = r"index.html"
palette = ['xkcd:sea blue', 'xkcd:leaf green', '#efa00b', '#d65108', '#591f0a']

def timestamp(): return time.strftime("%Y-%m-%d %H:%M:%S")


### Webserv ###
class Slave(threading.Thread):
    def run(self):
        self.kill = False
        self.ready = False
        import http.server
        Handler = http.server.SimpleHTTPRequestHandler
        try:
            httpd = socketserver.TCPServer(('0.0.0.0', PORT), Handler)
        except OSError as e:
            print (e)
            print("%s\tCaught socket exception, retrying..." % timestamp())
            time.sleep(10)
            self.run()

        self.ready = True

        while not self.kill:
            httpd.handle_request()

        return


### Sensor related functions ###
def read_sensor():
    try:
        req = requests.get(sensor1ip)
    except Exception as e:
        print(e)
        print("%s\tAn unknown error occurred, retrying..." % timestamp())
        time.sleep(10)
        return False

    if req.status_code is 200:
        jdata = req.json()
        print("%s\t%s" % (timestamp(), jdata))
        return jdata
    else:
        print("%s\tUnknown status code %d, retrying..."
              % (timestamp(), req.status_code))
        time.sleep(10)
        return False


### main loop ###
def update(c, conn, webslave):
    loopcounter = 0
    while(webslave.ready is False):
        print("%s\tWaiting for webslave..." % timestamp())
        try:
            urllib.request.urlopen('http://127.0.0.1:8000')  # kill the zombies
        except:
            pass
        time.sleep(10)

    sensor_sleeptime = 0
    graph_sleeptime = 0

    while (True):

        jdata = read_sensor()
        if jdata is False: continue

        with open(indexfile, 'w') as f:
            f.write(fmt_html(jdata))

        if not (np.isnan(jdata["celsius"]) or np.isnan(jdata["humidity"]) or 
                jdata["reservoir"] > 40 or jdata["ec"] <= 0 ):
            c.execute("INSERT INTO sensor1 VALUES ('%s', %s, %s, %s, %s, %s, %s)"
                      % (timestamp(), jdata["celsius"], jdata["humidity"],
                         jdata["heat index"], jdata["ph"], jdata["ec"],
                         jdata["reservoir"]))

        else:
            print("%s\tReceived garbage data from sensor" % timestamp())

        loopcounter += 1

        if sensor_sleeptime == graph_sleeptime:
            conn.commit()
            graph(c, commit=True)

        t = time.time()
        sensor_sleeptime = SENSOR_UPDATE_INTERVAL - ((t % SENSOR_UPDATE_INTERVAL))
        graph_sleeptime = GRAPH_UPDATE_INTERVAL - ((t % GRAPH_UPDATE_INTERVAL))
        if sensor_sleeptime - .75 > 0: time.sleep(sensor_sleeptime - .75)

if __name__ == '__main__':
    webslave = Slave()
    webslave.start()
    conn = sqlite3.connect("./sensordata.db")
    c = conn.cursor()
    time.sleep(1)
    try:
        update(c, conn, webslave)
    except KeyboardInterrupt as e:
        print("\n%s\tCTRL-C Detected. Closing threads..." % timestamp())
        webslave.kill = True
        conn.commit()
        c.close()
        conn.close()
        urllib.request.urlopen('http://127.0.0.1:8000') # slave's final request
#        requests.get('http://127.0.0.1:8000')
        webslave.join()
    except Exception:# as e:
#        print(e)
        traceback.print_exc(file=sys.stdout)
        print("\n%s\tSomething bad happened, attempting to shutdown gracefully"
              % timestamp())
        webslave.kill = True
        conn.commit()
        c.close()
        conn.close()
        urllib.request.urlopen('http://127.0.0.1:8000') # slave's final request
#        requests.get('http://127.0.0.1:8000')
        webslave.join()

    sys.exit()
