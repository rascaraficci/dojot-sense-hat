# -*- coding: utf-8 -*-
# https://pythonhosted.org/versiontools/usage.html
from setuptools import setup, find_packages


setup(
    name="dojot-sense-hat",
    description='Integration of raspberry pi sense hat with dojot platform.',
    version='1.0.0',

    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'paho-mqtt',
        'requests',
        'sense_hat'
    ],
    python_requires='>=3.0.0',
    author='Rafael Augusto Scaraficci',
    author_email='raugusto@cpqd.com.br',
    url='https://github.com/rascaraficci/dojot-sense-hat',
)
