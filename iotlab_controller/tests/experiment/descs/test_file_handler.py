# Copyright (C) 2020-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import json
import sys

import pytest
import yaml

from iotlab_controller.experiment.descs import file_handler


def test_nested_description_base_empty_enclosure():
    obj = file_handler.NestedDescriptionBase(
        {'b': 3},
        enclosure={},
        enclosure_keys=['b', 'c']
    )
    assert obj['b'] == 3
    with pytest.raises(KeyError):
        _ = obj['c']


def test_nested_description_base_no_enclosure():
    obj = file_handler.NestedDescriptionBase(
        {'b': 3},
        enclosure_keys=['b', 'c']
    )
    assert obj['b'] == 3
    assert 'c' not in obj
    assert obj.get('c', 'foobar') == 'foobar'
    with pytest.raises(KeyError):
        _ = obj['c']


def test_nested_description_base_dict_enclosure_keys():
    obj = file_handler.NestedDescriptionBase(
        {'b': 3},
        enclosure={'d': 0},
        enclosure_keys={'b': 'b', 'c': 'd'},
    )
    assert obj['b'] == 3
    assert obj.get('b', 'foobar') == 3
    assert 'b' in obj
    assert obj['c'] == 0
    assert obj.get('c', 'foobar') == 0
    assert 'c' in obj
    with pytest.raises(KeyError):
        _ = obj['d']
    assert 'd' not in obj
    assert obj.get('d', 'foobar') == 'foobar'


def create_obj_with_enclosure(enclosure_dict, obj_dict, enclosure_keys):
    enclosure = file_handler.NestedDescriptionBase(
        enclosure_dict
    )
    obj = file_handler.NestedDescriptionBase(
        obj_dict,
        enclosure=enclosure,
        enclosure_keys=enclosure_keys
    )
    return enclosure, obj


def test_nested_description_base_getitem():
    enclosure, obj = create_obj_with_enclosure(
        {'a': 0, 'b': 1, 'c': 2}, {'b': 3}, ['b', 'c']
    )
    assert enclosure['a'] == 0
    with pytest.raises(KeyError):
        _ = obj['a']
    assert enclosure['b'] == 1
    assert obj['b'] == 3
    assert enclosure['c'] == 2
    assert obj['c'] == 2
    with pytest.raises(KeyError):
        _ = enclosure['d']
    with pytest.raises(KeyError):
        _ = obj['d']


def test_nested_description_base_get():
    enclosure, obj = create_obj_with_enclosure(
        {'a': 0, 'b': 1, 'c': 2}, {'b': 3}, ['b', 'c']
    )
    assert str(obj) == "{'b': 3}"
    assert enclosure.get('a', 'foobar') == 0
    assert obj.get('a', 'foobar') == 'foobar'
    assert enclosure.get('b', 'foobar') == 1
    assert obj.get('b', 'foobar') == 3
    assert enclosure.get('c', 'foobar') == 2
    assert obj.get('c', 'foobar') == 2
    assert enclosure.get('d', 'foobar') == 'foobar'
    assert obj.get('d', 'foobar') == 'foobar'


def test_nested_description_base_contains():
    enclosure, obj = create_obj_with_enclosure(
        {'a': 0, 'b': 1, 'c': 2}, {'b': 3}, ['b', 'c']
    )
    assert 'a' in enclosure
    assert 'a' not in obj
    assert 'b' in enclosure
    assert 'b' in obj
    assert 'c' in enclosure
    assert 'c' in obj
    assert 'd' not in enclosure
    assert 'd' not in obj


def test_nested_description_base_env():
    enclosure_dict = {'env': {'a': 0, 'b': 1, 'c': 2}}
    obj_dict = {'env': {'b': 3, 'd': 4}}
    enclosure, obj = create_obj_with_enclosure(
        enclosure_dict, obj_dict, ['env']
    )
    assert enclosure.env == {'a': '0', 'b': '1', 'c': '2'}
    assert obj.env == {'a': '0', 'b': '3', 'c': '2', 'd': '4'}
    obj = file_handler.NestedDescriptionBase(
        obj_dict,
        enclosure=enclosure_dict,
        enclosure_keys=['env']
    )
    assert obj.env == {'a': '0', 'b': '3', 'c': '2', 'd': '4'}
    obj = file_handler.NestedDescriptionBase(
        obj_dict,
        enclosure=enclosure_dict,
    )
    assert obj.env == {'b': '3', 'd': '4'}
    obj = file_handler.NestedDescriptionBase(
        obj_dict,
        enclosure=None,
        enclosure_keys=['env']
    )
    assert obj.env == {'b': '3', 'd': '4'}


