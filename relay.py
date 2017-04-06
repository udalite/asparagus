import RPi.GPIO as GPIO
from datetime import datetime
from datetime import timedelta
import logging


class Relay:
    def __init__(self, port_type, port_number):
        self.port = port_number
        self.port_type = port_type
        if port_type == 'gpio':
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
#           current_mode = GPIO.gpio_function(port_number)
#           if current_mode != GPIO.OUT:
            GPIO.setup(port_number, GPIO.OUT)
        else:
            raise NameError('Unsupported port_type %s' % port_type)

    def switch_status(self, status):
        GPIO.output(self.port, status)

    def get_status(self):
        status = GPIO.input(self.port)
        return status


class RelaySet:
    def __init__(self, settings):
        self.relay_list = []
        for relay in settings['relays']:
            relay['object'] = Relay(relay['type'], relay['port'])
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
                relay['object'].switch_status(scheduled_status)
