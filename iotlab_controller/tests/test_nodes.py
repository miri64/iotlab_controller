# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.
# pylint: disable=redefined-outer-name
# pylint gets confused by fixture base_node

import io
import json

import pytest

import iotlab_controller.nodes


@pytest.fixture
def base_node(mocker):
    api = mocker.Mock()
    node = iotlab_controller.nodes.BaseNode(
        api, 'foobar', 0, '', 'foobar-1.test', 'test-site', '',
        '0.21', '1.34', '74.23'
    )
    yield node


@pytest.fixture
def base_node_dict():
    yield {
        'arch': 'foobar',
        'mobile': False,
        'mobility_type': None,
        'uri': 'foobar-1.test',
        'site': 'test-site',
        'uid': None,
        'x': 0.21,
        'y': 1.34,
        'z': 74.23,
    }


@pytest.fixture
def base_nodes_base():
    yield [
        {
            'archi': 'foobar',
            'mobile': False,
            'mobility_type': ' ',
            'network_address': 'foobar-1.test',
            'site': 'test-site',
            'uid': ' ',
            'x': ' ',
            'y': ' ',
            'z': ' ',
        },
        {
            'archi': 'foobar',
            'mobile': False,
            'mobility_type': ' ',
            'network_address': 'foobar-2.test',
            'site': 'test-site',
            'uid': ' ',
            'x': ' ',
            'y': ' ',
            'z': ' ',
        },
    ]


@pytest.fixture
def base_nodes(mocker, base_nodes_base):
    mocker.patch(
        'iotlab_controller.nodes.BaseNodes._fetch_all_nodes',
        return_value=base_nodes_base
    )
    api = mocker.Mock()
    nodes = iotlab_controller.nodes.BaseNodes(
        ['foobar-1.test', 'foobar-2.test'], api=api
    )
    yield nodes


@pytest.fixture
def networked_nodes_base():
    yield [
        {
            'archi': 'foobar',
            'mobile': False,
            'mobility_type': ' ',
            'network_address': 'm3-1.grenoble.iot-lab.info',
            'site': 'grenoble',
            'uid': ' ',
            'x': '53.321',
            'y': '5.32',
            'z': '23.43',
        },
        {
            'archi': 'foobar',
            'mobile': False,
            'mobility_type': ' ',
            'network_address': 'm3-2.grenoble.iot-lab.info',
            'site': 'grenoble',
            'uid': ' ',
            'x': '1.23',
            'y': '3.14',
            'z': '12.24',
        },
    ]


@pytest.fixture
def networked_nodes(mocker, networked_nodes_base):
    api = mocker.Mock()
    api.get_nodes = mocker.Mock(return_value={
        'items': networked_nodes_base
    })
    yield iotlab_controller.nodes.NetworkedNodes(
        'grenoble',
        io.BytesIO(b'm3-1 m3-2 2'),
        api=api,
    )


@pytest.fixture
def sink_networked_nodes(mocker, networked_nodes_base):
    api = mocker.Mock()
    api.get_nodes = mocker.Mock(return_value={
        'items': networked_nodes_base
    })
    yield iotlab_controller.nodes.SinkNetworkedNodes(
        'grenoble',
        'm3-1',
        io.BytesIO(b'm3-1 m3-2 2'),
        api=api,
    )


@pytest.mark.parametrize(
    'mobility_type, uid, x, y, z',
    [(' ', ' ', ' ', ' ', ' '),
     ('testbot', '0123', '0.9', ' ', ' '),
     ('testbot', '0123', '0.9', '0.134', ' '),
     ('testbot', '0123', '0.9', '0.134', '4.31')]
)
def test_base_node_init(mocker, mobility_type, uid, x, y, z):
    # pylint: disable=invalid-name, too-many-arguments
    # x, y, z are coordinates..., and we need that many arguments
    api = mocker.Mock()
    node = iotlab_controller.nodes.BaseNode(
        api, 'foobar', 1, mobility_type, 'foobar-1.test', 'test-site', uid,
        x, y, z
    )
    assert node.arch == 'foobar'
    assert node.mobile
    if mobility_type.strip():
        assert node.mobility_type == mobility_type
    else:
        assert node.mobility_type is None
    assert node.uri == 'foobar-1.test'
    assert node.site == 'test-site'
    if uid.strip():
        assert node.uid == uid
    else:
        assert node.uid is None
    if x.strip() and y.strip() and z.strip():
        assert node.x == float(x)
        assert node.y == float(y)
        assert node.z == float(z)
    else:
        assert node.x is None
        assert node.y is None
        assert node.z is None
    assert node.api == api


