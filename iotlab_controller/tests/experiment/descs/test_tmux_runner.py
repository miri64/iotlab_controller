# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.
# pylint: disable=redefined-outer-name
# pylint gets confused by fixture base_node

import logging

import pytest

from iotlab_controller.experiment.base import BaseExperiment
from iotlab_controller.experiment.tmux import TmuxExperiment

from iotlab_controller.experiment.descs import tmux_runner
# needed for api_mock
from iotlab_controller.tests.test_nodes import \
        networked_nodes_base    # noqa: F401

# importing fixture to be used with tests, for flake8 this is confusing
from test_runner import api_mock, descs             # noqa: F401


@pytest.fixture
def tmux_exp_runner(mocker, descs, api_mock):       # noqa: F811
    dispatcher = mocker.Mock()
    dispatcher.descs = descs
    key = [k for k in descs if isinstance(k, int)][0]
    yield tmux_runner.TmuxExperimentRunner(dispatcher, descs[key],
                                           api=api_mock)


@pytest.fixture
def tmux_exp_dispatcher(descs, mocker, api_mock):   # noqa: F811
    mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.load',
        return_value=descs
    )
    disp = tmux_runner.TmuxExperimentDispatcher('test.yaml', api=api_mock)
    disp.load_experiment_descriptions(True, False)
    yield disp


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
                1337: {'nodes': ['m3-1.grenoble.iot-lab.info']},
            },
            id='without tmux config'
        ),
        pytest.param({
                'globals': {'tmux': {'test': 'foobar'}},
                1337: {'nodes': ['m3-1.grenoble.iot-lab.info']},
            },
            id='without target'
        ),
        pytest.param({
                'globals': {'tmux': {'target': 'foobar'}},
                1337: {'nodes': ['m3-1.grenoble.iot-lab.info']},
            },
            id='with target'
        ),
    ], indirect=['descs']
)
def test_tmux_exp_runner_init(mocker, api_mock, descs):   # noqa: F811
    dispatcher = mocker.Mock()
    runner = tmux_runner.TmuxExperimentRunner(dispatcher, descs[1337],
                                              api=api_mock)
    assert runner.exp_id is None
    assert len(runner.nodes) == 1
    assert 'm3-1.grenoble.iot-lab.info' in runner.nodes
    assert not runner.exp_id == 1337
    if 'tmux' in descs[1337]:
        assert isinstance(runner.experiment, TmuxExperiment)
        assert runner.tmux_session == runner.experiment.tmux_session
    else:
        assert isinstance(runner.experiment, BaseExperiment)
    assert not runner.experiment.firmwares


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
            'globals': {'tmux': {'target': 'snafu'}},
            1337: {
                'tmux': {'foobar': 12345},
                'nodes': ['m3-1.grenoble.iot-lab.info']
            },
        }),
    ], indirect=['descs']
)
def test_tmux_exp_runner_get_tmux(tmux_exp_runner):
    assert tmux_exp_runner.get_tmux('target') == 'snafu'
    assert tmux_exp_runner.get_tmux('foobar') == 12345
    assert tmux_exp_runner.get_tmux('not there', 1337) == 1337


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
            'globals': {'tmux': {'target': 'snafu', 'cmds': [
                'abcd',
                'efgh',
            ]}},
            1337: {
                'tmux': {'foobar': 12345},
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'runs': [{}]
            },
        }, id="from enclosure"),
        pytest.param({
            'globals': {'tmux': {'target': 'snafu'}},
            1337: {
                'tmux': {'foobar': 12345},
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'runs': [{'tmux_cmds': [
                    'abcd',
                    'efgh',
                ]}]
            },
        }, id="from run"),
    ], indirect=['descs']
)
def test_tmux_exp_runner_get_tmux_cmds(tmux_exp_runner):
    assert tmux_exp_runner.get_tmux_cmds(
        tmux_exp_runner.runs[0]
    ) == ['abcd', 'efgh']


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
            'globals': {'tmux': {'target': 'snafu', 'cmds': []}},
            1337: {
                'tmux': {'foobar': 12345},
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'runs': [{'name': 'test'}]
            },
        }, id="from enclosure"),
    ], indirect=['descs']
)
def test_tmux_exp_runner_get_tmux_cmds_no_cmds(caplog, tmux_exp_runner):
    with caplog.at_level(logging.WARNING):
        assert tmux_exp_runner.get_tmux_cmds(
            tmux_exp_runner.runs[0]
        ) == []
    assert "No commands provided in {'name': 'test'}" in \
        [r.message for r in caplog.records]


