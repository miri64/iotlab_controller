# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import iotlab_controller.constants


def test_iotlab_domain():
    assert hasattr(iotlab_controller.constants, 'IOTLAB_DOMAIN')