def test_base_node_hash(base_node):
    assert isinstance(hash(base_node), int)


def test_base_node_str(base_node):
    assert str(base_node) == '<BaseNode: {}>'.format(base_node.uri)


def test_base_node_state_success(mocker, base_node):
    base_node.api.get_nodes = mocker.Mock(return_value={
        'items': [
            {'network_address': base_node.uri, 'state': 'Running'},
            {'network_address': 'foobar-2.test', 'state': 'Running'},
        ]
    })
    assert base_node.state == 'Running'


def test_base_node_state_error_list_empty(mocker, base_node):
    base_node.api.get_nodes = mocker.Mock(return_value={'items': []})
    with pytest.raises(iotlab_controller.nodes.NodeError):
        assert base_node.state


def test_base_node_state_error_not_in_list(mocker, base_node):
    base_node.api.get_nodes = mocker.Mock(return_value={
        'items': [
            {'network_address': 'foobar-2.test', 'state': 'Running'},
        ]
    })
    with pytest.raises(iotlab_controller.nodes.NodeError):
        assert base_node.state


def test_base_node_distance_error(mocker, base_node):
    api = mocker.Mock()
    other = iotlab_controller.nodes.BaseNode(
        api, 'foobar', 0, '', 'foobar-1.test', 'test-site', '',
        '0.21', ' ', ' '
    )
    with pytest.raises(iotlab_controller.nodes.NodeError):
        base_node.distance(other)
    with pytest.raises(iotlab_controller.nodes.NodeError):
        other.distance(base_node)
    other = iotlab_controller.nodes.BaseNode(
        api, 'foobar', 0, '', 'foobar-1.test', 'test-site2', '',
        '0.21', '1.34', '3.14'
    )
    with pytest.raises(iotlab_controller.nodes.NodeError):
        base_node.distance(other)


def test_base_node_flash(mocker, base_node):
    node_command = mocker.patch('iotlabcli.node.node_command')
    firmware = mocker.Mock()
    assert base_node.flash(12345, firmware) == node_command.return_value
    node_command.assert_called_once_with(base_node.api, 'flash', 12345,
                                         [base_node.uri], firmware.path)


def test_base_node_reset(mocker, base_node):
    node_command = mocker.patch('iotlabcli.node.node_command')
    assert base_node.reset(12345) == node_command.return_value
    node_command.assert_called_once_with(base_node.api, 'reset', 12345,
                                         [base_node.uri])


def test_base_node_start(mocker, base_node):
    node_command = mocker.patch('iotlabcli.node.node_command')
    assert base_node.start(12345) == node_command.return_value
    node_command.assert_called_once_with(base_node.api, 'start', 12345,
                                         [base_node.uri])


def test_base_node_stop(mocker, base_node):
    node_command = mocker.patch('iotlabcli.node.node_command')
    assert base_node.stop(12345) == node_command.return_value
    node_command.assert_called_once_with(base_node.api, 'stop', 12345,
                                         [base_node.uri])


def test_base_node_profile(mocker, base_node):
    node_command = mocker.patch('iotlabcli.node.node_command')
    profile = mocker.Mock()
    assert base_node.profile(12345, profile) == node_command.return_value
    node_command.assert_called_once_with(base_node.api, 'profile', 12345,
                                         [base_node.uri], profile)


def test_base_node_to_dict(base_node, base_node_dict):
    assert base_node.to_dict() == base_node_dict


def test_base_node_to_json(base_node, base_node_dict):
    assert json.loads(base_node.to_json()) == base_node_dict


def test_base_node_from_json(mocker):
    api = mocker.Mock
    args = {
        'archi': 'foobar',
        'mobile': 1,
        'mobility_type': '    ',
        'network_address': 'foobar-1.test',
        'site': 'test-site',
        'uid': '         \n',
        'x': '     ',
        'y': '     ',
        'z': '  ',
    }

    node1 = iotlab_controller.nodes.BaseNode.from_json(json.dumps(args), api)
    node2 = iotlab_controller.nodes.BaseNode(api, **args)

    assert hash(node1) == hash(node2)


def test_base_nodes_all_nodes(mocker):
    api = mocker.Mock()
    args = {
        'archi': 'foobar',
        'mobile': 1,
        'mobility_type': '    ',
        'network_address': 'foobar-1.test',
        'site': 'test-site',
        'uid': '         \n',
        'x': '     ',
        'y': '     ',
        'z': '  ',
    }
    api.get_nodes = mocker.Mock(return_value={'items': [args]})
    res = iotlab_controller.nodes.BaseNodes.all_nodes(
        archi='foobar',
        state='Running',
        site='test-site',
        api=api,
    )
    assert isinstance(res, iotlab_controller.nodes.BaseNodes)
    api.get_nodes.assert_called_with(archi='foobar', state='Running',
                                     site='test-site')
    assert len(res.nodes) == 1
    exp_node = iotlab_controller.nodes.BaseNode(api, **args)
    assert hash(res.nodes['foobar-1.test']) == hash(exp_node)


