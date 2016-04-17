#!/usr/bin/env python

from distutils.core import setup

setup(
    name='supersonic-shiny-proton',
    version='0.0',
    description='',
    packages=['ssp'],
    entry_points={
        'console_scripts': [
            'ssp-asm=ssp.scripting.assembler.main:main',
            'ssp-server=ssp.server.main:main',
            'ssp-client=ssp.client.main:main',
            ],
        },
    )
