# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.
# pylint: disable=redefined-outer-name
# pylint gets confused by fixture base_node

import copy
import logging
import pytest
import sys
import time
import urllib

import iotlab_controller.constants
from iotlab_controller.experiment.descs import file_handler
from iotlab_controller.experiment.descs import runner as descs_runner

# importing fixture to be used with tests, for flake8 this is confusing
from iotlab_controller.tests.test_nodes import \
        networked_nodes_base    # noqa: F401


@pytest.fixture
def exp_dispatcher(mocker, networked_nodes_base):   # noqa: F811
    api = mocker.Mock()
    api.get_nodes = mocker.Mock(
        return_value={'items': networked_nodes_base}
    )
    yield descs_runner.ExperimentDispatcher("test.yaml", api=api)


@pytest.fixture
def api_mock(mocker, networked_nodes_base):     # noqa: F811
    assert iotlab_controller.constants.IOTLAB_DOMAIN == 'iot-lab.info'
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={
            'state': 'Running',
            'nodes': [n['network_address'] for n in networked_nodes_base],
        }
    )
    api = mocker.Mock()
    api.get_nodes = mocker.Mock(
        return_value={'items': networked_nodes_base}
    )
    yield api


@pytest.fixture
def descs(request, mocker):
    handler = file_handler.DescriptionFileHandler('test.yaml')
    handler.dump = mocker.Mock()
    if request.param is None:
        yield None
    else:
        yield handler.load_content(request.param)


@pytest.mark.parametrize(
    'exp_id, descs', [
        pytest.param(123, {123: {}}, id='no nodes'),
        pytest.param(123, {123: {'nodes': 'foobar'}},
                     id='nodes not list or dict'),
        pytest.param(123, {123: {'nodes': [{'horst': 'foobar'}]}},
                     id='nodes list but no name'),
        pytest.param(123, {123: {'nodes': {'horst': 'foobar'}}},
                     id='nodes dict without network'),
        pytest.param(123, {123: {'nodes': {'network': {'foobar': {}}}}},
                     id='no site for network'),
        pytest.param(123, {123: {'nodes': {'network': {
                         'site': 'grenoble',
                         'foobar': {},
                     }}}},
                     id='no edgelist for network'),
        pytest.param(123, {123: {'nodes': {'network': {
                         'site': 'grenoble',
                         'edgelist': ['foobar'],
                     }}}},
                     id='malformed edgelist (not a list of lists)'),
        pytest.param(123, {123: {'nodes': {'network': {
                         'site': 'grenoble',
                         'edgelist': [(123,)]
                     }}}},
                     id='malformed edgelist (not a list of length 2 lists)'),
        pytest.param(123, {
                123: {
                    'firmwares': [{
                        'type': 'foobar',
                        'board': 'iotlab-m3',
                        'path': 'test-app',
                    }],
                    'nodes': [
                        'm3-1.grenoble.iot-lab.info',
                        'm3-2.grenoble.iot-lab.info',
                        'm3-3.grenoble.iot-lab.info',
                    ]
                },
            },
            id='unrecognized firmware type'
        ),
        pytest.param(123, {
                123: {
                    'firmwares': [
                        {'board': 'iotlab-m3'},
                    ],
                    'nodes': [
                        'm3-1.grenoble.iot-lab.info',
                        'm3-2.grenoble.iot-lab.info',
                        'm3-3.grenoble.iot-lab.info',
                    ]
                },
            },
            id='missing path'
        ),
        pytest.param(123, {
                123: {
                    'firmwares': [
                        {'path': 'test-app'},
                    ],
                    'nodes': [
                        'm3-1.grenoble.iot-lab.info',
                        'm3-2.grenoble.iot-lab.info',
                        'm3-3.grenoble.iot-lab.info',
                    ]
                },
            },
            id='missing board'
        ),
        pytest.param(123, {
                123: {
                    'firmwares': [
                        {'board': 'iotlab-m3', 'path': 'test-app'},
                        {'board': 'iotlab-m3', 'path': 'test-app'},
                    ],
                    'nodes': [
                        'm3-1.grenoble.iot-lab.info',
                        'm3-2.grenoble.iot-lab.info',
                        'm3-3.grenoble.iot-lab.info',
                    ]
                },
            },
            id='not enough firmwares for nodes'
        ),
        pytest.param(123, {
                123: {
                    'sink_firmware': {
                        'board': 'iotlab-m3',
                        'path': 'test-app'
                    },
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'sink': 'm3-1',
                            'edgelist': [('m3-1', 'm3-2')],
                        },
                    }
                },
            },
            id='sink_firmware but no nodes firmware'
        ),
    ], indirect=['descs']
)
def test_experiment_runner_init_faulty_descs(mocker, api_mock, exp_id, descs):
    dispatcher = mocker.Mock()
    with pytest.raises(file_handler.DescriptionError):
        descs_runner.ExperimentRunner(dispatcher, descs[exp_id],
                                      exp_id=exp_id, api=api_mock)