def test_base_nodes_add_error_node_not_exist(mocker):
    mocker.patch(
        'iotlab_controller.nodes.BaseNodes._fetch_all_nodes',
        return_value=[]
    )
    nodes = iotlab_controller.nodes.BaseNodes()
    with pytest.raises(iotlab_controller.nodes.NodeError):
        nodes.add('foobar-3.test')


def test_base_nodes_flash(mocker, base_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    firmware = mocker.Mock()
    res = base_nodes.flash(12345, firmware)
    assert res == node_command.return_value
    node_command.assert_called_once_with(base_nodes.api, 'flash', 12345,
                                         ['foobar-1.test', 'foobar-2.test'],
                                         firmware.path)


def test_base_nodes_reset(mocker, base_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    res = base_nodes.reset(12345)
    assert res == node_command.return_value
    node_command.assert_called_once_with(base_nodes.api, 'reset', 12345,
                                         ['foobar-1.test', 'foobar-2.test'])


def test_base_nodes_start(mocker, base_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    res = base_nodes.start(12345)
    assert res == node_command.return_value
    node_command.assert_called_once_with(base_nodes.api, 'start', 12345,
                                         ['foobar-1.test', 'foobar-2.test'])


def test_base_nodes_stop(mocker, base_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    res = base_nodes.stop(12345)
    assert res == node_command.return_value
    node_command.assert_called_once_with(base_nodes.api, 'stop', 12345,
                                         ['foobar-1.test', 'foobar-2.test'])


def test_base_nodes_profile(mocker, base_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    profile = mocker.Mock()
    res = base_nodes.profile(12345, profile)
    assert res == node_command.return_value
    node_command.assert_called_once_with(base_nodes.api, 'profile', 12345,
                                         ['foobar-1.test', 'foobar-2.test'],
                                         profile)


def test_base_nodes_to_json(base_nodes):
    exp = {
        'foobar-1.test': {'arch': 'foobar',
                          'mobile': False,
                          'mobility_type': None,
                          'site': 'test-site',
                          'uid': None,
                          'uri': 'foobar-1.test',
                          'x': None,
                          'y': None,
                          'z': None},
        'foobar-2.test': {'arch': 'foobar',
                          'mobile': False,
                          'mobility_type': None,
                          'site': 'test-site',
                          'uid': None,
                          'uri': 'foobar-2.test',
                          'x': None,
                          'y': None,
                          'z': None},
    }
    assert json.loads(base_nodes.to_json()) == exp


def test_base_nodes_from_json(mocker, base_nodes, base_nodes_base):
    api = mocker.Mock()
    nodes = base_nodes.from_json(json.dumps(
        {n['network_address']: n for n in base_nodes_base}
    ), api=api)
    assert len(nodes) == len(base_nodes)
    for uri in base_nodes.nodes:
        assert hash(nodes[uri]) == hash(base_nodes[uri])


def test_networked_nodes_str(networked_nodes):
    assert str(networked_nodes) == '9604883f'


def test_networked_nodes_leafs(networked_nodes):
    assert networked_nodes.leafs == ['m3-1', 'm3-2']


def test_networked_nodes_add_node(mocker, networked_nodes):
    add = mocker.patch(
        'iotlab_controller.nodes.NetworkedNodes.add',
    )
    assert networked_nodes.add_node('m3-4') == add.return_value


def test_networked_nodes_add_edge(mocker, networked_nodes, base_nodes):
    add = mocker.patch(
        'iotlab_controller.nodes.NetworkedNodes.add',
    )
    networked_nodes.add_edge(base_nodes['foobar-1.test'],
                             base_nodes['foobar-2.test'],
                             weight=1.5)
    add.assert_any_call('foobar-1')
    add.assert_any_call('foobar-2')


def test_networked_nodes_neighbors(networked_nodes):
    assert list(networked_nodes.neighbors('m3-1')) == ['m3-2']


def test_sink_networked_nodes_str(sink_networked_nodes):
    assert str(sink_networked_nodes) == 'm3-1x9604883f'


def test_sink_networked_nodes_non_sink_node_uris(sink_networked_nodes):
    assert sink_networked_nodes.non_sink_node_uris == \
        set(('m3-2.grenoble.iot-lab.info',))


def test_sink_networked_nodes_non_sink_nodes(sink_networked_nodes):
    assert sink_networked_nodes.non_sink_nodes == ['m3-2']


def test_sink_networked_nodes_flash_wo_sink(mocker, sink_networked_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    firmware = mocker.Mock()
    res = sink_networked_nodes.flash(12345, firmware)
    assert res == node_command.return_value
    node_command.assert_called_once_with(
        sink_networked_nodes.api, 'flash', 12345,
        ['m3-1.grenoble.iot-lab.info', 'm3-2.grenoble.iot-lab.info'],
        firmware.path
    )


def test_sink_networked_nodes_flash_same_sink_firmware(mocker,
                                                       sink_networked_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    firmware = mocker.Mock()
    res = sink_networked_nodes.flash(12345, firmware, firmware)
    assert res == node_command.return_value
    node_command.assert_called_once_with(
        sink_networked_nodes.api, 'flash', 12345,
        ['m3-1.grenoble.iot-lab.info', 'm3-2.grenoble.iot-lab.info'],
        firmware.path
    )


@pytest.mark.parametrize(
    'node_command_results, exp_res', [
        (
            [{'0': ['abc', 'test']}, {'0': ['def', 'foobar']}],
            {'0': ['abc', 'def', 'foobar', 'test']}
        ),
        (
            [{'0': ['abc', 'test']}, {'1': ['def', 'foobar']}],
            {'0': ['abc', 'test'], '1': ['def', 'foobar']}
        ),
        (
            [{'1': ['abc', 'test']}, {'0': ['def', 'foobar']}],
            {'1': ['abc', 'test'], '0': ['def', 'foobar']}
        ),
        (
            [{'1': ['abc', 'test']}, {'1': ['def', 'foobar']}],
            {'1': ['abc', 'def', 'foobar', 'test']}
        ),
    ]
)
def test_sink_networked_nodes_flash_w_sink(mocker, sink_networked_nodes,
                                           node_command_results, exp_res):
    node_command = mocker.patch(
        'iotlabcli.node.node_command',
        side_effect=node_command_results)
    firmware = mocker.Mock()
    sink_firmware = mocker.Mock()
    res = sink_networked_nodes.flash(12345, firmware, sink_firmware)
    assert res == exp_res
    node_command.assert_any_call(
        sink_networked_nodes.api, 'flash', 12345,
        ['m3-1.grenoble.iot-lab.info'],
        sink_firmware.path
    )
    node_command.assert_any_call(
        sink_networked_nodes.api, 'flash', 12345,
        ['m3-2.grenoble.iot-lab.info'],
        firmware.path
    )


def test_sink_networked_nodes_profile_wo_sink(mocker, sink_networked_nodes):
    node_command = mocker.patch('iotlabcli.node.node_command')
    profile = mocker.Mock()
    res = sink_networked_nodes.profile(12345, profile)
    assert res == node_command.return_value
    node_command.assert_called_once_with(
        sink_networked_nodes.api, 'profile', 12345,
        ['m3-1.grenoble.iot-lab.info', 'm3-2.grenoble.iot-lab.info'],
        profile
    )


@pytest.mark.parametrize(
    'node_command_results, exp_res', [
        (
            [{'0': ['abc', 'test']}, {'0': ['def', 'foobar']}],
            {'0': ['abc', 'def', 'foobar', 'test']}
        ),
        (
            [{'0': ['abc', 'test']}, {'1': ['def', 'foobar']}],
            {'0': ['abc', 'test'], '1': ['def', 'foobar']}
        ),
        (
            [{'1': ['abc', 'test']}, {'0': ['def', 'foobar']}],
            {'1': ['abc', 'test'], '0': ['def', 'foobar']}
        ),
        (
            [{'1': ['abc', 'test']}, {'1': ['def', 'foobar']}],
            {'1': ['abc', 'def', 'foobar', 'test']}
        ),
    ]
)
def test_sink_networked_nodes_profile_w_sink(mocker, sink_networked_nodes,
                                             node_command_results, exp_res):
    node_command = mocker.patch(
        'iotlabcli.node.node_command',
        side_effect=node_command_results)
    profile = mocker.Mock()
    sink_profile = mocker.Mock()
    res = sink_networked_nodes.profile(12345, profile, sink_profile)
    assert res == exp_res
    node_command.assert_any_call(
        sink_networked_nodes.api, 'profile', 12345,
        ['m3-1.grenoble.iot-lab.info'],
        sink_profile
    )
    node_command.assert_any_call(
        sink_networked_nodes.api, 'profile', 12345,
        ['m3-2.grenoble.iot-lab.info'],
        profile
    )
