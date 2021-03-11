# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.
# pylint: disable=redefined-outer-name
# pylint gets confused by fixture base_node

import datetime
import urllib.error

import pytest

import iotlab_controller.experiment.base
import iotlab_controller.riot

# importing fixture to be used with tests, for flake8 this is confusing
from iotlab_controller.tests.test_nodes import \
        base_nodes_base, base_nodes     # noqa: F401


@pytest.fixture
def base_experiment_scheduled(mocker, base_nodes):  # noqa: F811
    default_api = mocker.patch('iotlab_controller.common.get_default_api')
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={
            'state': 'Running',
            'nodes': ['foobar-1.test', 'foobar-2.test'],
        }
    )
    target = mocker.Mock()
    assert 'foobar-1.test' in base_nodes
    assert 'foobar-2.test' in base_nodes
    exp = iotlab_controller.experiment.base.BaseExperiment(
        'test-experiment',
        base_nodes,
        exp_id=12345,
        target=target,
    )
    assert exp.exp_id == 12345
    assert exp.api == default_api.return_value
    yield exp


@pytest.fixture
# using imported fixtures, for flake8 that is confusing
def base_experiment_unscheduled(mocker, base_nodes):  # noqa: F811
    default_api = mocker.patch('iotlab_controller.common.get_default_api')
    target = mocker.Mock()
    exp = iotlab_controller.experiment.base.BaseExperiment(
        'test-experiment',
        base_nodes,
        target=target,
    )
    assert exp.api == default_api.return_value
    yield exp


# using imported fixtures, for flake8 that is confusing
def test_base_experiment_init_error_firmwares(base_nodes):      # noqa: F811
    assert len(base_nodes) != 3
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        iotlab_controller.experiment.base.BaseExperiment(
            'test-experiment',
            base_nodes,
            # firmware is not used on init, so just throw in something
            firmwares=3 * [0],
        )


# using imported fixtures, for flake8 that is confusing
def test_base_experiment_init_error_profiles(base_nodes):       # noqa: F811
    assert len(base_nodes) != 3
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        iotlab_controller.experiment.base.BaseExperiment(
            'test-experiment',
            base_nodes,
            # profiles is not used on init, so just throw in something
            profiles=3 * [0],
        )


# using imported fixtures, for flake8 that is confusing
def test_base_experiment_init_error_http(mocker, base_nodes):   # noqa: F811
    api = mocker.Mock()
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        side_effect=urllib.error.HTTPError(
            url=mocker.Mock(),
            code=301,
            msg=mocker.Mock(),
            hdrs=mocker.Mock(),
            fp=mocker.Mock(),
        )
    )
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        iotlab_controller.experiment.base.BaseExperiment(
            'test-experiment',
            base_nodes,
            api=api,
            exp_id=12345,
        )


@pytest.mark.parametrize('state', ['Error', 'Terminated', 'Stopped'])
def test_base_experiment_init_error_state(
    mocker,
    # using imported fixtures, for flake8 that is confusing
    base_nodes,     # noqa: F811
    state
):
    api = mocker.Mock()
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={'state': state}
    )
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        iotlab_controller.experiment.base.BaseExperiment(
            'test-experiment',
            base_nodes,
            api=api,
            exp_id=12345,
        )


def test_base_experiment_init_error_nodes(mocker, base_nodes):  # noqa: F811
    api = mocker.Mock()
    mocker.patch(
        'iotlabcli.experiment.get_experiment',
        return_value={
            'state': 'Running',
            'nodes': ['foobar-1.test'],
        }
    )
    assert 'foobar-1.test' in base_nodes
    assert 'foobar-2.test' in base_nodes
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        iotlab_controller.experiment.base.BaseExperiment(
            'test-experiment',
            base_nodes,
            api=api,
            exp_id=12345,
        )