@pytest.mark.parametrize(
    'exp_id, exp_nodes, descs', [
        pytest.param(123, 3, {
                'globals': {'nodes': [
                    'm3-3.grenoble.iot-lab.info',
                    'm3-4.grenoble.iot-lab.info',
                ]},
                123: {'nodes': [
                    'm3-1.grenoble.iot-lab.info',
                    'm3-2.grenoble.iot-lab.info',
                    'm3-3.grenoble.iot-lab.info',
                ]},
            },
            id='nodes list'
        ),
        pytest.param(123, 2, {
                'globals': {'nodes': [
                    {'name': 'm3-1.grenoble.iot-lab.info'},
                    {'name': 'm3-2.grenoble.iot-lab.info'},
                ]},
                123: {},
            },
            id='nodes list of dict'
        ),
        pytest.param(123, 2, {
                'globals': {'nodes': {
                    'network': {
                        'site': 'grenoble',
                        'edgelist': [('m3-1', 'm3-2')],
                    },
                }},
                123: {},
            },
            id='networked nodes (edgelist)'
        ),
        pytest.param(123, 2, {
                'globals': {'nodes': {
                    'network': {
                        'site': 'grenoble',
                        'edgelist_file': 'network.edgelist',
                    },
                }},
                123: {},
            },
            id='networked nodes (edgelist_file)'
        ),
        pytest.param(123, 2, {
                'globals': {'nodes': {
                    'network': {
                        'site': 'grenoble',
                        'sink': 'm3-1',
                        'edgelist': [('m3-1', 'm3-2')],
                    },
                }},
                123: {
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'sink_firmware': {
                        'path': 'test-app',
                        'board': 'iotlab-m3',
                        'env': {'SINK': 'canary'},
                    }
                },
            },
            id='sink networked nodes'
        ),
        pytest.param(123, 3, {
                'globals': {'nodes': {
                    'network': {
                        'site': 'grenoble',
                        'sink': 'm3-1',
                        'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                    },
                }},
                123: {
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'sink_firmware': {
                        'path': 'test-app',
                        'board': 'iotlab-m3',
                        'env': {'SINK': 'canary'},
                    }
                },
            },
            id='single nodes firmware'
        ),
        pytest.param(123, 3, {
                'globals': {'nodes': {
                    'network': {
                        'site': 'grenoble',
                        'sink': 'm3-1',
                        'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                    },
                }},
                123: {
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                },
            },
            id='single firmware'
        ),
    ], indirect=['descs']
)
def test_experiment_runner_init_success(mocker, api_mock, exp_id, exp_nodes,
                                        descs):
    dispatcher = mocker.Mock()
    if isinstance(descs[exp_id]['nodes'], dict) and \
       'edgelist_file' in descs[exp_id]['nodes']['network']:
        open_mock = mocker.mock_open(read_data='m3-1 m3-2 2.4\n')
        mocker.patch('builtins.open',
                     open_mock)
        check_edgefile = True
    else:
        open_mock = mocker.Mock()
        check_edgefile = False
    runner = descs_runner.ExperimentRunner(dispatcher, descs[exp_id],
                                           exp_id=exp_id, api=api_mock)
    assert runner.exp_id == exp_id
    if check_edgefile:
        open_mock.assert_called_once_with(
            descs[exp_id]['nodes']['network']['edgelist_file'],
            mode='rb'
        )
    assert len(runner.nodes) == exp_nodes
    assert 'm3-1.grenoble.iot-lab.info' in runner.nodes
    assert 'm3-2.grenoble.iot-lab.info' in runner.nodes
    if exp_nodes > 2:
        assert 'm3-3.grenoble.iot-lab.info' in runner.nodes
    assert runner.experiment.name == dispatcher.DEFAULT_EXP_NAME
    if descs[exp_id].get('firmwares') or descs[exp_id].get('sink_firmware'):
        assert len(runner.experiment.firmwares) == exp_nodes
    else:
        assert not runner.experiment.firmwares
    if 'sink_firmware' in descs[exp_id]:
        assert runner.experiment.firmwares[0].env['SINK'] == 'canary'
    for firmware in runner.experiment.firmwares:
        assert firmware.application_path == 'test-app'
        assert firmware.board == 'iotlab-m3'


@pytest.mark.parametrize(
    'exp_id, descs', [
        pytest.param(123, {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'target_args': {
                        'env': {
                            'FOOBAR': 'test'
                        }
                    }
                },
                123: {'env': {'FOOBAR': 'foobar'}},
            },
            id='env partly overwritten'
        ),
        pytest.param(123, {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'target_args': {
                        'env': 1
                    }
                },
                123: {'env': {'FOOBAR': 'foobar'}},
            },
            id='env replaced'
        ),
    ], indirect=['descs']
)
def test_experiment_runner_init_warnings(mocker, caplog, exp_id, descs):
    # use patched "default" API to increase code coverage
    mocker.patch('iotlab_controller.common.get_default_api')
    dispatcher = mocker.Mock()
    with caplog.at_level(logging.WARNING):
        runner = descs_runner.ExperimentRunner(dispatcher, descs[exp_id],
                                               exp_id=exp_id)
    assert 'iotlab_controller.experiment.descs.runner' in \
        [r.name for r in caplog.records]
    assert runner.exp_id == exp_id
    # don't make any assertions on nodes or experiment as API is a MagicMock
    assert runner.desc.env['FOOBAR'] == 'foobar'
    assert runner.experiment.target_kwargs['env'] == {'FOOBAR': 'foobar'}


