# Copyright (C) 2020-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import logging
import subprocess
import time
import urllib

from iotlab_controller import common, nodes
from iotlab_controller.experiment.base import BaseExperiment, ExperimentError
from iotlab_controller.riot import RIOTFirmware

from .file_handler import DescriptionFileHandler, DescriptionError


logger = logging.getLogger(__name__)


class ExperimentRunner:
    def __init__(self, dispatcher, desc, exp_id=None, api=None):
        if api is None:
            self.api = common.get_default_api()
        else:
            self.api = api
        self.dispatcher = dispatcher
        self.desc = desc
        self._build_simple_params(exp_id)
        self._init_nodes()
        self._init_firmwares()
        self._init_profiles()
        self.experiment = self._init_experiment()

    @property
    def _firmwares(self):
        return self._exp_params['firmwares']

    @property
    def _sink_firmware(self):
        # can't use self.nodes here since experiment is not initialized yet
        if isinstance(self._exp_params['nodes'], nodes.SinkNetworkedNodes):
            return self.desc.get('sink_firmware')
        return None

    @property
    def exp_id(self):
        return self.experiment.exp_id

    @property
    def nodes(self):
        return self.experiment.nodes

    @property
    def results_dir(self):
        return self.desc.get('results_dir', '.')

    @property
    def runs(self):
        return self.desc.get('runs', [])

    def run_name(self, run):
        if '__timestamp__' not in run:
            run['__timestamp__'] = int(time.time())
        return run.get(
            'name',
            '{exp.exp_id}-{run[idx]}'
        ).format(exp=self.experiment, run=run, run_args=run.get('args', {}),
                 time=run['__timestamp__'])

    def _override_exp_params(self, key, value=None, default=None):
        if key in self._exp_params:
            logger.warning("'%s' from 'target_args' will be overwritten",
                           key)
        if value is None:
            value = self.desc.get(key, default)
        self._exp_params[key] = value

    def _override_env_params(self):
        if 'env' in self._exp_params and \
           isinstance(self._exp_params['env'], dict):
            logger.warning("'env' from 'target_args' may be partly "
                           "overwritten")
            self._exp_params['env'].update(self.desc.env)
        else:
            self._override_exp_params('env', self.desc.env)

    def _build_simple_params(self, exp_id=None):
        self._exp_params = self.desc.get('target_args', {})
        self._exp_params['api'] = self.api
        self._override_env_params()
        self._override_exp_params('ctx', {})
        self._override_exp_params('target', self.dispatcher.target)
        self._override_exp_params('name',
                                  default=self.dispatcher.DEFAULT_EXP_NAME)
        self._override_exp_params('runner', self)
        self._override_exp_params('exp_id', exp_id)

    def _init_network(self, network):
        if 'site' not in network:
            raise DescriptionError(f'Missing IoT-LAB site in {network}')
        kwargs = {'api': self.api, 'site': network['site']}
        if 'sink' in network:
            cls = nodes.SinkNetworkedNodes
            kwargs['sink'] = network['sink']
        else:
            cls = nodes.NetworkedNodes
        # network is either provided as a list of edges or a NetworkX edge
        # list file
        if 'edgelist' in network:
            res = cls(**kwargs)
            for edge in network['edgelist']:
                if not isinstance(edge, list) and len(edge) != 2:
                    raise DescriptionError(
                        f'Unrecognized edge {edge} in {network}'
                    )
                res.add_edge(edge[0], edge[1])
            return res
        if 'edgelist_file' in network:
            return cls(edgelist_file=network['edgelist_file'], **kwargs)
        raise DescriptionError('Missing edgelist in {nodes_desc}')

    def _init_nodes(self):
        nodes_desc = self.desc.get('nodes')
        if nodes_desc is None:
            raise DescriptionError(
                f'No nodes provided for {self.desc}'
            )
        if isinstance(nodes_desc, list):
            # two formats are allowed:
            # 1. - name: m3-1.grenoble.iot-lab.info
            #      role: forwarder
            # 2. - m3-1.grenoble.iot-lab.info
            try:
                self._exp_params['nodes'] = nodes.BaseNodes(
                    [n['name'] if isinstance(n, dict) else n
                     for n in nodes_desc],
                    api=self.api
                )
            except KeyError as exc:
                raise DescriptionError(
                    "As list, nodes must be represented as {'name': name, "
                    "'role': role} dictionary or just by their name as string"
                ) from exc
        elif isinstance(nodes_desc, dict) and 'network' in nodes_desc:
            self._exp_params['nodes'] = self._init_network(
                nodes_desc['network']
            )
        else:
            raise DescriptionError(
                f'Unrecognized nodes format in {nodes_desc}'
            )

    def _append_firmware(self, firmware_desc):
        env = self.desc.env
        env.update(firmware_desc.env)
        self._firmwares.append(self.init_firmware(firmware_desc, env))

    def _init_firmwares(self):
        self._exp_params['firmwares'] = []
        sink_firmware = self._sink_firmware
        firmwares = self.desc.get('firmwares', [])
        if not sink_firmware and not firmwares:
            return
        if sink_firmware and not firmwares:
            raise DescriptionError(
                f'sink_firmware but no firmwares for {self.desc}'
            )
        if sink_firmware:
            self._append_firmware(sink_firmware)
        for firmware in firmwares:
            self._append_firmware(firmware)
        # can't use self.nodes here since experiment is not initialized yet
        if len(self._firmwares) != len(self._exp_params['nodes']):
            if len(firmwares) == 1:
                while len(self._firmwares) < len(self._exp_params['nodes']):
                    # firmware was already build, so just append a copy of
                    # the last firmware without potential building
                    self._firmwares.append(self._firmwares[-1])
            else:
                raise DescriptionError(f'Not enough firmwares for all nodes '
                                       f'for {self.desc}')

    def _init_profiles(self):
        self._override_exp_params('profiles')

    def _init_experiment(self):
        return BaseExperiment(**self._exp_params)

    @staticmethod
    def init_firmware(firmware_desc, env):
        typ = firmware_desc.get('type', 'riot')
        if typ != 'riot':
            raise DescriptionError(
                'Unrecognized firmware type {typ}'
            )
        try:
            return RIOTFirmware(
                firmware_desc['path'],
                firmware_desc['board'],
                application_name=firmware_desc.get('name'),
                flashfile=firmware_desc.get('flashfile'),
                env=env
            )
        except KeyError as exc:
            raise DescriptionError(
                f'Missing firmware property {exc} in {firmware_desc}'
            ) from exc

    def reflash_firmwares(self, run, last_run):
        if run.get('rebuild') or (last_run and run.env != last_run.env):
            self.build_firmwares(build_env=run.env)
            if isinstance(self.nodes, nodes.SinkNetworkedNodes) and \
               len(self.experiment.firmwares) > 1 and \
               all(self.experiment.firmwares[1] == f
                   for f in self.experiment.firmwares[2:]):
                self.nodes.flash(
                    self.exp_id,
                    self.experiment.firmwares[1],
                    self.experiment.firmwares[0]
                )
            # all firmwares are the same
            elif all(self.experiment.firmwares[0] == f
                     for f in self.experiment.firmwares[1:]):
                self.nodes.flash(
                    self.exp_id,
                    self.experiment.firmwares[0]
                )
            else:
                # flash nodes one by one
                for i, node in enumerate(self.nodes):
                    node.flash(
                        self.exp_id,
                        self.experiment.firmwares[i]
                    )

    def build_firmwares(self, build_env=None):
        last_firmware = None
        for firmware in self._firmwares:
            if last_firmware != firmware:
                firmware.clean()
                firmware.build(build_env=build_env, threads='')
                last_firmware = firmware


