#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import iotlabcli.auth
import iotlabcli.rest

from iotlab_controller import constants


def get_default_api():
    return iotlabcli.rest.Api(*iotlabcli.auth.get_user_credentials())

def get_uri(site, node):
    """
    >>> get_uri("grenoble", "m3-1")
    m3-1.grenoble.iot-lab.info
    """
    return "{}.{}.{}".format(node, site, constants.IOTLAB_DOMAIN)