# using imported fixtures, for flake8 that is confusing
def test_base_experiment_init_success(mocker, base_nodes):  # noqa: F811
    api = mocker.Mock()
    mocker.patch(
        'iotlabcli.auth.get_user_credentials',
        return_value=('myuser', 'mypassword')
    )
    exp = iotlab_controller.experiment.base.BaseExperiment(
        'test-experiment',
        base_nodes,
        api=api,
    )
    assert exp.name == 'test-experiment'
    assert exp.nodes == base_nodes
    assert exp.firmwares is None
    assert exp.firmwares is None
    assert exp.username == 'myuser'
    assert exp.target is None
    assert not exp.target_args
    assert not exp.target_kwargs
    assert exp.exp_id is None


def test_base_experiment_init_str_scheduled(base_experiment_scheduled):
    assert str(base_experiment_scheduled) == \
           "<BaseExperiment: test-experiment (12345)>"


def test_base_experiment_init_str_unscheduled(base_experiment_unscheduled):
    assert str(base_experiment_unscheduled) == \
           "<BaseExperiment: test-experiment (unscheduled)>"


def test_base_experiment_iter_experiments_error1(mocker):
    mocker.patch('iotlab_controller.common.get_default_api')
    mocker.patch(
        'iotlabcli.experiment.get_active_experiments',
        side_effect=urllib.error.HTTPError(
            url=mocker.Mock(),
            code=301,
            msg=mocker.Mock(),
            hdrs=mocker.Mock(),
            fp=mocker.Mock(),
        )
    )
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        next(
            iotlab_controller.experiment.base.BaseExperiment.iter_experiments()
        )


def test_base_experiment_iter_experiments_error2(mocker):
    api = mocker.patch('iotlab_controller.common.get_default_api')
    api.return_value.get_experiment_info = mocker.Mock(
        side_effect=urllib.error.HTTPError(
            url=mocker.Mock(),
            code=301,
            msg=mocker.Mock(),
            hdrs=mocker.Mock(),
            fp=mocker.Mock(),
        )
    )
    mocker.patch(
        'iotlabcli.experiment.get_active_experiments',
        return_value={'Running': [12345]}
    )
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        next(
            iotlab_controller.experiment.base.BaseExperiment.iter_experiments()
        )


def test_base_experiment_iter_experiments_success(mocker, base_nodes_base):     # noqa: 811
    api = mocker.Mock()
    api.get_nodes = mocker.Mock(
        return_value={'items': base_nodes_base}
    )
    exp_info = {
        12345: {
            'nodes': ['foobar-1.test'],
            'name': 'foobar',
            'state': 'Running'
        },
        12346: {
            'nodes': ['foobar-1.test'],
            'name': 'fooba',
            'state': 'Waiting'
        },
    }
    api.get_experiment_info = mocker.Mock(
        side_effect=lambda exp_id, *args: exp_info[exp_id]
    )
    mocker.patch(
        'iotlabcli.experiment.get_active_experiments',
        return_value={'Running': [12345], 'Waiting': [12346]}
    )
    count = 0
    for i, exp in enumerate(
        iotlab_controller.experiment.base.BaseExperiment.iter_experiments(
            api=api
        )
    ):
        if i == 0:
            assert exp.exp_id == 12345
        else:
            assert exp.exp_id == 12346
        assert i < 2
        for node in exp_info[exp.exp_id]['nodes']:
            assert node in exp.nodes
        assert exp.name == exp_info[exp.exp_id]['name']
        assert exp.is_scheduled()
        count += 1
    assert count == 2


def test_base_experiment_schedule_scheduled(base_experiment_scheduled):
    assert base_experiment_scheduled.is_scheduled()
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        base_experiment_scheduled.schedule(5)


def test_base_experiment_schedule_success1(base_experiment_unscheduled):
    assert not base_experiment_unscheduled.is_scheduled()
    base_experiment_unscheduled.schedule(5, datetime.datetime.now())
    assert base_experiment_unscheduled.is_scheduled()


def test_base_experiment_schedule_success2(
    mocker,
    base_experiment_unscheduled
):
    submit = mocker.patch('iotlabcli.experiment.submit_experiment')
    firmware = iotlab_controller.riot.RIOTFirmware('this/is/a/test', 'foobar')
    base_experiment_unscheduled.firmwares = [firmware]
    assert not base_experiment_unscheduled.is_scheduled()
    base_experiment_unscheduled.schedule(5, datetime.datetime.now())
    assert base_experiment_unscheduled.is_scheduled()
    submit.assert_called_once()


