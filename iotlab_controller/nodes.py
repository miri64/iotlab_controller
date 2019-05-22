# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import iotlabcli.node
import hashlib
import json
import logging
import math
try:
    import networkx
except ImportError:
    logging.warning("Can't import networkx, you won't be able to use "
                    "NetworkedNodes")

from iotlab_controller import common


class NodeError(Exception):
    pass


class BaseNode(object):
    def __init__(self, api, archi, mobile, mobility_type, network_address,
                 site, uid, x, y, z, *args, **kwargs):
        self.arch = archi
        self.mobile = mobile != 0
        if mobility_type.strip() != "":
            self.mobility_type = mobility_type
        else:
            self.mobility_type = None
        self.uri = network_address
        self.site = site
        if uid.strip() != "":
            self.uid = uid
        else:
            self.uid = None
        if (x.strip() == "") or (y.strip() == "") or \
           (z.strip() == ""):
            self.x = None
            self.y = None
            self.z = None
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
        self.api = api

    def __hash__(self):
        return hash(self.uri)

    def __str__(self):
        return "<{}: {}>".format(type(self).__name__, self.uri)

    @property
    def state(self):
        nodes = self.api.get_resources(site=self.site,
                                       archi=self.arch)["items"]
        for node in nodes:
            if node["network_address"] == self.uri:
                return node["state"]
        raise NodeError("Unable to get node state")

    def distance(self, other):
        if (self.x is None) or (other.x is None) or (self.site != other.site):
            raise NodeError("Unable to determine distance of nodes {} and {}"
                            .format(self, other))
        return math.sqrt((self.x - other.x) ** 2 +
                         (self.y - other.y) ** 2 +
                         (self.z - other.z) ** 2)

    def flash(self, exp_id, firmware):
        return iotlabcli.node.node_command(self.api, "update", exp_id,
                                           [self.uri], firmware.path)

    def reset(self, exp_id):
        return iotlabcli.node.node_command(self.api, "reset", exp_id,
                                           [self.uri])

    def profile(self, exp_id, profile):
        return iotlabcli.node.node_command(self.api, "profile", exp_id,
                                           [self.uri], profile)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if k not in ["api"]}

    def to_json(self):
        return json.dumps(self,
                          default=lambda o: o.to_dict(),
                          sort_keys=True, indent=4)

    @classmethod
    def from_dict(cls, obj, api):
        return cls(api, **obj)

    @classmethod
    def from_json(cls, obj, api):
        return cls.from_dict(json.loads(obj), api)