@pytest.mark.parametrize(
    'exp_results_dir, descs', [
        pytest.param('.', {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                },
                124: {'runs': [{}, {'args': {'foobar': 'test'}}]},
            },
            id='no results_dir'
        ),
        pytest.param('foobar', {
                'globals': {
                    'results_dir': 'foobar',
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                },
                124: {'runs': [{}, {'args': {'foobar': 'test'}}]},
            },
            id='in globals'
        ),
        pytest.param('foobar', {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'run_name': '{exp.exp_id}-{time}'
                },
                124: {
                    'results_dir': 'foobar',
                    'runs': [
                        {'name': '{time}'},
                        {'args': {'foobar': 'test'}}
                    ]
                },
            },
            id='in exp'
        ),
    ], indirect=['descs']
)
def test_experiment_runner_results_dir(mocker, exp_results_dir, descs):
    # use patched "default" API to increase code coverage
    mocker.patch('iotlab_controller.common.get_default_api')
    dispatcher = mocker.Mock()
    runner = descs_runner.ExperimentRunner(dispatcher, descs[124],
                                           exp_id=124)
    assert runner.results_dir == exp_results_dir


@pytest.mark.parametrize(
    'exp_id, descs', [
        pytest.param(123, {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                },
                123: {'runs': [{}, {'args': {'foobar': 'test'}}]},
            },
            id='default'
        ),
        pytest.param(124, {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                    'run_name': '{exp.exp_id}-{time}'
                },
                124: {'runs': [
                    {'name': '{time}'},
                    {'args': {'foobar': 'test'}}
                ]},
            },
            id='with globals'
        ),
    ], indirect=['descs']
)
def test_experiment_runner_run_name(mocker, exp_id, descs):
    # use patched "default" API to increase code coverage
    mocker.patch('iotlab_controller.common.get_default_api')
    dispatcher = mocker.Mock()
    runner = descs_runner.ExperimentRunner(dispatcher, descs[exp_id],
                                           exp_id=exp_id)
    assert len(runner.runs) == 2
    for i, run in enumerate(runner.runs):
        run['idx'] = i
        if exp_id == 123:
            if i == 0:
                assert runner.run_name(run) == '123-0'
                # name stays the same
                assert runner.run_name(run) == '123-0'
            else:
                assert runner.run_name(run) == '123-1'
                # name stays the same
                assert runner.run_name(run) == '123-1'
        else:
            if i == 0:
                res = runner.run_name(run)
                # is a valid timestamp
                assert int(res) <= time.time()
                # name stays the same
                assert runner.run_name(run) == res
            else:
                res = runner.run_name(run)
                assert res == f'{exp_id}-{run["__timestamp__"]}'
                # name stays the same
                assert runner.run_name(run) == res