def test_description_file_handler_load_dump_json(mocker):
    mock_data = (
        '{'
        '"globals": {'
        '"name": "sfr-cc", "env": {"MODE": "hwr", "UDP_COUNT": 200}'
        '},'
        '"253655":{'
        '"runs": [{'
        '"args": {"data_len": 104, "delay_ms": 500},'
        '"env": {"CONGURE_IMPL": "congure_quic", "MODE": "sfr"}'
        '}]}}'
    )
    open_mock = mocker.mock_open(read_data=mock_data)
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    loader = file_handler.DescriptionFileHandler(filename='foobar.json')
    res = loader.load()
    open_mock.assert_called_once_with('foobar.json')
    assert res['globals']['name'] == 'sfr-cc'
    assert len(res[253655]['runs']) == 1
    assert res[253655]['runs'][0]['args']['data_len'] == 104
    assert res[253655]['runs'][0]['args']['delay_ms'] == 500
    assert res[253655]['runs'][0].env['CONGURE_IMPL'] == 'congure_quic'
    assert res[253655]['runs'][0].env['MODE'] == 'sfr'
    assert res[253655]['runs'][0].env['UDP_COUNT'] == '200'
    # check if second call creates same result
    open_mock.reset_mock()
    new_res = loader.load()
    open_mock.assert_called_once_with('foobar.json')
    assert res == new_res
    open_mock.reset_mock()
    loader.dump(res)
    open_mock.assert_called_once_with('foobar.json', 'w')
    # Accessing mock call args was only introduced in python 3.8:
    # https://bugs.python.org/issue21269
    if sys.version_info < (3, 8):
        return  # pragma: no cover
    out = ''
    for write in open_mock().write.mock_calls:
        out += write.args[0]
    assert json.loads(out) == json.loads(mock_data)
    # check if second call creates same result
    open_mock.reset_mock()
    loader.dump(res)
    open_mock.assert_called_once_with('foobar.json', 'w')
    out = ''
    for write in open_mock().write.mock_calls:
        out += write.args[0]
    assert json.loads(out) == json.loads(mock_data)


def test_description_file_handler_load_dump_unknown_file_type():
    with pytest.raises(ValueError):
        file_handler.DescriptionFileHandler(filename='foobar.foo')


def test_description_file_handler_load_no_globals_no_runs(mocker):
    mock_data = """
253655:
  name: sfr-cc
"""
    open_mock = mocker.mock_open(read_data=mock_data)
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    loader = file_handler.DescriptionFileHandler(filename='foobar.yaml')
    res = loader.load()
    open_mock.assert_called_once_with('foobar.yaml')
    assert res[253655]['name'] == 'sfr-cc'
    assert len(res[253655]['runs']) == 0


