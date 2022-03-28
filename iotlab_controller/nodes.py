# Copyright (C) 2019-21 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import hashlib
import json
import logging
import math

import iotlabcli.node
try:
    import networkx
except ImportError:                     # pragma: no cover
    logging.warning("Can't import networkx, you won't be able to use "
                    "NetworkedNodes")   # pragma: no cover

from iotlab_controller import common


class NodeError(Exception):
    pass


class BaseNode:
    # pylint: disable=too-many-instance-attributes
    # Maybe fix later
    def __init__(self, api, archi, mobile, mobility_type, network_address,
                 site, uid, x, y, z, *args, **kwargs):
        # pylint: disable=too-many-arguments, unused-argument, invalid-name
        # Maybe fix later
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
            # pylint: disable=invalid-name
            # These are coordinates...
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
        return f"<{type(self).__name__}: {self.uri}>"

    @property
    def state(self):
        nodes = self.api.get_nodes(site=self.site,
                                   archi=self.arch)["items"]
        for node in nodes:
            if node["network_address"] == self.uri:
                return node["state"]
        raise NodeError("Unable to get node state")

    def distance(self, other):
        if (self.x is None) or (other.x is None) or (self.site != other.site):
            raise NodeError("Unable to determine distance of nodes "
                            f"{self} and {other}")
        return math.sqrt((self.x - other.x) ** 2 +
                         (self.y - other.y) ** 2 +
                         (self.z - other.z) ** 2)

    def flash(self, exp_id, firmware):
        return iotlabcli.node.node_command(self.api, "flash", exp_id,
                                           [self.uri], firmware.path)

    def reset(self, exp_id):
        return iotlabcli.node.node_command(self.api, "reset", exp_id,
                                           [self.uri])

    def start(self, exp_id):
        return iotlabcli.node.node_command(self.api, "start", exp_id,
                                           [self.uri])

    def stop(self, exp_id):
        return iotlabcli.node.node_command(self.api, "stop", exp_id,
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


class BaseNodes:
    def __init__(self, node_list=None, state=None, api=None,
                 node_class=BaseNode):
        if node_list is None:
            node_list = []
        self.state = state
        if api is None:
            self.api = common.get_default_api()
        else:
            self.api = api
        self.nodes = {
            args["network_address"]: node_class.from_dict(args, api=self.api)
            for args in self._fetch_all_nodes()
            if args["network_address"] in node_list
        }
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
        return self._from_existing_nodes(nodes, state=self.state, api=self.api,
                                         node_class=self.node_class)

    @classmethod
    def all_nodes(cls, *args, site=None, state=None, archi=None, api=None,
                  node_class=BaseNode, **kwargs):
        # pylint: disable=unexpected-keyword-arg
        # Maybe fix later
        res = cls(state=state, api=api, node_class=node_class,
                  *args, **kwargs)
        # pylint: disable=protected-access
        # Access to protected method of class within class method
        res.nodes = {
            n["network_address"]: node_class.from_dict(n, api=res.api)
            for n in res._fetch_all_nodes(site=site, archi=archi)
        }
        return res

    @classmethod
    def _from_existing_nodes(cls, nodes, state=None, api=None,
                             node_class=BaseNode):
        res = cls(state=state, api=api, node_class=node_class)
        res.nodes = nodes
        return res

    def _fetch_all_nodes(self, site=None, archi=None):
        kwargs = {}
        if archi is not None:
            kwargs["archi"] = archi
        if self.state is not None:
            kwargs["state"] = self.state
        if site is not None:
            kwargs["site"] = site
        return self.api.get_nodes(**kwargs)["items"]

    @property
    def arglist(self):
        """
        >>> nodes = BaseNodes()
        >>> nodes.add("m3-1.paris.iot-lab.info")
        >>> nodes.add("m3-3.paris.iot-lab.info")
        >>> nodes.arglist
        'paris,m3,1+3'
        """
        site = None
        arch = None
        arch_name = None
        node_nums = []
        for node in self:
            if site is None:
                site = node.site
            if arch is None:
                arch = node.arch
            if node.site != site:
                raise AttributeError(
                    "Can not produce arglist, nodes have different sites"
                )   # pragma: no cover
            if node.arch != arch:
                raise AttributeError(
                    "Can not produce arglist, nodes have different archs"
                )   # pragma: no cover
            if arch_name is None:
                arch_name = node.uri.split('.')[0].split('-')[0]
            node_nums.append(node.uri.split('.')[0].split('-')[1])
        return f"{site},{arch_name},{'+'.join(node_nums)}"

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
                res = self.node_class.from_dict(args, api=self.api)
                self.nodes[node] = res
                return
        raise NodeError(f"Can't load node information on {node}")

    def flash(self, exp_id, firmware):
        return iotlabcli.node.node_command(self.api, "flash", exp_id,
                                           [n.uri for n in self],
                                           firmware.path)

    def reset(self, exp_id):
        return iotlabcli.node.node_command(self.api, "reset", exp_id,
                                           [n.uri for n in self])

    def start(self, exp_id):
        return iotlabcli.node.node_command(self.api, "start", exp_id,
                                           [n.uri for n in self])

    def stop(self, exp_id):
        return iotlabcli.node.node_command(self.api, "stop", exp_id,
                                           [n.uri for n in self])

    def profile(self, exp_id, profile):
        return iotlabcli.node.node_command(self.api, "profile", exp_id,
                                           [n.uri for n in self],
                                           profile)

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
        nodes_ = {k: v for k, v in self.nodes.copy().items() if k in nodes}
        return self._from_existing_nodes(nodes_, state=self.state,
                                         api=self.api,
                                         node_class=self.node_class)

    def to_json(self):
        return json.dumps({n: self.nodes[n].to_dict()
                           for n in self.nodes})

    @classmethod
    def from_json(cls, obj, state=None, api=None, node_class=BaseNode):
        nodes = json.loads(obj)
        nodes = {k: node_class.from_dict(v, api) for k, v in nodes.items()}
        return cls._from_existing_nodes(nodes, state, api, node_class)


class NetworkedNodes(BaseNodes):
    def __init__(self, site, edgelist_file=None, state=None,
                 weight_distance=True, api=None, node_class=BaseNode):
        # pylint: disable=too-many-arguments
        # Maybe fix later
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 2\\nm3-2 m3-3 1"
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
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 2\\nm3-2 m3-3 1"
        ...     ),
        ...     weight_distance=False,
        ... )
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.grenoble.iot-lab.info
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        """
        self.site = site
        if edgelist_file is not None:
            self.network = networkx.read_edgelist(edgelist_file,
                                                  data=[("weight", float)])
            super().__init__(
                [common.get_uri(site, n) for n in self.network.nodes()],
                state, api, node_class
            )
            info = {n: self[n] for n in self.network.nodes()}
            networkx.set_node_attributes(self.network, info, "info")
            if weight_distance:
                for node1, node2 in self.network.edges():
                    info1 = self[node1]
                    info2 = self[node2]
                    edge = self.network[node1][node2]
                    edge["weight"] = info1.distance(info2)
        else:
            self.network = networkx.Graph()
            super().__init__(state=state, api=api, node_class=node_class)

    def __getitem__(self, node):
        if not self._is_uri(node):
            node = common.get_uri(self.site, node)
        return super().__getitem__(node)

    def __delitem__(self, node):
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 2\\nm3-2 m3-3 1"
        ...     )
        ... )
        >>> del nodes["m3-1"]
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        >>> del nodes["m3-3.grenoble.iot-lab.info"]
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-2.grenoble.iot-lab.info
        """
        if self._is_uri(node):
            uri = node
            node = node.split(".")[0]
        else:
            uri = common.get_uri(self.site, node)
        self.network.remove_node(node)
        super().__delitem__(uri)

    def __add__(self, other):
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble", io.BytesIO(b"m3-1 m3-2 2"))
        >>> nodes += NetworkedNodes("grenoble", io.BytesIO(b"m3-2 m3-3 1"))
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.grenoble.iot-lab.info
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        """
        res = super().__add__(other)
        res.network = networkx.compose(self.network, other.network)
        return res

    @classmethod
    def _from_existing_nodes(cls, nodes, site=None, state=None, api=None,
                             node_class=BaseNode):
        # pylint: disable=too-many-arguments,arguments-differ,arguments-renamed
        # Maybe fix later
        # Adds additional, but optional arguments
        res = cls(site=site, state=state, api=api, node_class=node_class)
        res.nodes = nodes
        return res

    def _network_digest(self):
        edges = sorted(tuple(sorted([a, b])) for a, b in self.network.edges)
        return hashlib.sha512(str(edges).encode()).hexdigest()[:8]

    def __str__(self):
        return f"{self._network_digest()}"

    def _is_uri(self, node):
        return f".{self.site}." in node

    @property
    def leafs(self):
        return [n for n in self.network.nodes
                if len(list(self.network.neighbors(n))) == 1]

    @classmethod
    def all_nodes(cls, *args, site=None, state=None, archi=None, api=None,
                  node_class=BaseNode, **kwargs):
        res = cls(site=site, state=state, api=api, node_class=node_class,
                  *args, **kwargs)
        # pylint: disable=protected-access
        # Access to protected method of class within class method
        res.nodes = {
            n["network_address"]: node_class.from_dict(n, api=res.api)
            for n in res._fetch_all_nodes(site=site, archi=archi)
        }
        return res

    def add(self, node):
        """
        >>> nodes = NetworkedNodes("saclay")
        >>> nodes.add("m3-1")
        >>> nodes.add("m3-1.saclay.iot-lab.info")
        >>> nodes.add("m3-2.saclay.iot-lab.info")
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.saclay.iot-lab.info
        m3-2.saclay.iot-lab.info
        >>> for n in sorted(nodes.network.nodes()):
        ...     print(nodes.network.nodes[n]["info"].uri)
        m3-1.saclay.iot-lab.info
        m3-2.saclay.iot-lab.info
        """
        if self._is_uri(node):
            uri = node
            node = uri.split(".")[0]
        else:
            uri = common.get_uri(self.site, node)
        if uri in self.nodes:
            return
        super().add(uri)
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
        if isinstance(node1, BaseNode):
            node1 = node1.uri.split(".")[0]
        if isinstance(node2, BaseNode):
            node2 = node2.uri.split(".")[0]
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
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 2\\nm3-2 m3-3 1"
        ...     )
        ... )
        >>> nodes = nodes.select(['m3-2', 'm3-3.grenoble.iot-lab.info'])
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        """
        res = super().select([
            n if self._is_uri(n) else common.get_uri(self.site, n)
            for n in nodes
        ])
        res.network = networkx.Graph(self.network.subgraph(nodes))
        return res

    def save_edgelist(self, path):
        """
        >>> import io
        >>> nodes = NetworkedNodes("grenoble",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 2\\nm3-2 m3-3 1"
        ...     )
        ... )
        >>> out = io.BytesIO()
        >>> nodes.save_edgelist(out)
        >>> out.getvalue()
        b'm3-1 m3-2 0.5999999999999979\\nm3-2 m3-3 0.6000000000000014\\n'
        """
        networkx.write_edgelist(self.network, path, data=["weight"])


