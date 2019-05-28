# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import iotlabcli.auth
import iotlabcli.experiment

from iotlab_controller import common


class ExperimentError(Exception):
    pass


class BaseExperiment(object):
    def __init__(self, name, nodes, target, firmwares=None, exp_id=None,
                 profiles=None, api=None, *args, **kwargs):
        if (firmwares is not None) and \
           ((len(firmwares) > 1) or (len(nodes) != len(firmwares))):
            raise ExperimentError(
                "firmwares must be of length one or "
                "the multiplicity of nodes"
            )
        if (profiles is not None) and \
           ((len(profiles) > 1) or (len(nodes) != len(profiles))):
            raise ExperimentError(
                "profiles must be of length one or  "
                "the multiplicity of nodes"
            )
        username, _ = iotlabcli.auth.get_user_credentials()
        self.name = name
        self.nodes = nodes
        self.firmwares = firmwares
        self.profiles = profiles
        self.username = username
        self.target = target
        self.target_args = args
        self.target_kwargs = kwargs
        if api is None:
            self.api = common.get_default_api()
        else:
            self.api = api
        self.exp_id = exp_id
        if self.is_scheduled():
            self._check_experiment()

    def __str__(self):
        if self.is_scheduled():
            return "<{}: {} ({})>".format(type(self).__name__, self.name,
                                          self.exp_id)
        return "<{}: {} (unscheduled>)".format(type(self).__name__,
                                               self.name)

    def _check_experiment(self):
        exp = iotlabcli.experiment.get_experiment(self.api, self.exp_id)
        if exp["state"] in ["Error", "Terminated", "Stopped"]:
            raise ExperimentError(
                "{} terminated or had an error".format(self)
            )
        not_in_exp = []
        for node in self.nodes:
            if node.uri not in exp["nodes"]:
                not_in_exp.append(node.uri)
        if not_in_exp:
            error_msg = "The following nodes are not part of " \
                        "experiment {}:\n".format(self.exp_id)
            error_msg += "\n".join(["* {}".format(node)
                                    for node in self.nodes])
            raise ExperimentError(error_msg)

    def _get_resources(self):
        if (len(self.firmwares) == 1) and (len(self.profiles) == 1):
            return [
                iotlabcli.experiment.exp_resources(
                    [node.uri for node in self.nodes],
                    self.firmwares[0].path, self.profiles[0]
                )
            ]
        else:
            firmwares = self.firmwares
            profiles = self.profiles
            if len(firmwares) == 1:
                firmwares *= len(self.nodes)
            if len(profiles) == 1:
                profiles *= len(self.nodes)
            return [
                iotlabcli.experiment.exp_resource(x[0].uri, x[1].path, x[2])
                for x in zip(self.nodes, firmwares, profiles)
            ]

    def is_scheduled(self):
        return self.exp_id is not None

    def schedule(self, duration, start_time=None):
        if self.is_scheduled():
            raise ExperimentError("{} already scheduled".format(self))
        if start_time is not None:
            start_time = int(start_time.timestamp())
        resources = self._get_resources()
        self.exp_id = iotlabcli.experiment.submit_experiment(
            self.api, self.name, duration, resources, start_time
        )["id"]

    def stop(self):
        if self.is_scheduled():
            iotlabcli.experiment.stop_experiment(self.api, self.exp_id)

    def wait(self, states="Running", timeout=float("+inf")):
        if self.is_scheduled():
            iotlabcli.experiment.wait_experiment(self.api, self.exp_id,
                                                 states=states,
                                                 timeout=timeout)
        else:
            raise ExperimentError("{} is not scheduled".format(self))

    def run(self):
        if self.is_scheduled():
            if self.target:
                self.target(self, *self.target_args, **self.target_kwargs)
        else:
            raise ExperimentError("{} is not scheduled".format(self))