def test_description_file_handler_load_dump_no_unscheduled(mocker):
    mock_data = """
globals:
  name: sfr-cc
  env:
    MODE: hwr
    UDP_COUNT: 200
  run_name: 'foobar'
253655:
  firmwares:
  - board: iotlab-m3
    name: sfr-cc-source
    path: ../../apps/source
  sink_firmware:
    board: iotlab-m3
    name: sfr-cc-sink
    path: ../../apps/sink
  runs:
  - args:
      data_len: 104
      delay_ms: 500
    env:
      CONGURE_IMPL: congure_quic
      MODE: sfr"""
    open_mock = mocker.mock_open(read_data=mock_data)
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    loader = file_handler.DescriptionFileHandler(filename='foobar.yaml')
    res = loader.load()
    open_mock.assert_called_once_with('foobar.yaml')
    assert res['globals']['name'] == 'sfr-cc'
    assert res['globals'].env['MODE'] == 'hwr'
    assert 'CONGURE_IMPL' not in res['globals'].env
    assert res['globals'].env['UDP_COUNT'] == '200'
    assert res[253655]['name'] == 'sfr-cc'
    assert res[253655].env['MODE'] == 'hwr'
    assert res[253655].env['UDP_COUNT'] == '200'
    assert 'CONGURE_IMPL' not in res[253655].env
    assert len(res[253655]['runs']) == 1
    assert res[253655]['runs'][0].env['CONGURE_IMPL'] == 'congure_quic'
    assert res[253655]['runs'][0].env['MODE'] == 'sfr'
    assert res[253655]['runs'][0].env['UDP_COUNT'] == '200'
    assert res[253655]['runs'][0]['args']['data_len'] == 104
    assert res[253655]['runs'][0]['args']['delay_ms'] == 500
    assert res[253655]['runs'][0]['name'] == 'foobar'
    open_mock.reset_mock()
    loader.dump(res)
    open_mock.assert_called_once_with('foobar.yaml', 'w')
    # Accessing mock call args was only introduced in python 3.8:
    # https://bugs.python.org/issue21269
    if sys.version_info < (3, 8):
        return  # pragma: no cover
    out = ''
    for write in open_mock().write.mock_calls:
        out += write.args[0]
    assert yaml.load(out, Loader=yaml.FullLoader) == \
           yaml.load(mock_data, Loader=yaml.FullLoader)
    # check if second call creates same result
    open_mock.reset_mock()
    loader.dump(res)
    open_mock.assert_called_once_with('foobar.yaml', 'w')
    out = ''
    for write in open_mock().write.mock_calls:
        out += write.args[0]
    assert yaml.load(out, Loader=yaml.FullLoader) == \
           yaml.load(mock_data, Loader=yaml.FullLoader)


def test_description_file_handler_load_only_unscheduled_dict(mocker):
    mock_data = """
globals:
  name: sfr-cc
  env:
    MODE: hwr
    UDP_COUNT: 200
unscheduled:
  runs:
  - args:
      data_len: 104
      delay_ms: 500
    env:
      CONGURE_IMPL: congure_quic
      MODE: sfr"""
    open_mock = mocker.mock_open(read_data=mock_data)
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    loader = file_handler.DescriptionFileHandler(filename='foobar.yaml')
    res = loader.load()
    open_mock.assert_called_once_with('foobar.yaml')
    assert res['globals']['name'] == 'sfr-cc'
    assert res['globals'].env['MODE'] == 'hwr'
    assert 'CONGURE_IMPL' not in res['globals'].env
    assert res['globals'].env['UDP_COUNT'] == '200'
    assert len(res['unscheduled']) == 1
    assert res['unscheduled'][0]['name'] == 'sfr-cc'
    assert res['unscheduled'][0].env['MODE'] == 'hwr'
    assert res['unscheduled'][0].env['UDP_COUNT'] == '200'
    assert 'CONGURE_IMPL' not in res['unscheduled'][0].env
    assert len(res['unscheduled'][0]['runs']) == 1
    assert res['unscheduled'][0]['runs'][0].env['CONGURE_IMPL'] == \
           'congure_quic'
    assert res['unscheduled'][0]['runs'][0].env['MODE'] == 'sfr'
    assert res['unscheduled'][0]['runs'][0].env['UDP_COUNT'] == '200'
    assert res['unscheduled'][0]['runs'][0]['args']['data_len'] == 104
    assert res['unscheduled'][0]['runs'][0]['args']['delay_ms'] == 500


def test_description_file_handler_load_invalid_keys(mocker):
    mock_data = """
globals:
  name: sfr-cc
  env:
    MODE: hwr
    UDP_COUNT: 200
  run_name: foobar
  firmwares:
  - board: iotlab-m3
    name: sfr-cc-source
    path: ../../apps/source
  sink_firmware:
    board: iotlab-m3
    name: sfr-cc-sink
    path: ../../apps/sink
    runs:
unscheduled:
- runs:
  - args:
      data_len: 104
      delay_ms: 500
    env:
      CONGURE_IMPL: congure_quic
      MODE: sfr
253656:
  name: hwr-runs
  runs:
  - args:
      data_len: 1064
      delay_ms: 500
    env:
      MODE: hwr
    name: another one
1245foobar1245: I am something you don't want
"""
    open_mock = mocker.mock_open(read_data=mock_data)
    mocker.patch('iotlab_controller.experiment.descs.file_handler.open',
                 open_mock)
    loader = file_handler.DescriptionFileHandler(filename='foobar.yaml')
    with pytest.raises(file_handler.DescriptionError):
        loader.load()