class BaseNodes(object):
    def __init__(self, node_list=[], state=None, api=None,
                 node_class=BaseNode):
        self.state = state
        if api is None:
            self.api = common.get_default_api()
        else:
            self.api = api
        self.nodes = {args["network_address"]: node_class(api=self.api, **args)
                      for args in self._fetch_all_nodes()
                      if args["network_address"] in node_list}
        self.node_class = node_class
        self.iter_idx = -1

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        """
        >>> nodes = BaseNodes(["m3-1.lille.iot-lab.info",
        ...                    "m3-2.lille.iot-lab.info"])
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.lille.iot-lab.info
        m3-2.lille.iot-lab.info
        >>> "m3-1.lille.iot-lab.info" in nodes
        True
        """
        for node in self.nodes:
            yield self.nodes[node]

    def __contains__(self, node):
        return node in self.nodes

    def __getitem__(self, node):
        return self.nodes[node]

    def __delitem__(self, node):
        """
        >>> nodes = BaseNodes(["m3-1.lille.iot-lab.info",
        ...                    "m3-2.lille.iot-lab.info"])
        >>> del nodes["m3-1.lille.iot-lab.info"]
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-2.lille.iot-lab.info
        """
        del self.nodes[node]

    def __add__(self, other):
        """
        >>> a = BaseNodes(["m3-1.lille.iot-lab.info",
        ...                "m3-2.lille.iot-lab.info"])
        >>> b = BaseNodes(["m3-2.lille.iot-lab.info",
        ...                "m3-3.lille.iot-lab.info"])
        >>> nodes = a + b
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.lille.iot-lab.info
        m3-2.lille.iot-lab.info
        m3-3.lille.iot-lab.info
        """
        nodes = self.nodes.copy()
        nodes.update(other.nodes)
        return self._from_existing_nodes(nodes, self.state, self.api,
                                         self.node_class)

    @classmethod
    def _from_existing_nodes(cls, nodes, state=None, api=None,
                             node_class=BaseNode):
        res = cls(state=state, api=api, node_class=node_class)
        res.nodes = nodes
        return res

    def _fetch_all_nodes(self):
        kwargs = {}
        if self.state is not None:
            kwargs["state"] = self.state
        return self.api.get_resources(**kwargs)["items"]

    def add(self, node):
        """
        >>> nodes = BaseNodes()
        >>> nodes.add("m3-1.paris.iot-lab.info")
        >>> nodes.add("m3-1.paris.iot-lab.info")
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.paris.iot-lab.info
        """
        if node in self:
            return
        for args in self._fetch_all_nodes():
            if args["network_address"] == node:
                res = self.node_class(api=self.api, **args)
                self.nodes[node] = res
                return
        raise NodeError("Can't load node information on {}".format(node))

    def flash(self, exp_id, firmware):
        return iotlabcli.node.node_command(self.api, "update", exp_id,
                                           self.nodes, firmware.path)

    def reset(self, exp_id):
        return iotlabcli.node.node_command(self.api, "reset", exp_id,
                                           self.nodes)

    def profile(self, exp_id, profile):
        return iotlabcli.node.node_command(self.api, "profile", exp_id,
                                           self.nodes, profile)

    def select(self, nodes):
        """
        >>> a = BaseNodes(["m3-1.lille.iot-lab.info",
        ...                "m3-2.lille.iot-lab.info",
        ...                "m3-3.lille.iot-lab.info"])
        >>> nodes = a.select(["m3-1.lille.iot-lab.info",
        ...                   "m3-2.lille.iot-lab.info"])
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.lille.iot-lab.info
        m3-2.lille.iot-lab.info
        """
        ns = {k: v for k, v in self.nodes.copy().items() if k in nodes}
        return self._from_existing_nodes(ns, self.state, self.api,
                                         self)

    def to_json(self):
        return json.dumps({n: self.nodes[n].to_dict()
                           for n in self.nodes})

    @classmethod
    def from_json(cls, obj, state=None, api=None, node_class=BaseNode):
        nodes = json.loads(obj)
        nodes = {k: node_class.from_repr_json(v) for k, v in nodes.items()}
        return cls._from_existing_nodes(nodes, state, api, node_class)


