#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Martine Lenders <m.lenders@fu-berlin.de>
#
# Distributed under terms of the MIT license.

import logging
import subprocess
import time

import libtmux

from ..constants import IOTLAB_DOMAIN
from ..experiment import base


class TmuxExperiment(base.BaseExperiment):
    def __init__(self, name, nodes, *args, target=None, firmwares=None,
                 exp_id=None, profiles=None, api=None, **kwargs):
        super().__init__(name=name, nodes=nodes, target=target,
                         firmwares=firmwares, exp_id=exp_id, profiles=profiles,
                         api=api, *args, **kwargs)
        self.tmux_server = libtmux.Server()
        self.tmux_session = None

    def _create_tmux_session(self, session_name, window_name=None,
                             cwd=None):
        cmd = ["tmux", "new-session", "-d", "-s", session_name]
        if window_name is not None:
            cmd.extend(["-n", window_name])
        if cwd is not None:
            cmd.extend(["-c", cwd])
        subprocess.run(cmd, check=True)
        self.tmux_server = libtmux.Server()
        return self.tmux_server.find_where({"session_name": session_name})

    def _find_or_create_tmux_session(self, session_name, search_params,
                                     window_name=None, cwd=None):
        while self.tmux_session is None:
            try:
                self.tmux_session = self.tmux_server.find_where(
                    search_params
                )
            except libtmux.exc.LibTmuxException:
                self.tmux_session = self._create_tmux_session(session_name,
                                                              window_name,
                                                              cwd)
            if self.tmux_session is None:
                self.tmux_session = self._create_tmux_session(session_name,
                                                              window_name,
                                                              cwd)

    def initialize_tmux_session(self, session_name, window_name=None,
                                pane_id=None, cwd=None, env=None):
        # pylint: disable=too-many-arguments
        # Maybe fix later
        if self.tmux_session is None:
            # find pane
            search_params = {
                "session_name": session_name,
            }
            if window_name is not None:
                search_params["window_name"] = window_name
            if pane_id is not None:
                search_params["pane_id"] = pane_id

            self._find_or_create_tmux_session(session_name, search_params,
                                              window_name=window_name, cwd=cwd)
            # set environment
            if env is not None:
                for key, value in env.items():
                    self.tmux_session.set_environment(key, value)
            # find pane
            if window_name is not None:
                self.tmux_session = self.tmux_session.find_where(search_params)
            else:
                self.tmux_session = self.tmux_session.select_window(0)
            if pane_id is not None:
                self.tmux_session = self.tmux_session.find_where(search_params)
            else:
                self.tmux_session = self.tmux_session.select_pane(0)
        return self.tmux_session

    def start_serial_aggregator(self, site=None, with_a8=False, color=False,
                                logname=None):
        self.hit_ctrl_c()
        time.sleep(.1)
        self.send_keys("reset", enter=True)
        if site is not None:
            ssh = "ssh {}@{}.{} ".format(self.username, site, IOTLAB_DOMAIN)
        else:
            logging.warning("Assuming to run on SSH frontend")
            logging.warning("\tadd `site` parameter to "
                            "`start_serial_aggregator()` to prevent")
            ssh = ""
        if with_a8:
            with_a8 = " --with-a8"
        else:
            with_a8 = ""
        if color:
            color = " --color"
        else:
            color = ""
        cmd = "{}serial_aggregator -i {}{}{}".format(
                ssh, self.exp_id, with_a8, color
            )
        if logname is not None:
            cmd += "| tee -a {}".format(logname)
        self.send_keys(cmd, enter=True, wait_after=2)

    def stop_serial_aggregator(self):
        self.hit_ctrl_c()

    def send_keys(self, keys, enter=False, wait_after=0):
        assert self.tmux_session is not None
        self.tmux_session.send_keys(keys, enter=enter, suppress_history=False)
        if wait_after > 0:
            time.sleep(wait_after)

    def cmd(self, cmd, wait_after=0):
        self.send_keys(cmd, enter=True, wait_after=wait_after)

    def hit_ctrl_c(self):
        self.send_keys("C-c")

    def hit_ctrl_d(self):
        self.send_keys("C-d")

    def hit_enter(self):
        assert self.tmux_session is not None
        self.tmux_session.enter()
