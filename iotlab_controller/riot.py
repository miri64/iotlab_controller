# Copyright (C) 2019-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import os
import subprocess

from iotlab_controller import firmware


class RIOTFirmware(firmware.BaseFirmware):
    FILE_EXTENSION = "elf"

    def __init__(self, application_path, board, application_name=None,
                 flashfile=None, env=None):
        # pylint: disable=too-many-arguments
        # Maybe fixed later
        self.application_path = application_path
        self.flashfile = flashfile
        if application_name is None:
            if application_path.endswith("/"):
                application_path = application_path[:-1]
            self.application_name = os.path.basename(application_path)
        else:
            self.application_name = application_name
        self.env = os.environ.copy()
        self.env["BOARD"] = board
        if env is not None:
            self.env.update(env)

    def __repr__(self):
        return f"<{type(self).__name__} at {self.application_name}>"

    def __eq__(self, other):
        return isinstance(other, RIOTFirmware) and \
               self.application_path == other.application_path and \
               self.application_name == other.application_name and \
               self.flashfile == other.flashfile and \
               self.env == other.env

    @property
    def board(self):
        return self.env['BOARD']

    @property
    def path(self):
        if self.flashfile is None:
            return os.path.join(self.application_path,
                                "bin", self.board,
                                f"{self.application_name}."
                                f"{RIOTFirmware.FILE_EXTENSION}")
        return self.flashfile

    def _run(self, build_env, cmd):
        env = self.env.copy()
        if build_env is not None:
            env.update(build_env)
        try:
            subprocess.run(cmd, env=env, check=True)
        except subprocess.CalledProcessError as exc:
            raise firmware.FirmwareBuildError(exc)

    def build(self, build_env=None, threads=1):
        # pylint: disable=arguments-differ
        # Adds additional, but optional arguments
        cmd = ['make', "-C", self.application_path, "all"]
        if not threads:
            cmd.append('-j')
        else:
            cmd.extend(['-j', str(threads)])
        self._run(build_env, cmd)

    def clean(self, build_env=None):
        # pylint: disable=arguments-differ
        # Adds additional, but optional arguments
        self._run(build_env, ["make", "-C", self.application_path, "clean"])

    @staticmethod
    def distclean(application_path):
        try:
            subprocess.run(["make", "-C", application_path, "distclean"],
                           check=True)
        except subprocess.CalledProcessError as exc:
            raise firmware.FirmwareBuildError(exc)
