# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2019 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import json
import math

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

    def repr_json(self):
        return {k: v for k, v in self.__dict__.items() if k not in ["api"]}

    def to_json(self):
        return json.dumps(self,
                          default=lambda o: o.repr_json(),
                          sort_keys=True, indent=4)

    @staticmethod
    def from_json(obj, api):
        return BaseNode(api, **json.loads(obj))


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

    def to_json(self):
        return json.dumps({n: self.nodes[n].repr_json()
                           for n in self.nodes})
