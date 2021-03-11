# Copyright (C) 2019-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.
# pylint: disable=redefined-outer-name
# pylint gets confused by fixture base_node

import libtmux.exc
import pytest

import iotlab_controller.experiment.tmux

# importing fixture to be used with tests, for flake8 this is confusing
from iotlab_controller.tests.test_nodes import \
        base_nodes_base, base_nodes     # noqa: F401


@pytest.fixture
# using imported fixtures, for flake8 that is confusing
def tmux_exp(mocker, base_nodes):  # noqa: F811
    mocker.patch('iotlab_controller.experiment.base.BaseExperiment.__init__')
    exp = iotlab_controller.experiment.tmux.TmuxExperiment(
        'test-experiment', base_nodes
    )
    # BaseExperiment is mocked, so we need to provide the values needed for
    # tests
    exp.exp_id = 12345
    exp.username = 'user'
    yield exp
    if exp.tmux_session:
        exp.hit_ctrl_d()    # leave pane and kill TMUX session


# using imported fixtures, for flake8 that is confusing
def test_tmux_experiment_init(mocker, base_nodes):  # noqa: F811
    init = mocker.patch(
        'iotlab_controller.experiment.base.BaseExperiment.__init__'
    )
    exp = iotlab_controller.experiment.tmux.TmuxExperiment(
        'test-experiment', base_nodes
    )
    init.assert_called_once()
    # The tmux server is a TMUX server object but has no sessions
    with pytest.raises(libtmux.exc.LibTmuxException):
        assert not exp.tmux_server.list_sessions()
    assert exp.tmux_session is None


@pytest.mark.parametrize(
    'window_name, pane_id, cwd',
    [
        (None,          None,   None),
        ('test-window', None,   None),
        (None,          '%0',   None),
        ('test-window', '%0',   None),
        (None,          None,   '/tmp'),
        ('test-window', None,   '/tmp'),
        (None,          '%0',   '/tmp'),
        ('test-window', '%0',   '/tmp'),
    ]
)
def test_tmux_experiment_init_session(tmux_exp, window_name, pane_id,
                                      cwd):
    # tmux_exp has no session initialized
    with pytest.raises(libtmux.exc.LibTmuxException):
        assert not tmux_exp.tmux_server.list_sessions()
    session = tmux_exp.initialize_tmux_session('test-session', window_name,
                                               pane_id, cwd)
    assert session is not None
    assert session == tmux_exp.tmux_session
    # there is now a session named test-session
    tmux_sessions = [s for s in tmux_exp.tmux_server.list_sessions()
                     if s.name == 'test-session']
    assert len(tmux_sessions) == 1
    assert session.window.session == tmux_sessions[0]
    assert not window_name or session.window.name == window_name
    assert not pane_id or session.id == pane_id
    if cwd:
        tmux_exp.cmd('pwd')
        # capture_pane() provides a list of lines, check if cwd is in it.
        assert cwd in tmux_exp.tmux_session.capture_pane()
    new_session = tmux_exp.initialize_tmux_session('test-session', window_name,
                                                   pane_id, cwd)
    assert session == new_session


@pytest.mark.parametrize(
    'site, with_a8, color, logname',
    [
        (None,      None,   None,   None),
        (None,      False,  False,  None),
        ('foobar',  False,  False,  None),
        (None,      True,   False,  None),
        ('foobar',  True,   False,  None),
        (None,      False,  True,   None),
        ('foobar',  False,  True,   None),
        (None,      True,   True,   None),
        ('foobar',  True,   True,   None),
        (None,      False,  False,  'logfile.log'),
        ('foobar',  False,  False,  'logfile.log'),
    ]
)
def test_tmux_experiment_start_serial_aggregator(mocker, tmux_exp, site,
                                                 with_a8, color, logname):
    send_keys = mocker.patch(
        'iotlab_controller.experiment.tmux.TmuxExperiment.send_keys'
    )
    tmux_exp.start_serial_aggregator(site, with_a8, color, logname)
    expect = ""
    if site:
        expect += "ssh user@foobar.iot-lab.info "
    expect += "serial_aggregator -i 12345"
    if with_a8:
        expect += " --with-a8"
    if color:
        expect += " --color"
    if logname:
        expect += "| tee -a logfile.log"
    send_keys.assert_called_with(expect, enter=True, wait_after=2)


def test_tmux_experiment_stop_serial_aggregator(mocker, tmux_exp):
    send_keys = mocker.patch(
        'iotlab_controller.experiment.tmux.TmuxExperiment.send_keys'
    )
    tmux_exp.stop_serial_aggregator()
    send_keys.assert_called_once_with("C-c")


def test_tmux_experiment_serial_aggregator(mocker, tmux_exp):
    send_keys = mocker.patch(
        'iotlab_controller.experiment.tmux.TmuxExperiment.send_keys'
    )
    expect = "serial_aggregator -i 12345"
    with tmux_exp.serial_aggregator() as exp:
        assert tmux_exp == exp
        exp.cmd("test")
    send_keys.assert_any_call(expect, enter=True, wait_after=2)
    send_keys.assert_any_call("test", enter=True, wait_after=0)
    # last thing done is closing the serial_aggregator
    send_keys.assert_called_with("C-c")


def test_tmux_experiment_send_keys_wo_session(tmux_exp):
    with pytest.raises(AssertionError):
        tmux_exp.send_keys('echo "test"', wait_after=1337)


def test_tmux_experiment_send_keys_success(mocker, tmux_exp):
    sleep = mocker.patch('time.sleep')
    tmux_exp.initialize_tmux_session('test-session')
    tmux_exp.send_keys('echo "test"', enter=True, wait_after=1337)
    # capture_pane() provides a list of lines, check if 'test' is in it.
    assert 'test' in tmux_exp.tmux_session.capture_pane()
    sleep.assert_called_once_with(1337)


def test_tmux_experiment_hit_enter_wo_session(tmux_exp):
    with pytest.raises(AssertionError):
        tmux_exp.hit_enter()


def test_tmux_experiment_hit_enter_success(mocker, tmux_exp):
    tmux_exp.initialize_tmux_session('test-session')
    tmux_exp.send_keys('echo "test"', enter=False)
    # capture_pane() provides a list of lines, check if 'test' is in it.
    assert 'test' not in tmux_exp.tmux_session.capture_pane()
    tmux_exp.hit_enter()
    assert 'test' in tmux_exp.tmux_session.capture_pane()
