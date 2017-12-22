from collections import OrderedDict

reserved_tags = set("""
        bool int float complex
        string bytestring base64
        duration datetime
        set list dict object
        unknown
""".split())

class Registry:
    def __init__(self):
        self.classes = OrderedDict()
        self.tag_for = OrderedDict()

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

    def from_tag(self, name, value):
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

@registry.add()
class Link:
    def __init__(self, url):
        self.url = url

    def __call__(self):
        return Request('GET', url,  {},{}, None)

@registry.add()
class Service:
    def __init__(self, attrs):
        self.attrs = attrs

    def __getattr__(self, name):
        if name in self.attrs:
            return self.attrs[name]

@registry.add()
class Form:
    def __init__(self, url):
        self.url = url

    def __call__(self, **args):
        return Request('POST', self.url,  {},{}, args)

@registry.add()
class Request:
    def __init__(self,method, url, headers, params, data):
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


def tag_value_for_object(obj):
    return registry.as_tagged(obj)

def tag_rson_value(name, value):
    return registry.from_tag(name, value)