class NetworkedNodes(BaseNodes):
    def __init__(self, site, edgelist_file=None, weight_distance=True,
                 api=None):
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 {'weight': 2}\\nm3-2 m3-3 {'weight': 1}"
        ...     )
        ... )
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.grenoble.iot-lab.info
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        >>> for n in sorted(nodes.network.nodes()):
        ...     print(nodes.network.nodes[n]["info"].uri)
        m3-1.grenoble.iot-lab.info
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        >>> nodes = NetworkedNodes("grenoble")
        >>> len(nodes)
        0
        """
        self.site = site
        if edgelist_file is not None:
            self.network = networkx.read_edgelist(edgelist_file)
            super(NetworkedNodes, self).__init__(
                [common.get_uri(site, n) for n in self.network.nodes()], api
            )
            info = {n: self[n] for n in self.network.nodes()}
            networkx.set_node_attributes(self.network, info, "info")
            if weight_distance:
                for n1, n2 in self.network.edges():
                    info1 = self[n1]
                    info2 = self[n2]
                    self.network[n1][n2]["weight"] = info1.distance(info2)
        else:
            self.network = networkx.Graph()
            super(NetworkedNodes, self).__init__()

    def __getitem__(self, node):
        return super(NetworkedNodes, self).__getitem__(
                common.get_uri(self.site, node)
            )

    def __delitem__(self, node):
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 {'weight': 2}\\nm3-2 m3-3 {'weight': 1}"
        ...     )
        ... )
        >>> del nodes["m3-1"]
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        """
        super(NetworkedNodes, self).__delitem__(
                common.get_uri(self.site, node)
            )
        self.network.remove_node(node)

    def __add__(self, other):
        res = super(NetworkedNodes, self).__add__(other)
        res.network = networkx.compose(self.network, other.network)
        return res

    def _network_digest(self):
        edges = sorted(tuple(sorted([a, b])) for a, b in self.network.edges)
        return hashlib.sha512(str(edges).encode()).hexdigest()[:8]

    def __str__(self):
        return "{}".format(self._network_digest())

    @property
    def leafs(self):
        return [n for n in self.network.nodes
                if len(list(self.network.neighbors(n))) == 1]

    def add(self, node):
        """
        >>> nodes = NetworkedNodes("saclay")
        >>> nodes.add("m3-1")
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.saclay.iot-lab.info
        >>> for n in sorted(nodes.network.nodes()):
        ...     print(nodes.network.nodes[n]["info"].uri)
        m3-1.saclay.iot-lab.info
        """
        uri = common.get_uri(self.site, node)
        if node in self.nodes:
            return
        super(NetworkedNodes, self).add(uri)
        info = self[node]
        self.network.add_node(node, info=info)

    def add_node(self, node):
        return self.add(node)

    def add_edge(self, node1, node2, weight=None):
        """
        >>> nodes = NetworkedNodes("saclay")
        >>> nodes.add_edge("m3-1", "m3-3")
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.saclay.iot-lab.info
        m3-3.saclay.iot-lab.info
        >>> for n in sorted(nodes.network.edges()):
        ...     print(sorted(n), nodes.network[n[0]][n[1]]["weight"])
        ['m3-1', 'm3-3'] 1.6
        """
        self.add(node1)
        self.add(node2)
        if weight is None:
            info1 = self[node1]
            info2 = self[node2]
            weight = info1.distance(info2)
        self.network.add_edge(node1, node2, weight=weight)

    def neighbors(self, node):
        return self.network.neighbors(node)

    def select(self, nodes):
        res = super(NetworkedNodes, self).select([common.get_uri(n)
                                                  for n in nodes])
        res.network = networkx.Graph(self.network.subgraph(nodes))
        return res

    def save_edgelist(self, path):
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 {'weight': 2}\\nm3-2 m3-3 {'weight': 1}"
        ...     )
        ... )
        >>> out = io.BytesIO()
        >>> nodes.save_edgelist(out)
        >>> out.getvalue()
        b'm3-1 m3-2 0.5999999999999979\\nm3-2 m3-3 0.6000000000000014\\n'
        """
        networkx.write_edgelist(self.network, path, data=["weight"])


class SinkNetworkedNodes(NetworkedNodes):
    def __init__(self, site, sink, edgelist_file=None, weight_distance=True,
                 api=None):
        super(SinkNetworkedNodes, self).__init__(site, edgelist_file,
                                                 weight_distance, api)
        self.sink = sink

    def __str__(self):
        return "{}x{}".format(self.sink, self._network_digest())

    @property
    def non_sink_node_uris(self):
        return set(n for n in self.nodes
                   if n != common.get_uri(self.site, self.sink))

    @property
    def non_sink_nodes(self):
        return [n for n in self.network.nodes() if n != self.sink]

    def flash(self, exp_id, firmware, sink_firmware=None):
        if sink_firmware is None:
            return super(SinkNetworkedNodes, self).flash(exp_id, firmware)
        else:
            res1 = iotlabcli.node.node_command(
                    self.api, "update", exp_id, self.non_sink_node_uris,
                    firmware.path
                )
            res2 = iotlabcli.node.node_command(
                    self.api, "update", exp_id, [self.sink], sink_firmware.path
                )
            res1.update(res2)
            return res1

    def profile(self, exp_id, profile, sink_profile=None):
        if sink_profile is None:
            return super(SinkNetworkedNodes, self).profile(exp_id, profile)
        else:
            res1 = iotlabcli.node.node_command(
                    self.api, "profile", exp_id, self.non_sink_node_uris,
                    profile
                )
            res2 = iotlabcli.node.node_command(
                    self.api, "profile", exp_id, [self.sink],
                    sink_profile
                )
            res1.update(res2)
            return res1