def test_base_experiment_schedule_success3(
    mocker,
    base_experiment_unscheduled
):
    submit = mocker.patch('iotlabcli.experiment.submit_experiment')
    profile = ['sniff']
    base_experiment_unscheduled.profiles = [profile]
    assert not base_experiment_unscheduled.is_scheduled()
    base_experiment_unscheduled.schedule(5)
    assert base_experiment_unscheduled.is_scheduled()
    submit.assert_called_once()


@pytest.mark.parametrize(
    'firmwares, profiles', [
        (2 * [iotlab_controller.riot.RIOTFirmware('this/is/a/test', 'foobar')],
         ['sniff', 'sniff']),
        (2 * [iotlab_controller.riot.RIOTFirmware('this/is/a/test', 'foobar')],
         ['sniff']),
        ([iotlab_controller.riot.RIOTFirmware('this/is/a/test', 'foobar')],
         ['sniff', 'sniff']),
        (None, ['sniff', 'sniff']),
        (2 * [iotlab_controller.riot.RIOTFirmware('this/is/a/test', 'foobar')],
         None),
    ]
)
def test_base_experiment_schedule_success4(
    mocker,
    base_experiment_unscheduled,
    firmwares,
    profiles
):
    assert len(base_experiment_unscheduled.nodes) == 2
    submit = mocker.patch('iotlabcli.experiment.submit_experiment')
    base_experiment_unscheduled.firmwares = firmwares
    base_experiment_unscheduled.profiles = profiles
    assert not base_experiment_unscheduled.is_scheduled()
    base_experiment_unscheduled.schedule(5, datetime.datetime.now())
    assert base_experiment_unscheduled.is_scheduled()
    submit.assert_called_once()
    # check first 4th argument of submit (resources) for firmwares and profiles
    # to be correct:
    for resource in submit.call_args[0][3]:
        if firmwares is None:
            assert resource['firmware'] is None
        else:
            assert resource['firmware'] == 'this/is/a/test/bin/foobar/test.elf'
        if profiles is None:
            assert resource['profile'] is None
        else:
            assert resource['profile'] == 'sniff'


def test_base_experiment_stop(mocker, base_experiment_scheduled):
    stop = mocker.patch('iotlabcli.experiment.stop_experiment')
    assert base_experiment_scheduled.is_scheduled()
    base_experiment_scheduled.stop()
    assert not base_experiment_scheduled.is_scheduled()
    stop.assert_called_once_with(base_experiment_scheduled.api, 12345)
    # stopping a stopped experiment should do nothing
    base_experiment_scheduled.stop()
    assert not base_experiment_scheduled.is_scheduled()
    # still only called once
    stop.assert_called_once()


def test_base_experiment_wait_unscheduled(base_experiment_unscheduled):
    assert not base_experiment_unscheduled.is_scheduled()
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        base_experiment_unscheduled.wait()


def test_base_experiment_wait(mocker, base_experiment_scheduled):
    wait = mocker.patch('iotlabcli.experiment.wait_experiment')
    assert base_experiment_scheduled.is_scheduled()
    base_experiment_scheduled.wait()
    wait.assert_called_once_with(base_experiment_scheduled.api, 12345,
                                 states="Running", timeout=float("+inf"))


def test_base_experiment_run_unscheduled(base_experiment_unscheduled):
    assert not base_experiment_unscheduled.is_scheduled()
    with pytest.raises(iotlab_controller.experiment.base.ExperimentError):
        base_experiment_unscheduled.run()


def test_base_experiment_run_scheduled(base_experiment_scheduled):
    exp = base_experiment_scheduled
    assert exp.is_scheduled()
    exp.run()
    exp.target.assert_called_once_with(exp, *exp.target_args,
                                       **exp.target_kwargs)
    exp.target = None
    exp.run()