@pytest.mark.parametrize(
    'tmux_target, descs', [
        pytest.param('foobar', {
            'globals': {'tmux': {'not_target': 'snafu'}},
            1337: {
                'name': 'foobar',
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
        }, id='foobar'),
        pytest.param('snafu', {
            'globals': {'tmux': {'target': 'snafu'}},
            1337: {
                'name': 'foobar',
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
        }, id='snafu'),
        pytest.param('snafu:win', {
            'globals': {'tmux': {'target': 'snafu:win'}},
            1337: {
                'name': 'foobar',
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
        }, id='snafu:win'),
        pytest.param('snafu:win.0', {
            'globals': {'tmux': {'target': 'snafu:win.0'}},
            1337: {
                'name': 'foobar',
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
        }, id='snafu:win.0'),
    ], indirect=['descs']
)
def test_tmux_exp_runner_ensure_tmux_session_without_cwd(caplog, mocker,
                                                         tmux_target,
                                                         tmux_exp_runner):
    tmux_session_mock = mocker.Mock()

    def init_tmux_session_mock(*args, **kwargs):
        # pylint: disable=unused-argument
        tmux_exp_runner.experiment.tmux_session = tmux_session_mock

    tmux_exp_runner.experiment.initialize_tmux_session = init_tmux_session_mock
    tmux_cmd = tmux_exp_runner.experiment.cmd = mocker.Mock()
    with caplog.at_level(logging.INFO):
        tmux_exp_runner.ensure_tmux_session()
    assert f'Starting TMUX session in {tmux_target}' in \
        [r.message for r in caplog.records]
    assert tmux_exp_runner.tmux_session == tmux_session_mock
    caplog.clear()
    # second call should just change the cwd
    with caplog.at_level(logging.INFO):
        tmux_exp_runner.ensure_tmux_session()
    assert not caplog.records
    assert tmux_exp_runner.tmux_session == tmux_session_mock
    tmux_cmd.assert_not_called()


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
            'globals': {'tmux': {'target': 'snafu', 'cwd': './abcd'}},
            1337: {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
        }, id='target provided'),
        pytest.param({
            'globals': {'tmux': {'not_target': 'foobar', 'cwd': './abcd'}},
            1337: {
                'name': 'snafu',
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
        }, id='target from exp name'),
    ], indirect=['descs']
)
def test_tmux_exp_runner_ensure_tmux_session_with_cwd(caplog, mocker,
                                                      tmux_exp_runner):
    tmux_target = 'snafu'
    tmux_session_mock = mocker.Mock()

    def init_tmux_session_mock(*args, **kwargs):
        # pylint: disable=unused-argument
        tmux_exp_runner.experiment.tmux_session = tmux_session_mock

    tmux_exp_runner.experiment.initialize_tmux_session = init_tmux_session_mock
    tmux_cmd = tmux_exp_runner.experiment.cmd = mocker.Mock()
    with caplog.at_level(logging.INFO):
        tmux_exp_runner.ensure_tmux_session()
    assert f'Starting TMUX session in {tmux_target} ./abcd' in \
        [r.message for r in caplog.records]
    assert tmux_exp_runner.tmux_session == tmux_session_mock
    caplog.clear()
    # second call should just change the cwd
    with caplog.at_level(logging.INFO):
        tmux_exp_runner.ensure_tmux_session()
    assert f'Changing to ./abcd in TMUX session {tmux_target}' in \
        [r.message for r in caplog.records]
    assert tmux_exp_runner.tmux_session == tmux_session_mock
    tmux_cmd.assert_called_once_with('cd ./abcd')


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
                1337: {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'runs': [{'name': 'foobar'}],
                },
            },
            id='without tmux config'
        ),
    ], indirect=['descs']
)
def test_tmux_exp_dispatcher_run_not_run(caplog, tmux_exp_dispatcher):
    with caplog.at_level(logging.ERROR):
        tmux_exp_dispatcher.run(tmux_exp_dispatcher.runners[-1],
                                tmux_exp_dispatcher.runners[-1].runs[-1],
                                ctx={})
    assert len([r for r in caplog.records if r.message.endswith(
        'is not a TMUX experiment'
    )]) == 1


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
                'globals': {'tmux': {'test': 'foobar'}},
                1337: {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'runs': [{'name': 'foobar'}],
                },
            },
        ),
    ], indirect=['descs']
)
def test_tmux_exp_dispatcher_run_without_wait(tmux_exp_dispatcher):
    with pytest.raises(tmux_runner.DescriptionError):
        tmux_exp_dispatcher.run(tmux_exp_dispatcher.runners[-1],
                                tmux_exp_dispatcher.runners[-1].runs[-1],
                                ctx={})


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
                'globals': {
                    'run_wait': 12,
                    'tmux': {'test': 'foobar'},
                },
                1337: {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'runs': [{'name': 'foobar'}],
                },
            },
        ),
    ], indirect=['descs']
)
def test_tmux_exp_dispatcher_run_without_site(caplog, mocker,
                                              tmux_exp_dispatcher):
    mocker.patch('time.sleep')
    mocker.patch('iotlab_controller.experiment.tmux.TmuxExperiment.send_keys')
    tmux_exp_dispatcher.runners[-1].experiment.tmux_session = mocker.Mock(
        capture_pane=mocker.Mock(return_value=['Aggregator started'])
    )
    with caplog.at_level(logging.WARNING):
        tmux_exp_dispatcher.run(tmux_exp_dispatcher.runners[-1],
                                tmux_exp_dispatcher.runners[-1].runs[-1],
                                ctx={'logname': 'assumed.log'})
    assert 'No IoT-LAB site provided to run TMUX commands. Will assume we ' \
        'run on IoT-LAB frontend.' in [r.message for r in caplog.records]


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
                'globals': {
                    'run_wait': 12,
                    'tmux': {
                        'test': 'foobar',
                        'cmds': ['abcd']
                    },
                },
                1337: {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'edgelist': [['m3-1', 'm3-2']]
                        }
                    },
                    'runs': [{'name': 'foobar'}],
                },
            },
            id='networked nodes'
        ),
        pytest.param({
                'globals': {
                    'run_wait': 12,
                    'site': 'grenoble',
                    'tmux': {
                        'test': 'foobar',
                        'cmds': ['abcd']
                    },
                },
                1337: {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'runs': [{'name': 'foobar'}],
                },
            },
            id='site in globals'
        ),
        pytest.param({
                'globals': {
                    'run_wait': 12,
                    'serial_aggregator_color': True,
                    'site': 'grenoble',
                    'tmux': {
                        'test': 'foobar',
                        'cmds': ['abcd']
                    },
                },
                1337: {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'runs': [{'name': 'foobar'}],
                },
            },
            id='colors'
        ),
    ], indirect=['descs']
)
def test_tmux_exp_dispatcher_run_success(caplog, mocker, tmux_exp_dispatcher):
    mocker.patch('time.sleep')
    mocker.patch('time.asctime', return_value='soon')
    mocker.patch('iotlab_controller.experiment.tmux.TmuxExperiment.send_keys')
    tmux_exp_dispatcher.runners[-1].experiment.tmux_session = mocker.Mock(
        capture_pane=mocker.Mock(return_value=['Aggregator started'])
    )
    with caplog.at_level(logging.INFO):
        tmux_exp_dispatcher.run(tmux_exp_dispatcher.runners[-1],
                                tmux_exp_dispatcher.runners[-1].runs[-1],
                                ctx={'logname': 'assumed.log'})
    assert len([r for r in caplog.records if r.levelname == 'WARNING']) == 0
    assert 'Waiting for 12s for run foobar (until soon) to finish' in \
        [r.message for r in caplog.records]


