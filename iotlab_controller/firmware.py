#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# Distributed under terms of the MIT license.


class FirmwareBuildError(Exception):
    pass


class BaseFirmware(object):
    @property
    def path(self):
        raise NotImplementedError()

    def build(self):
        raise NotImplementedError()

    def clean(self):
        raise NotImplementedError()
