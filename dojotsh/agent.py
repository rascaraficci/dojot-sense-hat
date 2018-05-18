import time
import logging
import requests
import json
import paho.mqtt.client as mqtt
from sense_hat import SenseHat


class DojotAgent (object):

    def __init__(self, host, port, tenant, user, password, secure, interval):
        # set logger
        self._logger = logging.getLogger('raspberry-pi.dojot.agent')

        # keep connection parameters
        self._host = host
        self._port = port
        self._tenant = tenant
        self._user = user
        self._password = password
        self._secure = secure
        self._interval = interval

        # get raspberry pi serial number
        self._hw_serial = self._get_raspberry_pi_serial()

        # dojot jwt token
        self._logger.info("Getting JWT token ...")
        if self._secure:
            url = 'https://{}/auth'.format(self._host)
        else:
            url = 'http://{}:8000/auth'.format(self._host)
        data = {"username": "{}".format(self._user),
                "passwd": "{}".format(self._password)}
        response = requests.post(url=url, json=data)
        if response.status_code != 200:
            self._logger.error("HTTP POST to get JWT token failed (%s).",
                               response.status_code)
            raise Exception("HTTP POST failed {}.".
                            format(response.status_code))
        token = response.json()['jwt']
        self._auth_header = {"Authorization": "Bearer {}".format(token)}
        self._logger.info("Got JWT token %s", token)

        # dojot device ID
        self._device_id = self._has_dojot_been_set()

        # connect to dojot MQTT broker
        self._mqttc = mqtt.Client(self._hw_serial)
        self._mqttc.connect(host=host, port=port)
        self._mqttc.loop_start()

        # create template and device instances in dojot
        if self._device_id is None:
            self._set_raspeberry_pi_in_dojot()

        # register callbacks to handle actuation
        self._subscribe_to_mqtt_broker()

        # sense hat
        self._sense = SenseHat()

    def _get_raspberry_pi_serial(self):
        serial = "UNKNOWN000000000"
        try:
            f = open('/proc/cpuinfo', 'r')
            for line in f:
                if line[0:6] == 'Serial':
                    serial = line[10:26]
            f.close()
        except (OSError, IOError):
            self._logger.error("Cannot read /proc/cpuinfo")
            raise Exception("Cannot read /proc/cpuinfo")

        return serial

    def _has_dojot_been_set(self):
        # Check whether raspberry has been set in dojot
        if self._secure:
            url = 'https://{}/device'.format(self._host)
        else:
            url = 'http://{}:8000/device'.format(self._host)
        response = requests.get(url=url, headers=self._auth_header)
        if response.status_code != 200:
            raise Exception("HTTP POST failed {}.".
                            format(response.status_code))
        all_devices = list(response.json()['devices'])

        for dev in all_devices:
            if dev['label'] == 'Raspberry-Pi':
                return dev['id']

        return None

    def _set_raspeberry_pi_in_dojot(self):
        # create template
        self._logger.info("Creating raspberry-pi template in dojot ...")
        if self._secure:
            url = 'https://{}/template'.format(self._host)
        else:
            url = 'http://{}:8000/template'.format(self._host)
        data = {"label": "Raspberry-Pi-Sense-Hat",
                "attrs": [{"label": "protocol",
                           "type": "meta",
                           "value_type": "string",
                           "static_value": "mqtt"},
                          {"label": "temperature",
                           "type": "dynamic",
                           "value_type": "float"},
                          {"label": "humidity",
                           "type": "dynamic",
                           "value_type": "float"},
                          {"label": "pressure",
                           "type": "dynamic",
                           "value_type": "float"},
                          {"label": "message",
                           "type": "actuator",
                           "value_type": "string"},
                          {"label": "serial",
                           "type": "static",
                           "value_type": "string",
                           "static_value": "undefined"}
                          ]}
        response = requests.post(url=url, headers=self._auth_header, json=data)
        if response.status_code != 200:
            self._logger.error("HTTP POST to create template failed (%s).", 
                               response.status_code)
            raise Exception("HTTP POST failed {}.".
                            format(response.status_code))

        template_id = response.json()['template']['id']
        self._logger.info("Created template %s", template_id)

        # create device
        self._logger.info("Creating raspberry-pi device in dojot ...")
        if self._secure:
            url = 'https://{}/device'.format(self._host)
        else:
            url = 'http://{}:8000/device'.format(self._host)
        data = {"templates": ["{}".format(template_id)],
                "label": "Raspberry-Pi"}
        response = requests.post(url=url, headers=self._auth_header, json=data)
        if response.status_code != 200:
            self._logger.error("HTTP POST to create device failed (%s).", 
                               response.status_code)
            raise Exception("HTTP POST failed {}.".
                            format(response.status_code))

        self._device_id = response.json()['devices'][0]['id']
        self._logger.info("Created device %s", self._device_id)

        # set serial number
        if self._secure:
            url = 'https://{}/device/{}'.format(self._host, self._device_id)

        else:
            url = 'http://{}:8000/device/{}'.format(self._host, self._device_id)

        # Get
        response = requests.get(url=url, headers=self._auth_header)
        if response.status_code != 200:
            raise Exception("HTTP POST failed {}.".
                            format(response.status_code))
        data = response.json()
        attrs_static = []
        for attribute in data['attrs']["{}".format(template_id)]:
            if attribute['type'] == 'static':
                if attribute['label'] == 'serial':
                    attribute['static_value'] = self._hw_serial
                attrs_static.append(attribute)
        data['attrs'] = attrs_static

        # Put
        response = requests.put(url=url, headers=self._auth_header, json=data)
        if response.status_code != 200:
            raise Exception("HTTP POST failed {}.".
                            format(response.status_code))

    def _subscribe_to_mqtt_broker(self):
        # expected topic /<tenant>/<device_id>/config
        topic = "/{}/{}/config".format(self._tenant,
                                        self._device_id)
        self._logger.info("Subscribing to topic %s", topic)
        self._mqttc.subscribe(topic)
        self._mqttc.message_callback_add(topic, self._on_command)
        self._logger.info('Expecting command {{"attrs": {{"message": "<text>"}} }} in topic %s',
                          topic)

    def _on_command(self, _mqttc, _obj, msg):
        # expected command {"message": "<text>"}
        try:
            command = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            self._logger.error("Command is not coded as a JSON")
            return

        self._logger.info("Received command %s", command)
        if 'message' in command['attrs']:
            message = command['attrs']['message']
            self._logger.info("Writing message %s into the led matrix.", 
                              message)
            self._sense.clear()
            self._sense.show_message(message)
        else:
            self._logger.error("Unexpected command %s. Nothing will be done.", 
                               command)

    def _read_sensors(self):
        # temperature
        self._logger.info("Getting temperature ...")
        temperature = self._sense.temperature
        self._logger.info("Got temperature %s", temperature)

        # humidity
        self._logger.info("Getting humidity ...")
        humidity = self._sense.humidity
        self._logger.info("Got humidity %s", humidity)

        # pressure
        self._logger.info("Getting pressure ...")
        pressure = self._sense.pressure
        self._logger.info("Got pressure %s", pressure)

        return temperature, humidity, pressure

    def run(self):
        while True:
            temperature, humidity, pressure = self._read_sensors()
            data = {'temperature': temperature,
                    'humidity': humidity,
                    'pressure': pressure}
            # publish data
            self._logger.info("Publishing: %s", json.dumps(data))
            self._mqttc.publish("/{}/{}/attrs".format(self._tenant,
                                                      self._device_id),
                                json.dumps(data))

            time.sleep(self._interval)
