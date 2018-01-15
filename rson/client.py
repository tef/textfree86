from functools import singledispatch
from urllib.parse import urljoin
from collections import OrderedDict

import requests

from . import format, objects

HEADERS={'Content-Type': format.CONTENT_TYPE}

@singledispatch
def resolve(obj, base_url):
    return obj

@resolve.register(objects.Link)
def resolve_link(obj, base_url):
    url = urljoin(base_url, obj.url)
    return RemoteFunction('GET', url, [])

@resolve.register(objects.Form)
def resolve_form(obj, base_url):
    url = urljoin(base_url, obj.url)
    return RemoteFunction('POST', url, obj.arguments)

@resolve.register(objects.Resource)
def resolve_resource(obj, base_url):
    url = urljoin(base_url, obj.url)
    return RemoteObject(url, obj.attributes, obj.methods)


class RemoteFunction:
    def __init__(self, method, url, arguments):
        self.method = method
        self.url = url
        self.arguments = arguments

    def __call__(self, *args, **kwargs):
        if self.method == 'GET':
            return objects.Request('GET', self.url, {}, {}, None)

        data = OrderedDict()
        for key, value in zip(self.arguments, args):
            data[key] = value
            if key in kwargs:
                raise Exception('invalid')
        data.update(kwargs)
        return objects.Request('POST', self.url, {}, {}, data)

class RemoteObject:
    def __init__(self, url, attributes, methods):
        self.url = url
        self.attributes = attributes
        self.methods = methods

    def __getattr__(self, name):
        if name in self.attributes:
            return self.attributes[name]
        arguments = self.methods[name]
        url = '{}/{}'.format(self.url, name)
        return RemoteFunction('POST', url, arguments)


def get(url):
    if isinstance(url, objects.Request):
        if url.method != 'GET':
            raise Exception('mismatch')
        return fetch(url.method, url.url, url.params, url.headers, url.data)
    else:
        return fetch('GET', url, {}, {}, None)

def post(url, data=None):
    if isinstance(url, objects.Request):
        return fetch(url.method, url.url, url.params, url.headers, url.data)
    else:
        return fetch('GET', url, {}, {}, None)

def fetch(method, url, params, headers, data):
    h = OrderedDict(HEADERS)
    h.update(headers)

    if data is not None:
        data = format.dump(data)
    result = requests.request(method, url, params=params, headers=h,data=data)

    def transform(obj):
        obj = resolve(obj, result.url)
        return obj
    obj = format.parse(result.text, transform)

    return obj

