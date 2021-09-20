# Copyright (C) 2019-21 Freie Universität Berlin
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
    'm3-1.grenoble.iot-lab.info'
    """
    return f"{node}.{site}.{constants.IOTLAB_DOMAIN}"