@pytest.mark.parametrize(
    'exp_id, exp_builds, exp_flashs, descs', [
        pytest.param(123, 0, 0, {   # exp_builds=0, exp_flashs=0
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'runs': [{}]
                },
            },
            id='no rebuild'
        ),
        pytest.param(123, 1, 1, {   # exp_builds=1, exp_flashs=1
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'runs': [{'rebuild': True}]
                },
            },
            id='single firmware, no sink, rebuild run'
        ),
        pytest.param(123, 1, 1, {   # exp_builds=1, exp_flashs=1
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'runs': [{'env': {'FOOBAR': 'test'}}, {}]
                },
            },
            id='single firmware, no sink, different run envs'
        ),
        pytest.param(123, 1, 1, {   # exp_builds=1, exp_flashs=1
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'sink_firmware': {
                        'path': 'test-sink',
                        'board': 'iotlab-m3'
                    },
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'runs': [{'env': {'FOOBAR': 'test'}}, {}]
                },
            },
            id='single firmware, diff sink firmware, no sink, '
               'different run envs'
        ),
        pytest.param(123, 3, 3, {   # exp_builds=3, exp_flashs=3
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'firmwares': [
                        {'path': 'test-app1', 'board': 'iotlab-m3'},
                        {'path': 'test-app2', 'board': 'iotlab-m3'},
                        {'path': 'test-app2', 'board': 'nrf52dk'},
                    ],
                    'runs': [{'rebuild': True}]
                },
            },
            id='multiple firmwares, no sink, rebuild run'
        ),
        pytest.param(123, 1, 1, {   # exp_builds=1, exp_flashs=1
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'sink': 'm3-1',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'runs': [{'rebuild': True}]
                },
            },
            id='single firmware, with sink, rebuild run'
        ),
        pytest.param(123, 2, 2, {   # exp_builds=2, exp_flashs=2
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'sink': 'm3-1',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'sink_firmware': {
                        'path': 'test-sink',
                        'board': 'iotlab-m3'
                    },
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'runs': [{'rebuild': True}]
                },
            },
            id='single firmware, diff sink firmware, with sink, rebuild run'
        ),
        pytest.param(123, 1, 1, {   # exp_builds=1, exp_flashs=1
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'sink': 'm3-1',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'sink_firmware': {
                        'path': 'test-app',
                        'board': 'iotlab-m3'
                    },
                    'firmwares': [{'path': 'test-app', 'board': 'iotlab-m3'}],
                    'runs': [{'rebuild': True}]
                },
            },
            id='single firmware, same sink firmware, with sink, rebuild run'
        ),
        pytest.param(123, 3, 3, {   # exp_builds=3, exp_flashs=3
                'globals': {
                    'nodes': {
                        'network': {
                            'site': 'grenoble',
                            'sink': 'm3-1',
                            'edgelist': [('m3-1', 'm3-2'), ('m3-1', 'm3-3')],
                        },
                    },
                    'env': {
                        'ABC': 'DEF',
                    },
                },
                123: {
                    'firmwares': [
                        {'path': 'test-app1', 'board': 'iotlab-m3'},
                        {'path': 'test-app2', 'board': 'iotlab-m3'},
                        {'path': 'test-app2', 'board': 'nrf52dk'},
                    ],
                    'runs': [{'rebuild': True}]
                },
            },
            id='multiple firmware, with sink, rebuild run'
        ),
    ], indirect=['descs']
)
def test_experiment_runner_flash_firmwares(mocker, api_mock, exp_id, descs,
                                           exp_builds, exp_flashs):
    # pylint: disable=too-many-arguments
    dispatcher = mocker.Mock()
    runner = descs_runner.ExperimentRunner(dispatcher, descs[exp_id],
                                           exp_id=exp_id, api=api_mock)
    assert runner.exp_id == exp_id
    clean = mocker.patch('iotlab_controller.riot.RIOTFirmware.clean')
    build = mocker.patch('iotlab_controller.riot.RIOTFirmware.build')
    flash = mocker.patch('iotlabcli.node.node_command')
    run = runner.runs[-1]
    if len(runner.runs) > 1:
        prev_run = runner.runs[-2]
    else:
        prev_run = None
    for firmware in runner.experiment.firmwares:
        assert firmware.env['ABC'] == 'DEF'
    runner.reflash_firmwares(run, prev_run)
    assert len(clean.mock_calls) == exp_builds
    assert len(build.mock_calls) == exp_builds
    # Accessing mock call args was only introduced in python 3.8:
    # https://bugs.python.org/issue21269
    if sys.version_info < (3, 8):
        return  # pragma: no cover
    assert len([c for c in flash.mock_calls
                if len(c.args) > 1 and c.args[1] == "flash"]) == exp_flashs


