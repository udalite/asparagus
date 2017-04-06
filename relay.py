import RPi.GPIO as GPIO
from datetime import datetime
from datetime import timedelta
import logging
import subprocess
from subprocess import Popen

class Relay:
    def __init__(self, **relay_settings):
        port_type = relay_settings['type']
        if port_type == "gpio":
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
#           current_mode = GPIO.gpio_function(port_number)
#           if current_mode != GPIO.OUT:
            self.port_type = port_type
            self.port_number = relay_settings['port_number']
            GPIO.setup(self.port_number, GPIO.OUT)
        elif port_type == "w1":
            self.port_type = port_type
            self.w1_id = relay_settings["w1_id"]
            self.port_number = relay_settings['port_number']
            self.w1_path = "/sys/bus/w1/devices/%s/output" % self.w1_id
        else:
            raise NameError('Unsupported port_type %s' % self.port_type)

    def w1_read_status_int(self):
        if self.port_type == "w1":
            cmd = "dd if=%s bs=1 count=1 | hexdump" % self.w1_path
            process = Popen(cmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
            output = process.stdout.readline().strip()
            status_hex_str = output[-2:]
            if len(status_hex_str) == 0:
                return False
            else:
                status_int = int(status_hex_str, 16)
                return status_int

    def w1_write_status_int(self, new_status_int):
        if self.port_type == "w1":
            new_status_hex = hex(new_status_int)[1:]
            cmd = "echo -e \\\\%s | dd of=%s bs=1 count=1"\
                  % (new_status_hex, self.w1_path)
            Popen(cmd, shell=True, executable='/bin/bash',
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def set_status(self, status):
        if self.port_type == "gpio":
            GPIO.output(self.port, status)
        elif self.port_type == "w1":
            status_int = self.w1_read_status_int()
            if status == 1:
                new_status_int = status_int & ~(1 << self.port)
            elif status == 0:
                new_status_int = status_int | 1 << self.port
            self.w1_write_status_int(new_status_int)

    def get_status(self):
        if self.port_type == "gpio":
            status = GPIO.input(self.port)
        elif self.port_type == "w1":
            status_int = self.read_status_int()
            bit_mask = 1 << self.port
            status = (status_int & bit_mask == 0)
        return status


class RelaySet:
    def __init__(self, settings):
        self.relay_list = []
        for relay in settings['relays']:
            relay['object'] = Relay(relay)
            self.relay_list.append(relay)

    @staticmethod
    def gen_cycles(schedule):
        for cycle_start in schedule:
            now_dt = datetime.now()
            cycle_start_dt = datetime.strptime(cycle_start, '%H.%M')
            cycle_start_dt = cycle_start_dt.replace(year=now_dt.year)
            cycle_start_dt = cycle_start_dt.replace(month=now_dt.month)
            cycle_start_dt = cycle_start_dt.replace(day=now_dt.day)
            if cycle_start_dt > now_dt:
                cycle_start_dt += timedelta(days=-1)
            duration = schedule[cycle_start]
            cycle_end_dt = cycle_start_dt + timedelta(minutes=duration)
            yield (cycle_start_dt, cycle_end_dt)

    @staticmethod
    def get_scheduled_status(schedule):
        scheduled_status = GPIO.LOW
        now_dt = datetime.now()
        for cycle in RelaySet.gen_cycles(schedule):
            print(cycle)
            if cycle[0] < now_dt < cycle[1]:
                scheduled_status = GPIO.HIGH
        return scheduled_status

    def actualize(self):
        for relay in self.relay_list:
            scheduled_status = self.get_scheduled_status(relay['schedule'])
            current_status = relay['object'].get_status()
            msg = "Current_status %s" % current_status
            print(msg)
            logging.info(msg)
            if current_status != scheduled_status:
                msg = "Switching to %s" % scheduled_status
                print(msg)
                logging.info(msg)
                relay['object'].set_status(scheduled_status)
