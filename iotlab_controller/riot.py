#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019-2020 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import os
import subprocess

from iotlab_controller import firmware


class RIOTFirmware(firmware.BaseFirmware):
    FILE_EXTENSION = "elf"

    def __init__(self, application_path, board, application_name=None,
                 flashfile=None, env=None):
        self.application_path = application_path
        self.board = board
        self.flashfile = flashfile
        if application_name is None:
            if application_path.endswith("/"):
                application_path = application_path[:1]
            self.application_name = os.path.basename(application_path)
        else:
            self.application_name = application_name
        self.env = os.environ.copy()
        self.env["BOARD"] = board
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

    def _run(self, build_env, cmd):
        env = self.env.copy()
        if build_env is not None:
            env.update(build_env)
        try:
            subprocess.run(cmd, env=env, check=True)
        except subprocess.CalledProcessError as e:
            raise firmware.FirmwareBuildError(e)

    def build(self, build_env=None, threads=1):
        self._run(build_env, ["make", "-j", str(threads), "-C",
                             self.application_path, "all"])

    def clean(self, build_env=None):
        self._run(build_env, ["make", "-C", self.application_path, "clean"])

    def distclean(application_path):
        try:
            subprocess.run(["make", "-C", application_path, "distclean"], check=True)
        except subprocess.CalledProcessError as e:
            raise firmware.FirmwareBuildError(e)
