#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Martine Lenders <m.lenders@fu-berlin.de>
#
# Distributed under terms of the MIT license.

import libtmux
import logging
import subprocess
import time

from ..constants import IOTLAB_DOMAIN
from ..experiment import base

class TmuxExperiment(base.BaseExperiment):
    def __init__(self, name, nodes,
                 session_name, window_name=None, pane_id=None, cwd=None,
                 env=None,
                 firmwares=None, exp_id=None, profiles=None,
                 api=None, *args, **kwargs):
        super().__init__(name, nodes, firmwares=firmwares, exp_id=exp_id,
                         profiles=profiles, api=api, *args, **kwargs)
        self.tmux_server = libtmux.Server()
        self.tmux_session = None
        self.session_name = session_name
        self.window_name = window_name
        self.pane_id = pane_id
        self.cwd = cwd
        self.env = env

    def _create_tmux_session(self):
        cmd = ["tmux", "new-session", "-d", "-s", self.session_name]
        if self.window_name is not None:
            cmd.extend(["-n", self.window_name])
        if self.cwd is not None:
            cmd.extend(["-c", self.cwd])
        subprocess.run(cmd)
        self.tmux_server = libtmux.Server()
        return self.tmux_server.find_where({"session_name": self.session_name})

    def run(self, site, logname=None):
        if type(self.tmux_session) is not libtmux.Pane:
            # find pane
            search_params = {
                "session_name": self.session_name,
            }
            if self.window_name is not None:
                search_params["window_name"] = self.window_name
            if self.pane_id is not None:
                search_params["pane_id"] = self.pane_id

            # find or create TMUX session
            while self.tmux_session is None:
                try:
                    self.tmux_session = self.tmux_server.find_where(search_params)
                except libtmux.exc.LibTmuxException:
                    self.tmux_session = self._create_tmux_session()
                if self.tmux_session is None:
                    self.tmux_session = self._create_tmux_session()
            # set environment
            if self.env is not None:
                for k, v in self.env.items():
                    self.tmux_session.set_environment(k, v)
            # find pane
            if self.window_name is not None:
                self.tmux_session = self.tmux_session.find_where(search_params)
            else:
                self.tmux_session = self.tmux_session.select_window(0)
            if self.pane_id is not None:
                self.tmux_session = self.tmux_session.find_where(search_params)
            else:
                self.tmux_session = self.tmux_session.select_pane(0)
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
        cmd = "{}serial_aggregator -i {}{}{}".format(
                ssh, self.exp_id
            )
        if logname is not None:
            cmd += "| tee -a {}".format(logname)
        self.send_keys(cmd, enter=True)

    def send_keys(self, keys, enter=False, wait_after=0):
        assert self.tmux_session is not None
        self.tmux_session.send_keys(keys, enter=enter, suppress_history=False)
        if wait_after > 0:
            time.sleep(wait_after)

    def cmd(self, cmd, wait_after=0):
        self.send_keys(cmd, enter=True, wait_after=wait_after)

    def hit_ctrl_c(self):
        self.send_keys("C-c")

    def hit_enter(self):
        assert self.tmux_session is not None
        self.tmux_session.enter()