class ExperimentDispatcher:
    _EXPERIMENT_RUNNER_CLASS = ExperimentRunner
    DEFAULT_EXP_DURATION = 20
    DEFAULT_EXP_NAME = 'iotlab-controller-dispatcher-experiment'

    def __init__(self, filename, api=None):
        if api is None:
            self.api = common.get_default_api()
        else:
            self.api = api
        self.runners = []
        self._file_handler = DescriptionFileHandler(filename)
        self.descs = {}

    def _pre_experiment(self, runner, ctx, *args, **kwargs):
        ctx.update(self.pre_experiment(runner, ctx, *args, **kwargs) or {})

    def pre_experiment(self, runner, ctx, *args, **kwargs):
        # pylint: disable=unused-argument
        return {}

    @staticmethod
    def _retry_http_error(func, *args, **kwargs):
        while True:
            try:
                func(*args, **kwargs)
                break
            except urllib.error.HTTPError:
                pass

    def target(self, exp, runner, ctx, *args, **kwargs):
        assert exp == runner.experiment
        self._pre_experiment(runner, ctx, *args, **kwargs)
        last_run_desc = None
        try:
            for idx, run_desc in enumerate(list(runner.runs)):
                if 'idx' not in run_desc:
                    run_desc['idx'] = idx
                else:
                    logger.warning(
                        'Setting idx=%s in run description %s may lead to '
                        'inconsistent lognames', run_desc['idx'], run_desc
                    )
                try:
                    self._retry_http_error(runner.reflash_firmwares, run_desc,
                                           last_run_desc)
                except subprocess.CalledProcessError:
                    run_desc["rebuild"] = True
                    raise
                last_run_desc = run_desc
                if run_desc.get('reset', True):
                    self._retry_http_error(exp.nodes.reset, exp.exp_id)
                self._pre_run(runner, run_desc, ctx, *args, **kwargs)
                try:
                    self.run(runner, run_desc, ctx, *args, **kwargs)
                finally:
                    self._post_run(runner, run_desc, ctx, *args, **kwargs)
        finally:
            self._post_experiment(runner, ctx, *args, **kwargs)

    def _post_experiment(self, runner, ctx, *args, **kwargs):
        self.post_experiment(runner, ctx, *args, **kwargs)

    def post_experiment(self, runner, ctx, *args, **kwargs):
        # pylint: disable=unused-argument
        pass

    def _pre_run(self, runner, run, ctx, *args, **kwargs):
        ctx.update(self.pre_run(runner, run, ctx, *args, **kwargs) or {})

    def pre_run(self, runner, run, ctx, *args, **kwargs):
        # pylint: disable=unused-argument
        return {}

    def run(self, runner, run, ctx, *args, **kwargs):
        # pylint: disable=unused-argument
        pass

    def _post_run(self, runner, run, ctx, *args, **kwargs):
        self.post_run(runner, run, ctx, *args, **kwargs)
        runner.runs.remove(run)
        runner.dispatcher.dump_experiment_descriptions()

    def post_run(self, runner, run, ctx, *args, **kwargs):
        # pylint: disable=unused-argument
        pass

    @property
    def filename(self):
        return self._file_handler.filename

    def num_experiments_to_run(self):
        diff = 0
        unscheduled = 0
        if 'globals' in self.descs:
            diff += 1
        if 'unscheduled' in self.descs:
            diff += 1
            unscheduled += len(self.descs['unscheduled'])
        return len(self.descs) + unscheduled - diff

    def has_experiments_to_run(self):
        return self.num_experiments_to_run() > 0

    def load_experiment_descriptions(self, schedule=True, run=True):
        # if run is True, schedule must be True as well
        assert not run or schedule
        self.descs = self._file_handler.load()
        if schedule:
            self.schedule_experiments()
            if run:
                self.run_experiments()

    def dump_experiment_descriptions(self):
        self._file_handler.dump(self.descs)

    def _schedule_unscheduled(self, unscheduled):
        runners = []
        # make unscheduled mutable during iteration
        for desc in list(unscheduled):
            duration = desc.get('duration', self.DEFAULT_EXP_DURATION)
            runner = self._EXPERIMENT_RUNNER_CLASS(self, desc, api=self.api)
            runner.build_firmwares()
            logger.info("Scheduling experiment '%s' with duration %s",
                        runner.experiment.name, duration)
            runner.experiment.schedule(duration)
            logger.info("Scheduled %d", runner.exp_id)
            self.descs["unscheduled"].remove(desc)
            self.descs[runner.exp_id] = desc
            runners.append(runner)
        del self.descs["unscheduled"]
        self.dump_experiment_descriptions()
        return runners

    def schedule_experiments(self):
        self.runners = []

        for key, desc in list(self.descs.items()):
            if key == 'globals':
                continue
            if key == 'unscheduled':
                self.runners.extend(self._schedule_unscheduled(desc))
            else:
                try:
                    logger.info(
                        "Trying to requeue experiment %s (%d)",
                        desc.get('name'), key
                    )
                    runner = self._EXPERIMENT_RUNNER_CLASS(self, desc,
                                                           exp_id=key,
                                                           api=self.api)
                    self.runners.append(runner)
                except ExperimentError as exc:
                    logger.error('Unable to requeue %d: %s', key, exc)
                    del self.descs[key]
                    self.dump_experiment_descriptions()
        self.runners.sort(key=lambda runner: runner.exp_id)

    def run_experiments(self):
        while self.has_experiments_to_run():
            if not self.runners:
                logger.warning('No runners available. Did you schedule?')
                self.descs.clear()
                self.dump_experiment_descriptions()
                break
            for runner in self.runners:
                exp_id = runner.exp_id
                logger.info('Waiting for experiment %d to start', exp_id)
                try:
                    runner.experiment.wait()
                except (ExperimentError, RuntimeError) as exc:
                    logger.error('Could not wait for experiment: %s', exc)
                else:
                    runner.experiment.run()
                del self.descs[exp_id]
                self.dump_experiment_descriptions()
