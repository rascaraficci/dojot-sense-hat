# Dojot Sense Hat Agent
It integrates raspberry pi/sense hat with dojot IoT platform.

The sensors are read periodically and their values are published through MQTT protocol to dojot.

You can also send a message to be shown on the sense hat display, publishing to MQTT topic
```\<tenant>\<device_id>\config``` with payload ```{"attrs": {"message": "<text>"}}```.

# Installation
To install into raspberry pi run:

```
$ apt-get install sense-hat
$ git clone https://github.com/rascaraficci/dojot-sense-hat.git
$ cd dojot-sense-hat
$ pip3 install -r requirements.txt
```

I advise you install *sense-hat* through *apt-get* instead of *pip* in order to avoid some dependency problems.

# Usage
```
$ python3 -m dojotsh.main -h
Usage: main.py [options]

Options:
  -h, --help            show this help message and exit
  -H HOST, --host=HOST  MQTT host to connect. Defaults to localhost.
  -P PORT, --port=PORT  MQTT port to connect to. Defaults to 1883.
  -t TENANT, --tenant=TENANT
                        Tenant identifier in dojot. Defaults to admin.
  -u USER, --user=USER  User identifier in dojot. Defaults to admin.
  -p PASSWORD, --password=PASSWORD
                        User password in dojot. Defaults to admin.
  -i INTERVAL, --interval=INTERVAL
                        Polling interval in seconds. Defaults to 15.
```