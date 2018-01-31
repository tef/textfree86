"""rson.objects

registry of objects sent/recieved on the wire. 
"""

from collections import OrderedDict
from urllib.parse import urljoin

from .rson import Codec, reserved_tags, CONTENT_TYPE

import werkzeug.exceptions as wz

class NotFound(wz.NotFound): pass
class Forbidden(wz.Forbidden): pass
class NotImplemented(wz.NotImplemented): pass
class MethodNotAllowed(wz.MethodNotAllowed): pass

class ServiceError:
    pass

class MethodNotAllowed:
    pass

class Forbidden:
    pass

class Registry:
    def __init__(self):
        self.classes = OrderedDict()
        self.tag_for = OrderedDict()
        self.codec = Codec(self.as_tagged, self.from_tagged)
        self.content_type = self.codec.content_type

    def parse(self, buf, transform):
        return self.codec.parse(buf, transform)
    
    def dump(self, obj, transform):
        return self.codec.dump(obj, transform)

    def add(self, name=None):
        def _add(cls):
            n = cls.__name__ if name is None else name
            if n in reserved_tags:
                raise InvalidTag(
                    name, "Can't tag {} with {}, {} is reserved".format(cls, name, name))
            self.classes[n] = cls
            self.tag_for[cls] = n
            return cls
        return _add

    def as_tagged(self, obj):
        if obj.__class__ == TaggedObject:
            return obj.name, obj.value
        elif obj.__class__ in self.tag_for:
            name = self.tag_for[obj.__class__]
            return name, OrderedDict(obj.__dict__)
        else:
            raise InvalidTag('unknown',
                "Can't find tag for object {}: unknown class {}".format(obj, obj.__class__))

    def from_tagged(self, name, value):
        if name in reserved_tags:
            raise InvalidTag(
                name, "Can't use tag {} with {}, {} is reserved".format(value, name, name))

        if name in self.classes:
            return self.classes[name](**value)
        else:
            return TaggedObject(name, value)


registry = Registry()

class InvalidTag(Exception):
    def __init__(self, name, reason):
        self.name = name
        Exception.__init__(self, reason)

class TaggedObject:
    def __init__(self, name, value):
        self.name, self.value = name,value

    def __repr__(self):
        return "<{} {}>".format(self.name, self.value)

class Hyperlink:
    pass

@registry.add()
class Link(Hyperlink):
    def __init__(self, url, value=None):
        self.url = url
        self.value = value

@registry.add()
class Form(Hyperlink):
    def __init__(self, url, arguments, defaults=None):
        self.url = url
        self.arguments = arguments
        self.defaults = defaults

@registry.add()
class Waiter(Hyperlink):
    def __init__(self, metadata):
        self.metadata = metadata

    @property
    def url(self):
        return self.metadata['url']

@registry.add()
class Dataset(Hyperlink):
    def __init__(self, kind, metadata):
        self.kind = kind
        self.metadata = metadata

    @property
    def url(self):
        return self.metadata['url']

@registry.add()
class Service(Hyperlink):
    def __init__(self, kind, metadata, attributes):
        self.kind = kind
        self.metadata = metadata
        self.attributes = attributes

    @property
    def url(self):
        return self.metadata['url']


@registry.add()
class List(Hyperlink):
    def __init__(self, kind, metadata, items):
        self.kind = kind
        self.items = items
        self.metadata = OrderedDict(metadata)

@registry.add()
class Resource(Hyperlink):
    def __init__(self, kind, metadata, attributes):
        self.kind = kind
        self.attributes = attributes
        self.metadata = OrderedDict(metadata)

    @property
    def url(self):
        return self.metadata['url']

@registry.add()
class Struct:
    def __init__(self, kind, names, values):
        self.kind = kind
        self.names = names
        self.values = values

@registry.add()
class Request:
    def __init__(self,method, url, params, headers, data):
        self.method = method
        self.url = url
        self.headers = headers
        self.params = params
        self.data = data

@registry.add()
class Response:
    def __init__(self, code, status, headers, data):
        self.code = code
        self.status = status
        self.headers = headers
        self.data = data
class Operator:
    ops = Registry()
    class Operator:
        def __init__(self, key, value):
            self.key = key
            self.value = value

    @ops.add()
    class Equals(Operator):pass

    @ops.add()
    class NotEquals(Operator):pass

    @ops.add()
    class LessThan(Operator):pass

    @ops.add()
    class GreaterThan(Operator):pass

    @ops.add()
    class LessEqualTo(Operator):pass

    @ops.add()
    class GreaterEqualTo(Operator):pass

    @ops.add()
    class In(Operator):pass

    @ops.add()
    class NotIn(Operator):pass

    @ops.add()
    class Exists:
        def __init__(self, key): self.key = key

    @ops.add()
    class NotExists:
        def __init__(self, key): self.key = key

    @ops.add()
    class All:pass



def parse(obj, transform=None):
    return registry.parse(obj, transform)

def dump(obj, transform=None):
    return registry.dump(obj, transform)


def parse_selector(string):
    if string is None or string == "*": return None
    return Operator.ops.parse(string, transform=None)

def dump_selector(selectors):
    if selectors is None: return "*"
    return Operator.ops.dump(selectors, transform=None)
