#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import os.path
import subprocess

from iotlab_controller import firmware


class RIOTFirmware(firmware.BaseFirmware):
    FILE_EXTENSION = "elf"

    def __init__(self, application_name, application_path, board,
                 flashfile=None, env=None):
        self.application_name = application_name
        self.application_path = application_path
        self.board = board
        self.flashfile = flashfile
        self.env = {"BOARD": board}
        if env is not None:
            self.env.update(env)

    @property
    def path(self):
        if self.flashfile is None:
            return os.path.join(self.application_path,
                                "bin", self.board,
                                "{}.{}".format(self.application_name,
                                               RIOTFirmware.FILE_EXTENSION))
        else:
            return self.flashfile

    def build(self, build_env=None, threads=1):
        env = self.env.copy()
        if build_env is not None:
            env.update(build_env)
        try:
            subprocess.run(["make", "-j", str(threads), "-C",
                           self.application_path, "all"],
                           env=env, check=True)
        except subprocess.CalledProcessError as e:
            raise firmware.FirmwareBuildError(e)

    def clean(self, build_env=None):
        env = self.env.copy()
        if build_env is not None:
            env.update(build_env)
        try:
            subprocess.run(["make", "-C", self.application_path, "clean"],
                           env=env, check=True)
        except subprocess.CalledProcessError as e:
            raise firmware.FirmwareBuildError(e)
