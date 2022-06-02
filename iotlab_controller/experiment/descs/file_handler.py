# Copyright (C) 2021 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import abc
import json

import yaml


GLOBAL_EXP_KEYS = ['duration', 'env', 'firmwares', 'name', 'nodes', 'profiles',
                   'run_name', 'results_dir', 'run_wait', 'sink_firmware',
                   'serial_aggregator_color', 'site', 'target_args', 'tmux']
REQUIRED_EXP_KEYS = ['name']
EXP_RUN_KEYS = {
    'env': 'env',
    'firmwares': 'firmwares',
    'name': 'run_name',
    'profiles': 'profiles',
    'wait': 'run_wait',
    'serial_aggregator_color': 'serial_aggregator_color',
    'sink_firmwares': 'sink_firmware',
    'site': 'site',
    'tmux': 'tmux'
}
FIRMWARE_ENCLOSURE_KEYS = {
    'env': 'env',
}


class DescriptionError(Exception):
    pass


class NestedDescriptionBase(dict):
    def __init__(self, *args, enclosure=None, enclosure_keys=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._enclosure = enclosure
        if enclosure_keys is None:
            self._enclosure_keys = {}
        elif isinstance(enclosure_keys, dict):
            self._enclosure_keys = enclosure_keys
        else:
            self._enclosure_keys = {k: k for k in enclosure_keys}

    def _in_enclosure(self, key):
        return not super().__contains__(key) and self._enclosure and \
               key in self._enclosure_keys

    def __contains__(self, key):
        if self._in_enclosure(key):
            return self._enclosure_keys[key] in self._enclosure
        return super().__contains__(key)

    def __getitem__(self, key):
        if self._in_enclosure(key):
            return self._enclosure[self._enclosure_keys[key]]
        return super().__getitem__(key)

    def get(self, key, default=None):
        if self._in_enclosure(key):
            return self._enclosure.get(self._enclosure_keys[key], default)
        return super().get(key, default)

    @property
    def env(self):
        if 'env' not in self._enclosure_keys:
            res = {}
        elif self._enclosure is None:
            res = {}
        elif isinstance(self._enclosure, NestedDescriptionBase):
            res = dict(self._enclosure.env)
        else:
            res = {k: str(v) for k, v
                   in self._enclosure.get('env', {}).items()}
        res.update({k: str(v) for k, v in self.get('env', {}).items()})
        return res


class DescriptionSerializerBase(abc.ABC):
    @abc.abstractmethod
    def load(self, inp):
        raise NotImplementedError()

    @abc.abstractmethod
    def dump(self, outp, descs):
        raise NotImplementedError()


class JSONSerializer(DescriptionSerializerBase):
    def load(self, inp):
        return json.load(inp)

    def dump(self, outp, descs):
        return json.dump(descs, outp)


class YAMLSerializer(DescriptionSerializerBase):
    class _YAMLDumper(yaml.SafeDumper):
        # pylint: disable=too-many-ancestors
        def represent_data(self, data):
            if isinstance(data, NestedDescriptionBase):
                data = dict(data)
            return super().represent_data(data)

    def load(self, inp):
        return yaml.load(inp, Loader=yaml.FullLoader)

    def dump(self, outp, descs):
        return yaml.dump(descs, outp, Dumper=self._YAMLDumper)


class DescriptionSerializerFactory:
    # pylint: disable=too-few-public-methods
    def get_serializer(self, filename):
        if filename.endswith('.json'):
            return JSONSerializer()
        if filename.endswith('.yaml') or \
           filename.endswith('.yml'):
            return YAMLSerializer()
        raise ValueError(f'Unknown file format for {filename}')


_factory = DescriptionSerializerFactory()


class DescriptionFileHandler:
    def __init__(self, filename):
        self._filename = filename
        self._serializer = _factory.get_serializer(filename)

    @property
    def filename(self):
        return self._filename

    @staticmethod
    def _parse_firmware(firmware, enclosure):
        return NestedDescriptionBase(
            firmware, enclosure=enclosure,
            enclosure_keys=FIRMWARE_ENCLOSURE_KEYS
        )

    def _parse_firmwares(self, firmwares, enclosure):
        res = []
        for firmware in firmwares:
            res.append(self._parse_firmware(firmware, enclosure))
        return res

    @staticmethod
    def _parse_run(run, exp):
        res = NestedDescriptionBase(
            run, enclosure=exp,
            enclosure_keys=EXP_RUN_KEYS
        )
        return res

    def _parse_runs(self, runs, exp):
        res = []
        for run in runs:
            res.append(self._parse_run(run, exp))
        return res

    def _parse_experiment(self, exp, globs):
        res = NestedDescriptionBase(
            exp, enclosure=globs,
            enclosure_keys=GLOBAL_EXP_KEYS
        )
        if 'runs' in exp:
            res['runs'] = self._parse_runs(exp['runs'], res)
        else:
            res['runs'] = []
        if 'firmwares' in exp:
            res['firmwares'] = self._parse_firmwares(res['firmwares'], exp)
        if 'sink_firmware' in exp:
            res['sink_firmware'] = self._parse_firmware(res['sink_firmware'],
                                                        exp)
        return res

    def _parse_unscheduled(self, unscheduled_exps, globs):
        res = []
        if isinstance(unscheduled_exps, dict):
            unscheduled_exps = [unscheduled_exps]
        for exp in unscheduled_exps:
            res.append(self._parse_experiment(exp, globs))
        return res

    def load_content(self, content):
        for key in list(content):   # list() so we can change `content`
            if key == 'globals':
                globs = NestedDescriptionBase(content['globals'])
                content['globals'] = globs
                if 'firmwares' in globs:
                    globs['firmwares'] = self._parse_firmwares(
                        globs['firmwares'], globs
                    )
                if 'sink_firmware' in globs:
                    globs['sink_firmware'] = self._parse_firmware(
                        globs['sink_firmware'], globs
                    )
            elif key == 'unscheduled':
                content['unscheduled'] = self._parse_unscheduled(
                    content['unscheduled'], content.get('globals')
                )
            else:
                try:
                    int_key = int(key)
                except ValueError as exc:
                    raise DescriptionError(
                        f"Top level keys must be 'global', 'unscheduled' "
                        f"or a numeric FIT IoT-LAB experiment ID not {key}."
                    ) from exc
                content[int_key] = self._parse_experiment(
                    content[key], content.get('globals'),
                )
                if int_key != key:
                    del content[key]
        return content

    def load(self):
        with open(self.filename, encoding='utf-8') as inp:
            res = self._serializer.load(inp)
            res = self.load_content(res)
        return res

    def dump(self, descs):
        with open(self.filename, 'w', encoding='utf-8') as outp:
            return self._serializer.dump(outp, descs)
