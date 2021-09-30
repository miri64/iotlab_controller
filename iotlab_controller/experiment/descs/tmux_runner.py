# Copyright (C) 2020-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import logging
import os
import time


from iotlab_controller.experiment.base import BaseExperiment
from iotlab_controller.experiment.tmux import TmuxExperiment

from .runner import ExperimentRunner, ExperimentDispatcher
from .file_handler import DescriptionError


logger = logging.getLogger(__name__)


class TmuxExperimentRunner(ExperimentRunner):
    @property
    def tmux_session(self):
        return self.experiment.tmux_session

    def get_tmux(self, key, default=None):
        return self.desc.get('tmux', {}).get(
            key, self.dispatcher.descs.get('globals', {}).get(
                'tmux', {}
            ).get(key, default)
        )

    def get_tmux_cmds(self, run):
        res = run.get('tmux_cmds', self.get_tmux('cmds', []))
        if len(res) == 0:
            logger.warning('No commands provided in %s', run)
        return res

    def ensure_tmux_session(self):
        cwd = self.get_tmux('cwd')
        tmux_target = self.get_tmux('target')
        session = self._parse_tmux_target(tmux_target)

        if not self.tmux_session:
            logger.info("Starting TMUX session in %s%s",
                        tmux_target or self.experiment.name,
                        '' if cwd is None else f' {cwd}')
            self.experiment.initialize_tmux_session(cwd=cwd, **session)
        elif cwd is not None:
            logger.info("Changing to %s in TMUX session %s", cwd,
                        tmux_target or self.experiment.name)
            self.experiment.cmd(f'cd {cwd}')

    def _init_experiment(self):
        if 'tmux' in self.desc:
            return TmuxExperiment(**self._exp_params)
        return BaseExperiment(**self._exp_params)

    def _parse_tmux_target(self, tmux_target):
        res = {}
        if tmux_target is None:
            res["session_name"] = self.experiment.name
        else:
            session_window = tmux_target.split(":")
            res["session_name"] = session_window[0]
            if len(session_window) > 1:
                window_pane = (":".join(session_window[1:])).split(".")
                res["window_name"] = window_pane[0]
                if len(window_pane) > 1:
                    res["pane_id"] = ".".join(window_pane[1:])
        return res


class TmuxExperimentDispatcher(ExperimentDispatcher):
    _EXPERIMENT_RUNNER_CLASS = TmuxExperimentRunner

    def _pre_run(self, runner, run, ctx, *args, **kwargs):
        if isinstance(runner.experiment, TmuxExperiment):
            runner.ensure_tmux_session()
            run_name = runner.run_name(run)
            ctx['logname'] = os.path.join(runner.desc.get('results_dir', '.'),
                                          f'{run_name}.log')
        super()._pre_run(runner, run, ctx, *args, **kwargs)

    def run(self, runner, run, ctx, *args, **kwargs):
        # pylint: disable=unused-argument
        run_name = runner.run_name(run)
        if not isinstance(runner.experiment, TmuxExperiment):
            logger.error('%s: %s is not a TMUX experiment', run_name,
                         runner.experiment)
            super().run(runner, run, ctx, *args, **kwargs)
            return
        wait = run.get('wait')
        if wait is None:
            raise DescriptionError(
                "'wait' for run or 'run_wait' in experiment description "
                "required"
            )
        if hasattr(runner.experiment.nodes, 'site'):
            site = runner.experiment.nodes.site
        else:
            site = run.get('site')
        if site is None:
            logger.warning('No IoT-LAB site provided to run TMUX commands. '
                           'Will assume we run on IoT-LAB frontend.')
        with_a8 = any(f.board == 'iotlab-a8-m3'
                      for f in runner.experiment.firmwares)
        color = bool(run.get('serial_aggregator_color'))
        logname = ctx['logname']
        runner.experiment.cmd(f'echo "Starting run {run_name}" >> {logname}')
        nodes = ctx.get('nodes')
        with runner.experiment.serial_aggregator(site=site, with_a8=with_a8,
                                                 color=color, logname=logname,
                                                 nodes=nodes):
            if runner.get_tmux_cmds(run):
                for cmd in runner.get_tmux_cmds(run):
                    runner.experiment.cmd(cmd.format(
                        runner=runner, run=run, ctx=ctx,
                        run_args=run.get('args'), **kwargs
                    ), wait_after=.1)
                until = time.asctime(time.localtime(time.time() + wait))
                logger.info('Waiting for %ss for run %s (until %s) to '
                            'finish', wait, run_name, until)
                time.sleep(wait)
            else:
                super().run(runner, run, ctx, *args, **kwargs)
