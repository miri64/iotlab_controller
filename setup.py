#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

from setuptools import setup, find_packages
import os
import sys

name = "iotlab_controller"
version = "0.4.2a"
description = "Python-based controller for IoT-LAB experiments"
author = "Martine Lenders"
author_email = "m.lenders@fu-berlin.de"
url = "https://github.com/miri64/iotlab_controller"

def get_requirements():
    with open(os.path.join(os.path.dirname(sys.argv[0]),
                           "requirements.txt")) as req_file:
        for line in req_file:
            yield line.strip()

extras_require = {
    "networked": ["networkx>=2.2"],
    "tmux": ["libtmux"],
    "all": []
}

for k, v in extras_require.items():
    if k.startswith("k") or (k in ["all"]):
        continue
    extras_require["all"].extend(v)

setup(
    name=name,
    version=version,
    description=description,
    packages=find_packages(),

    author=author,
    author_email=author_email,
    url=url,

    keywords=["iotlab", "iot", "experimentation"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audionce :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],

    install_requires=list(get_requirements()),
    extras_require=extras_require,
    python_requires=">=3.4",
)
