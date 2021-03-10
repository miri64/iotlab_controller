# Copyright (C) 2019-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import abc


class FirmwareBuildError(Exception):
    pass


class BaseFirmware(abc.ABC):
    @property
    @abc.abstractmethod
    def path(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def build(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def clean(self):
        raise NotImplementedError()
