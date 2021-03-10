# Copyright (C) 2019-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.


class FirmwareBuildError(Exception):
    pass


class BaseFirmware:
    @property
    def path(self):
        raise NotImplementedError()

    def build(self):
        raise NotImplementedError()

    def clean(self):
        raise NotImplementedError()
