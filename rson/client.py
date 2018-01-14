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
    def fn():
        url = urljoin(base_url, obj.url)
        return objects.Request('GET', url,  {},{}, None)
    return fn

@resolve.register(objects.Form)
def resolve_form(obj, base_url):
    def fn(*args,**kwargs):
        url = urljoin(base_url, obj.url)
        data = OrderedDict()
        for name, value in zip(obj.arguments, args):
            data[name] = value
            if name in kwargs:
                raise Exception('invalid')
        data.update(kwargs)
        return objects.Request('POST', url,  {},{}, data)

    return fn

@resolve.register(objects.Resource)
def resolve_resource(obj, base_url):
    return RemoteResource(obj, base_url)

class RemoteResource:
    def __init__(self, obj, base_url):
        self.url = urljoin(base_url, obj.url)
        self.obj = obj

    def __getattr__(self, name):
        return self.obj.attrs[name]
        
@resolve.register(objects.Service)
def resolve_service(obj, base_url):
    return RemoteService(obj, base_url)

class RemoteService:
    def __init__(self, obj, base_url):
        self.url = urljoin(base_url, obj.url)
        self.obj = obj

    def __getattr__(self, name):
        def call(*args, **kwargs):
            arguments = self.obj.methods[name]
            data = OrderedDict()
            for key, value in zip(arguments, args):
                data[key] = value
                if key in kwargs:
                    raise Exception('invalid')
            data.update(kwargs)
            return objects.Request('POST', '{}/{}'.format(self.url, name),
                    {}, {}, data)
        return call

@resolve.register(objects.Record)
def resolve_model(obj, base_url):
    return RemoteRecord(obj, base_url)

class RemoteRecord:
    def __init__(self, obj, base_url):
        self.url = urljoin(base_url, obj.url)
        self.obj = obj

    def __getattr__(self, name):
        if name in self.obj.attributes:
            return self.obj.attributes[name]
        def call(*args, **kwargs):
            arguments = self.obj.methods[name]
            data = OrderedDict()
            for key, value in zip(arguments, args):
                data[key] = value
                if key in kwargs:
                    raise Exception('invalid')
            data.update(kwargs)
            return objects.Request('POST', '{}/{}'.format(self.url, name),
                    {}, {}, data)
        return call

@resolve.register(objects.Model)
def resolve_model(obj, base_url):
    def fn(*args,**kwargs):
        url = urljoin(base_url, obj.url)
        if args:
            data = args[0]
        else:
            data =kwargs
        return objects.Request('POST', url,  {},{}, data)

    return fn

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