def test_experiment_dispatcher_init(mocker):
    dispatcher = descs_runner.ExperimentDispatcher("test.yaml")
    assert not dispatcher.runners
    assert not dispatcher.descs
    assert dispatcher.filename == 'test.yaml'
    api = mocker.Mock()
    dispatcher = descs_runner.ExperimentDispatcher("test.yaml", api=api)
    assert dispatcher.api == api
    assert not dispatcher.runners
    assert not dispatcher.descs
    assert dispatcher.filename == 'test.yaml'


@pytest.mark.parametrize(
    'exp_exp, descs', [
        pytest.param(0, {}, id="empty descs"),
        pytest.param(1, {
            'globals': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'target_args': {
                    'env': {
                        'FOOBAR': 'test'
                    }
                }
            },
            123: {'env': {'FOOBAR': 'foobar'}},
        }, id="globals, no unscheduled"),
        pytest.param(1, {
            'unscheduled': {'runs': []},
        }, id="no globals, unscheduled"),
        pytest.param(2, {
            'globals': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'target_args': {
                    'env': {
                        'FOOBAR': 'test'
                    }
                }
            },
            123: {'env': {'FOOBAR': 'foobar'}},
            'unscheduled': {'runs': []},
        }, id="globals, unscheduled"),
    ], indirect=['descs']
)
def test_experiment_dispatcher_num_exp_to_run(exp_dispatcher, exp_exp, descs):
    exp_dispatcher.descs = descs
    assert exp_dispatcher.num_experiments_to_run() == exp_exp


@pytest.mark.parametrize(
    'exp_res, descs', [
        pytest.param(False, None, id="no descs"),
        pytest.param(False, {}, id="empty descs"),
        pytest.param(True, {
            'unscheduled': {'runs': []},
        }, id="unscheduled exps"),
    ], indirect=['descs']
)
def test_experiment_dispatcher_more_exp_to_run(exp_dispatcher, exp_res, descs):
    if descs is not None:
        exp_dispatcher.descs = descs
    assert exp_dispatcher.has_experiments_to_run() == exp_res


@pytest.mark.parametrize(
    'schedule, run',
    [(False, False), (True, False), (True, True)],
)
def test_experiment_dispatcher_load_exp_descs(mocker, exp_dispatcher,
                                              schedule, run):
    load = mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.load'
    )
    exp_dispatcher.schedule_experiments = mocker.Mock()
    exp_dispatcher.run_experiments = mocker.Mock()
    exp_dispatcher.load_experiment_descriptions(schedule=schedule, run=run)
    load.assert_called_once()
    assert exp_dispatcher.descs == load.return_value
    if schedule:
        exp_dispatcher.schedule_experiments.assert_called_once()
    else:
        exp_dispatcher.schedule_experiments.assert_not_called()
    if run:
        exp_dispatcher.run_experiments.assert_called_once()
    else:
        exp_dispatcher.run_experiments.assert_not_called()


def test_experiment_dispatcher_load_exp_descs_no_schedule_run(mocker,
                                                              exp_dispatcher):
    load = mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.load'
    )
    with pytest.raises(AssertionError):
        exp_dispatcher.load_experiment_descriptions(schedule=False, run=True)
    load.assert_not_called()