@pytest.mark.parametrize(
    'tmux_exp, descs', [
        pytest.param(False, {
                'globals': {
                    'run_wait': 12,
                    'site': 'grenoble',
                },
                1337: {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'runs': [{'name': 'foobar'}],
                },
            },
            id='no tmux experiments'
        ),
        pytest.param(True, {
                'globals': {
                    'run_wait': 12,
                    'site': 'grenoble',
                    'tmux': {
                        'test': 'foobar',
                        'cmds': ['abcd']
                    },
                },
                1337: {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'runs': [{'name': 'foobar'}],
                },
            },
            id='tmux experiments'
        ),
    ], indirect=['descs']
)
def test_tmux_exp_dispatcher_run_exps(caplog, mocker, tmux_exp,
                                      tmux_exp_dispatcher):
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={'state': 'Running',
                      'nodes': ['m3-1.grenoble.iot-lab.info']}
    )
    mocker.patch('time.sleep')
    mocker.patch('time.asctime', return_value='soon')
    send_keys = mocker.patch(
        'iotlab_controller.experiment.tmux.TmuxExperiment.send_keys'
    )
    tmux_exp_dispatcher.tmux_session = mocker.Mock()
    tmux_exp_dispatcher.runners[-1].experiment.tmux_session = mocker.Mock(
        capture_pane=mocker.Mock(return_value=['Aggregator started'])
    )
    open_mock = mocker.mock_open()
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    with caplog.at_level(logging.INFO):
        tmux_exp_dispatcher.run_experiments()
    if tmux_exp:
        assert not len([r for r in caplog.records if r.levelname == 'WARNING'])
        assert 'Waiting for 12s for run foobar (until soon) to finish' in \
            [r.message for r in caplog.records]
        send_keys.assert_called()
    else:
        assert 'Waiting for 12s for run foobar (until soon) to finish' not in \
            [r.message for r in caplog.records]
