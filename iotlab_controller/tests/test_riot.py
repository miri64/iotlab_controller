# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import subprocess

import pytest

import iotlab_controller.firmware
import iotlab_controller.riot


@pytest.mark.parametrize(
    'application_path, application_name, exp_name, flashfile, env',
    [('this/is/a/test', None, 'test', None, None),
     ('this/is/a/test/', None, 'test', None, None),
     ('this/is/a/test', 'foobar', 'foobar', 'foobar/has/a/path', None),
     ('this/is/a/test/', 'foobar', 'foobar', None, None),
     ('this/is/a/test', None, 'test', None, None),
     ('this/is/a/test/', None, 'test', None, None),
     ('this/is/a/test', 'foobar', 'foobar', None, {'ONE': '1', 'TWO': '2'}),
     ('this/is/a/test/', 'foobar', 'foobar', None, None)]
)
def test_init(application_path, application_name, exp_name, flashfile, env):
    firmware = iotlab_controller.riot.RIOTFirmware(
        application_path=application_path,
        board='myboard',
        application_name=application_name,
        flashfile=flashfile,
        env=env
    )
    assert firmware.application_path == application_path
    assert firmware.board == 'myboard'
    assert firmware.flashfile == flashfile
    assert firmware.application_name == exp_name
    assert firmware.env['BOARD'] == 'myboard'
    if env is not None:
        for var, value in env.items():
            assert firmware.env[var] == value


def test_repr():
    firmware = iotlab_controller.riot.RIOTFirmware(
        application_path='this/is/a/test',
        board='myboard',
    )
    assert repr(firmware) == "<RIOTFirmware at test>"


@pytest.mark.parametrize(
    'kwargs_change',
    [{'application_path': 'this/is/one/test'},
     {'board': 'otherboard'},
     {'flashfile': 'a_flash_file.elf'},
     {'env': {'FOOBAR': 'test'}}]
)
def test_eq(kwargs_change):
    kwargs = {
        'application_path': 'this/is/a/test',
        'board': 'myboard',
        'flashfile': None,
        'env': None,
    }
    firmware1 = iotlab_controller.riot.RIOTFirmware(**kwargs)
    firmware2 = iotlab_controller.riot.RIOTFirmware(**kwargs)
    assert firmware1 == firmware2
    assert all(k in kwargs for k in kwargs_change)
    assert all(v != kwargs[k] for k, v in kwargs_change.items())
    kwargs.update(kwargs_change)
    firmware3 = iotlab_controller.riot.RIOTFirmware(**kwargs)
    assert firmware1 != firmware3
    assert firmware1 != "foobar"


@pytest.mark.parametrize('flashfile', [None, 'firmware/has/a/path.elf'])
def test_path(flashfile):
    firmware = iotlab_controller.riot.RIOTFirmware(
        application_path='this/is/a/test',
        board='myboard',
        flashfile=flashfile
    )
    if flashfile is None:
        assert firmware.path == 'this/is/a/test/bin/myboard/test.{}' \
                .format(firmware.FILE_EXTENSION)
    else:
        assert firmware.path == flashfile


@pytest.mark.parametrize('build_env', [None, {'ONE': '1'}])
def test_build_success(mocker, build_env):
    run = mocker.patch('subprocess.run')
    firmware = iotlab_controller.riot.RIOTFirmware(
        application_path='this/is/a/test',
        board='myboard',
    )
    exp_env = {k: v for k, v in firmware.env.items()}
    if build_env:
        exp_env.update(build_env)
    firmware.build(build_env=build_env)
    run.assert_called_once_with(
        ['make', '-C', firmware.application_path, 'all', '-j', '1'],
        env=exp_env,
        check=True
    )


@pytest.mark.parametrize('build_env', [None, {'ONE': '1'}])
def test_build_error(mocker, build_env):
    run = mocker.patch(
        'subprocess.run',
        side_effect=subprocess.CalledProcessError(returncode=1, cmd='foobar')
    )
    firmware = iotlab_controller.riot.RIOTFirmware(
        application_path='this/is/a/test',
        board='myboard',
    )
    exp_env = {k: v for k, v in firmware.env.items()}
    if build_env:
        exp_env.update(build_env)
    with pytest.raises(iotlab_controller.firmware.FirmwareBuildError):
        firmware.build(build_env=build_env, threads='')
    run.assert_called_once_with(
        ['make', '-C', firmware.application_path, 'all', '-j'],
        env=exp_env,
        check=True
    )


@pytest.mark.parametrize('build_env', [None, {'ONE': '1'}])
def test_clean_success(mocker, build_env):
    run = mocker.patch('subprocess.run')
    firmware = iotlab_controller.riot.RIOTFirmware(
        application_path='this/is/a/test',
        board='myboard',
    )
    exp_env = {k: v for k, v in firmware.env.items()}
    if build_env:
        exp_env.update(build_env)
    firmware.clean(build_env=build_env)
    run.assert_called_once_with(
        ['make', '-C', firmware.application_path, 'clean'],
        env=exp_env,
        check=True
    )


@pytest.mark.parametrize('build_env', [None, {'ONE': '1'}])
def test_clean_error(mocker, build_env):
    run = mocker.patch(
        'subprocess.run',
        side_effect=subprocess.CalledProcessError(returncode=1, cmd='foobar')
    )
    firmware = iotlab_controller.riot.RIOTFirmware(
        application_path='this/is/a/test',
        board='myboard',
    )
    exp_env = {k: v for k, v in firmware.env.items()}
    if build_env:
        exp_env.update(build_env)
    with pytest.raises(iotlab_controller.firmware.FirmwareBuildError):
        firmware.clean(build_env=build_env)
    run.assert_called_once_with(
        ['make', '-C', firmware.application_path, 'clean'],
        env=exp_env,
        check=True
    )


@pytest.mark.parametrize('build_env', [None, {'ONE': '1'}])
def test_distclean_success(mocker, build_env):
    run = mocker.patch('subprocess.run')
    iotlab_controller.riot.RIOTFirmware.distclean('this/is/a/test')
    run.assert_called_once_with(
        ['make', '-C', 'this/is/a/test', 'distclean'], check=True
    )


@pytest.mark.parametrize('build_env', [None, {'ONE': '1'}])
def test_distclean_error(mocker, build_env):
    run = mocker.patch(
        'subprocess.run',
        side_effect=subprocess.CalledProcessError(returncode=1, cmd='foobar')
    )
    with pytest.raises(iotlab_controller.firmware.FirmwareBuildError):
        iotlab_controller.riot.RIOTFirmware.distclean('this/is/a/test')
    run.assert_called_once_with(
        ['make', '-C', 'this/is/a/test', 'distclean'], check=True
    )