class SinkNetworkedNodes(NetworkedNodes):
    def __init__(self, site, sink, edgelist_file=None, state=None,
                 weight_distance=True, api=None, node_class=BaseNode):
        # pylint: disable=too-many-arguments
        # Maybe fix later
        super().__init__(site, edgelist_file, state, weight_distance, api,
                         node_class)
        self.sink = sink
        self.add(sink)

    def __str__(self):
        return f"{self.sink}x{self._network_digest()}"

    def __iter__(self):
        """
        >>> import io
        >>> nodes = SinkNetworkedNodes("grenoble", "m3-2",
        ...     io.BytesIO(
        ...         b"m3-1 m3-2 2\\nm3-2 m3-3 1"
        ...     )
        ... )
        >>> for n in sorted(nodes, key=lambda n: n.uri):
        ...     print(n.uri)
        m3-1.grenoble.iot-lab.info
        m3-2.grenoble.iot-lab.info
        m3-3.grenoble.iot-lab.info
        >>> for n in nodes:
        ...     print(n.uri)
        ...     break
        m3-2.grenoble.iot-lab.info
        """
        sink_uri = common.get_uri(self.site, self.sink)
        # ensure sink to be first
        yield self[sink_uri]
        for node in self.nodes:
            if node != sink_uri:
                yield self[node]

    @property
    def non_sink_node_uris(self):
        return set(n for n in self.nodes
                   if n != common.get_uri(self.site, self.sink))

    @property
    def non_sink_nodes(self):
        return [n for n in self.network.nodes() if n != self.sink]

    def flash(self, exp_id, firmware, sink_firmware=None):
        # pylint: disable=arguments-differ
        # Adds additional, but optional arguments
        if sink_firmware is None or sink_firmware == firmware:
            return super().flash(exp_id, firmware)
        res1 = iotlabcli.node.node_command(
                self.api, "flash", exp_id, list(self.non_sink_node_uris),
                firmware.path
            )
        res2 = iotlabcli.node.node_command(
                self.api, "flash", exp_id,
                [common.get_uri(self.site, self.sink)],
                sink_firmware.path
            )
        for res in ['0', '1']:
            if res in res1 and res in res2:
                res1[res].extend(res2[res])
                res1[res].sort()
            elif res not in res1 and res in res2:
                res1[res] = res2[res]
        return res1

    def profile(self, exp_id, profile, sink_profile=None):
        # pylint: disable=arguments-differ
        # Adds additional, but optional arguments
        if sink_profile is None:
            return super().profile(exp_id, profile)
        res1 = iotlabcli.node.node_command(
                self.api, "profile", exp_id, list(self.non_sink_node_uris),
                profile
            )
        res2 = iotlabcli.node.node_command(
                self.api, "profile", exp_id,
                [common.get_uri(self.site, self.sink)],
                sink_profile
            )
        for res in ['0', '1']:
            if res in res1 and res in res2:
                res1[res].extend(res2[res])
                res1[res].sort()
            elif res not in res1 and res in res2:
                res1[res] = res2[res]
        return res1
