import datetime
import time
from relay import RelaySet
import yaml
import logging
import os
from picamera import PiCamera
from YaDiskClient.YaDiskClient import YaDisk
from PIL import Image

CONF_FILE = '/opt/asparagus/config.yml'

with open(CONF_FILE) as fp:
    sett = yaml.load(fp)
print(sett)


def make_photo():
    try:
        fname = "%s.jpg" % str(datetime.datetime.now())
        path = os.path.join(sett['photos_path'], fname)
        with open(path, 'wb') as fp:
            camera.capture(fp)
        logging.info('Captured photo %s' % fname)
        return path
    except:
        return False


def rotate_photo(path):
    img = Image.open(path)
    img = img.rotate(180)
    img.save(path, quality=80, optimize=True, progressive=True)


# Set up logging
logging.basicConfig(filename=sett['logfile'], level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S')
logging.info('Grow worker started')

# Save PID to pid file
pid = str(os.getpid())
logging.info("PID is {}".format(pid))
if sett['pidfile']:
    with open(sett['pidfile'], "w") as f:
        f.write(pid)

# Set up relays
rs = RelaySet(sett)

# Set up camera
camera = PiCamera(resolution=(2592, 1944))
time.sleep(2)

# Set Up YaDisk webdav
disk = YaDisk(sett['yandex']['login'], sett['yandex']['pass'])

while True:
    rs.actualize()
    photo_path = make_photo()
    photo_name = photo_path.split("/")[-1]
    ya_path = "asparagus/%s" % photo_name
    if photo_path:
        try:
            rotate_photo(photo_path)
            disk.upload(photo_path, ya_path)
        except:
            logging.info('Could not upload photo')
            pass
    else:
        logging.info('Could not capture photo')
    time.sleep(300)
