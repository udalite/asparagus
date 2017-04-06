import subprocess
from subprocess import Popen
import os
import json
from datetime import datetime
import time

def retry_on_error(func):
    def decorated_func(self):
        res = func(self)
        count = 0
        while not res and count < 3:
            res = func(self)
            count += 1
        return res
    return decorated_func

class W1Relay():
    """Class to work with DS2408 1Wire chip through w1_ds2408 block device"""
    def __init__(self, w1_id):
        self.w1_path = "/sys/bus/w1/devices/%s/output" % w1_id

    @retry_on_error
    def read_status_int(self):
        cmd = "dd if=%s bs=1 count=1 | hexdump" % self.w1_path
        process = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.readline().strip()
        status_hex_str = output[-2:]
        if len(status_hex_str) == 0:
            return False
        else:
            status_int = int(status_hex_str, 16)
            return status_int

    def write_status_int(self, new_status_int):
        new_status_hex = hex(new_status_int)[1:]
        cmd = "echo -e \\\\%s | dd of=%s bs=1 count=1" % (new_status_hex, self.w1_path)
        # /bin/sh doesn't support echo -e, so using /bin/bash for
        Popen(cmd, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def get_relay_status(self, relay_n):
        status_int = self.read_status_int()
        bit_mask = 1<<relay_n
        return (status_int & bit_mask == 0)

    def on(self, relay_n):
        status_int = self.read_status_int()
        new_status_int = status_int & ~(1<<relay_n)
        self.write_status_int(new_status_int)

    def off(self, relay_n):
        status_int = self.read_status_int()
        new_status_int = status_int | 1<<relay_n
        self.write_status_int(new_status_int)

class W1Thermometer():
    """Class to work with 1wire thermometer"""
    def __init__(self, w1_id):
        self.w1_path = "/sys/bus/w1/devices/%s/w1_slave" % w1_id

    def read_temp(self):
        with open(self.w1_path, "r") as fp:
            lines = fp.readlines()
            if lines[0][-4:-1] == "YES":
                water_temp = int(lines[1][-6:-1])
                water_temp = water_temp/1000.0
                return water_temp
            else:
                return False

class Settings():
    """docstring for Settings"""
    def __init__(self, path):
        self.path = path

    def get(self):
        with open(self.path, "r") as fp:
            file_data = fp.read()
            settings = json.loads(file_data)
            return settings
        return False

    def save(self, obj):
        file_data = json.dumps(obj)
        with open(self.path, "w") as fp:
            fp.write(file_data)

class logger(object):
    """docstring for logger"""
    def __init__(self, path):
        self.path = path

    def write(self, log_obj):
        data = json.dumps(log_obj)
        with open(self.path, "a") as fp:
            fp.write(data+"\n")



pid = str(os.getpid())
pidfile = "1wire.pid"
file(pidfile, 'w').write(pid)

settings_obj = Settings("settings.json")
settings = settings_obj.get()
relay = W1Relay(settings["relay_1w_id"])
thermometer = W1Thermometer(settings["thermometer_1w_ip"])
logfile = logger("log.json")

while(True):
    now = datetime.now()
    (hour, minute) = (now.hour, now.minute)
    log = {}
    log["timestamp"] = now.isoformat()
    try:
        log["water_temp"] = thermometer.read_temp()
    except:
        log["water_temp"] = "n/a"
    relay_count = 0
    for relay_schedule in settings["relays"]:
        relay_on = relay.get_relay_status(relay_count)
        if hour in relay_schedule["on_hours"] and minute <= relay_schedule["duration"]:
            print relay_on
            if not relay_on:
                relay.on(relay_count)
        else:
            if relay_on:
                relay.off(relay_count)
        relay_count += 1
    log["relay_status"] = relay.read_status_int()
    logfile.write(log)
    time.sleep(settings["sleep_time"])