@pytest.mark.parametrize(
    'descs', [
        {
            'globals': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'target_args': {
                    'env': {
                        'FOOBAR': 'test'
                    }
                }
            },
            123: {'env': {'FOOBAR': 'foobar'}},
        },
    ], indirect=['descs']
)
def test_experiment_dispatcher_dump_exp_descs(mocker, exp_dispatcher, descs):
    dump = mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.dump'
    )
    exp_dispatcher.descs = descs
    exp_dispatcher.dump_experiment_descriptions()
    dump.assert_called_once_with(descs)


@pytest.mark.parametrize(
    'exp_runners, exp_id, descs', [
        pytest.param(1, None, {
            'unscheduled': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'runs': [],
            },
        }, id='no globals'),
        pytest.param(1, None, {
            'globals': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
            'unscheduled': [{'runs': []}],
        }, id='with globals'),
        pytest.param(2, 123455, {
            123455: {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'runs': [],
            },
            'unscheduled': [{
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'runs': [],
            }],
        }, id='with scheduled experiment, no globals'),
        pytest.param(2, 123455, {
            'globals': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
            'unscheduled': {'runs': []},
            123455: {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
                'runs': [],
            },
        }, id='with scheduled experiment, with globals'),
    ], indirect=['descs']
)
def test_experiment_dispatcher_sched_exp(mocker, exp_dispatcher, exp_runners,
                                         exp_id, descs):
    mocker.patch(
        'iotlab_controller.experiment.descs.runner.'
        'ExperimentRunner.build_firmwares'
    )
    mocker.patch(
        'iotlab_controller.experiment.BaseExperiment._get_resources'
    )
    mocker.patch(
        'iotlabcli.experiment.submit_experiment',
        return_value={'id': 123456}
    )
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={'state': 'Waiting',
                      'nodes': ['m3-1.grenoble.iot-lab.info']}
    )
    dump = mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.dump'
    )
    pre_descs = copy.deepcopy(descs)
    exp_dispatcher.descs = descs
    # fill runners with some garbage
    exp_dispatcher.runners = [1, 2, 3, 4, 5, 6, 7, 8]
    exp_dispatcher.schedule_experiments()
    assert len(exp_dispatcher.runners) == exp_runners
    assert exp_dispatcher.runners[-1].exp_id == 123456
    assert len(exp_dispatcher.runners[-1].nodes) == 1
    assert 'm3-1.grenoble.iot-lab.info' in exp_dispatcher.runners[-1].nodes
    assert 'unscheduled' not in descs
    assert 123456 in descs
    assert descs[123456] == pre_descs['unscheduled'][0]
    if exp_id is not None:
        assert exp_id in descs
        assert descs[exp_id] == pre_descs[exp_id]
    dump.assert_called_once()
    # Accessing mock call args was only introduced in python 3.8:
    # https://bugs.python.org/issue21269
    if sys.version_info < (3, 8):
        return  # pragma: no cover
    assert len(dump.mock_calls[0].args) == 1
    arg_descs = dump.mock_calls[0].args[0]
    assert 123456 in arg_descs
    assert arg_descs[123456] == descs[123456]
    if exp_id is not None:
        assert exp_id in arg_descs
        assert descs[exp_id] == descs[exp_id]


@pytest.mark.parametrize(
    'exp_id, descs', [
        pytest.param(123455, {
            'globals': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
            123455: {
                'runs': [],
            },
        }),
    ], indirect=['descs']
)
def test_experiment_dispatcher_sched_exp_unable_to_requeue(
    mocker, caplog, exp_dispatcher, exp_id, descs
):
    mocker.patch(
        'iotlab_controller.experiment.descs.runner.'
        'ExperimentRunner.build_firmwares'
    )
    mocker.patch(
        'iotlab_controller.experiment.BaseExperiment._get_resources'
    )
    mocker.patch(
        'iotlabcli.experiment.submit_experiment',
        side_effect=descs_runner.ExperimentError('foobar')
    )
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={'state': 'Terminated',
                      'nodes': ['m3-1.grenoble.iot-lab.info']}
    )
    dump = mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.dump'
    )
    exp_dispatcher.descs = descs
    # fill runners with some garbage
    exp_dispatcher.runners = [1, 2, 3, 4, 5, 6, 7, 8]
    with caplog.at_level(logging.ERROR):
        print(1234)
        exp_dispatcher.schedule_experiments()
    assert len(caplog.records) == 1
    assert caplog.records[0].message.startswith(f'Unable to requeue {exp_id}:')
    assert exp_id not in descs
    assert len(exp_dispatcher.runners) == 0
    dump.assert_called_once_with({
        'globals': {
            'nodes': ['m3-1.grenoble.iot-lab.info'],
        }
    })


@pytest.mark.parametrize(
    'descs', [
        pytest.param({
            'globals': {
                'nodes': ['m3-1.grenoble.iot-lab.info'],
            },
            123455: {
                'runs': [{'name': 'one'}, {'name': 'two', 'reset': False}],
            },
            123456: {
                'runs': [],
            },
        }),
    ], indirect=['descs']
)
def test_experiment_dispatcher_run_exps(mocker, exp_dispatcher, descs):
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={'state': 'Running',
                      'nodes': ['m3-1.grenoble.iot-lab.info']}
    )
    mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.load',
        return_value=descs
    )
    open_mock = mocker.mock_open()
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    exp_dispatcher.load_experiment_descriptions(False, False)
    exp_dispatcher.schedule_experiments()
    open_mock.reset_mock()
    exp_dispatcher.run_experiments()
    # 1 call for each removal of runs of exp 123455
    # 1 call for each removal of an experiment
    assert open_mock.call_args_list == 4 * [
        mocker.call(exp_dispatcher.filename, 'w', encoding='utf-8')
    ]


@pytest.mark.parametrize(
    'descs, func', [
        pytest.param(
            {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                },
                123455: {
                    'runs': [{'name': 'one', 'idx': 1235}],
                },
            },
            'iotlab_controller.experiment.descs.runner.ExperimentRunner.'
            'reflash_firmwares'
        ),
        pytest.param(
            {
                'globals': {
                    'nodes': ['m3-1.grenoble.iot-lab.info'],
                },
                123455: {
                    'runs': [{'name': 'one'}],
                },
            },
            'iotlab_controller.nodes.BaseNodes.reset'
        ),
    ], indirect=['descs'])
def test_experiment_dispatcher_run_exps_retry_http(mocker, exp_dispatcher,
                                                   descs, func):
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={'state': 'Running',
                      'nodes': ['m3-1.grenoble.iot-lab.info']}
    )
    mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.load',
        return_value=descs
    )
    func_mock = mocker.patch(func, side_effect=[
        urllib.error.HTTPError(
            url=mocker.Mock(),
            code=301,
            msg=mocker.Mock(),
            hdrs=mocker.Mock(),
            fp=mocker.Mock(),
        ), 'foobar'])
    open_mock = mocker.mock_open()
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    exp_dispatcher.load_experiment_descriptions(False, False)
    exp_dispatcher.schedule_experiments()
    open_mock.reset_mock()
    exp_dispatcher.run_experiments()
    assert len(func_mock.call_args_list) == 2


def test_experiment_dispatcher_run_exps_no_runners(caplog, mocker,
                                                   exp_dispatcher):
    dump = mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.dump'
    )
    exp_dispatcher.descs = {123456: {}}
    assert exp_dispatcher.runners == []
    with caplog.at_level(logging.WARNING):
        exp_dispatcher.run_experiments()
    assert "No runners available. Did you schedule?" in \
        [r.message for r in caplog.records]
    assert exp_dispatcher.descs == {}
    dump.assert_called_once()


def test_experiment_dispatcher_run_exps_cant_wait(caplog, mocker,
                                                  exp_dispatcher):
    dump = mocker.patch(
        'iotlab_controller.experiment.descs.file_handler.'
        'DescriptionFileHandler.dump'
    )
    exp_dispatcher.runners = [
        mocker.Mock(exp_id=123456, experiment=mocker.Mock(
            wait=mocker.Mock(side_effect=descs_runner.ExperimentError)
        )),
        mocker.Mock(exp_id=123457, experiment=mocker.Mock(
            wait=mocker.Mock(side_effect=RuntimeError)
        )),
    ]
    exp_dispatcher.descs = {123456: {}, 123457: {}}
    with caplog.at_level(logging.ERROR):
        exp_dispatcher.run_experiments()
    assert len([
        r for r in caplog.records if
        r.message.startswith("Could not wait for experiment: ")
    ]) == 2
    assert exp_dispatcher.descs == {}
    # for each experiment removal once
    assert len(dump.call_args_list) == 2
