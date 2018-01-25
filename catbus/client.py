"""catbus.client

This is a simple client with a handful of crud 
or http-like methods. The real magic is in the
RemoteObject/RemoteFunction wrapper objects.

"""

# warning: defines a function called list
_list = list

from functools import singledispatch
from urllib.parse import urljoin
from collections import OrderedDict

import requests

from . import objects

HEADERS={'Content-Type': objects.CONTENT_TYPE}

def unwrap_request(method, request, data=None):
    if isinstance(request, objects.Request):
        if data is not None:
            raise Exception('too much data')
        return request

    if hasattr(request, 'url'):
        request = request.url

    return objects.Request(method, request, {}, {}, data)

class Client:
    def __init__(self):
        self.session=requests.session()

    def get(self, request):
        request = unwrap_request('GET', request)

        if request.method != 'GET':
            raise Exception('mismatch')
        return self.fetch(request)

    def post(self, request, data=None):
        request = unwrap_request('POST', request, data)

        if request.method != 'POST':
            raise Exception('mismatch')
        
        return self.fetch(request)

    def call(self, request, method=None, data=None):
        if isinstance(request, RemoteFunction):
            if method is None:
                request = request(**data)
            else:
                raise Exception('no')
        elif isinstance(request, RemoteObject):
            if method is None:
                raise Exception('no')
            else:
                request = getattr(request, method)(**data)
        request = unwrap_request('POST', request, data)

        return self.fetch(request)

    def create(self, request, data):
        if isinstance(request, RemoteDataset):
            request = request.create(**data)
        else:
            request = unwrap_request('PUT', request, data)
        if request.method not in ('PUT', 'POST'):
            raise Exception('mismatch')

        return self.fetch(request)

    def update(self, request, data):
        raise Exception('no')
    
    def lookup(self, request, data):
        if isinstance(request, RemoteDataset):
            request = request.lookup(data)
        else:
            request = unwrap_request('GET', request)
            if request.method != 'GET' or data != None:
                raise Exception('mismatch')

        return self.fetch(request)

    def delete(self, request, arg=None):
        if isinstance(request, RemoteDataset):
            request = request.delete(arg)
        else:
            request = unwrap_request('DELETE', request)
        if request.method not in ('DELETE', 'POST'):
            raise Exception('mismatch')

        return self.fetch(request)

    
    def delete_list(self, request, where=None):
        if isinstance(request, RemoteDataset):
            request = request.delete_list(where=where)
        elif instance(obj, objects.Request):
            pass
        else:
            raise Exception('no')

        return self.fetch(request)

    
    def list(self, request, where=None, batch=None):
        if isinstance(request, RemoteDataset):
            request = request.list(where=where, batch=batch)
        elif instance(obj, objects.Request):
            pass
        else:
            raise Exception('no')

        # while ... keep returning them
        obj = self.fetch(request)
        if isinstance(obj, RemoteList):
            while obj:
                for x in obj.values():
                    yield x
                request = obj.next(batch)
                if request:
                    obj = self.fetch(request)
                else:
                    obj = None
        else:
            for x in obj:
                yield x

    def watch(self, request):
        pass

    def fetch(self, request):
        headers = OrderedDict(HEADERS)
        if request.headers:
            headers.update(request.headers)
        
        method = request.method
        url = request.url
        params = request.params
        
        if request.data is not None:
            data = objects.dump(request.data)
        else:
            data = None

        result = self.session.request(
                method, 
                url, 
                params=params, 
                headers=headers, 
                data=data
        )

        if result.status_code == 204:
            return None

        def transform(obj):
            if not isinstance(obj, objects.Hyperlink):
                return obj

            if isinstance(obj, objects.List):
                return RemoteList(obj.kind, result.url, obj)

            url = urljoin(result.url, obj.url)

            if isinstance(obj, objects.Link):
                if obj.value:
                    return lambda: obj.value
                return RemoteFunction('GET', url, [])
            if isinstance(obj, objects.Form):
                return RemoteFunction('POST', url, obj.arguments)
            if isinstance(obj, objects.Dataset):
                return RemoteDataset(obj.kind, url, obj)
            if isinstance(obj, objects.Resource):
                return RemoteObject(obj.kind, url, obj)

            return obj

        obj = objects.parse(result.text, transform)

        return obj

class RemoteFunction:
    def __init__(self, method, url, arguments, defaults=()):
        self.method = method
        self.url = url
        self.arguments = arguments
        self.defaults = defaults

    def __str__(self):
        return "<Link to {}>".format(self.url)

    def __call__(self, *args, **kwargs):
        if self.method == 'GET':
            return objects.Request('GET', self.url, {}, {}, None)

        data = OrderedDict()
        for key, value in zip(self.arguments, args):
            data[key] = value
            if key in kwargs:
                raise Exception('invalid')
        data.update(kwargs)
        for key in self.arguments:
            if key not in data:
                if key in self.defaults:
                    data[key] = self.defaults
        return objects.Request('POST', self.url, {}, {}, data)

class RemoteDataset:
    def __init__(self, kind, url, obj, selectors=()):
        self.kind = kind
        self.url = url
        self.obj = obj
        self.selectors = selectors

    def __str__(self):
        return "<Link to {}>".format(self.url)

    def __getitem__(self, name):
        return self.lookup(name)

    def __call__(self, *args, **kwargs):
        return self.create(*args, **kwargs)

    def lookup(self, name):
        url = "{}/id/{}".format(self.url, name)
        return objects.Request('GET', url, {}, {}, None)
    
    def create(self, *args, **kwargs):
        url = "{}/new".format(self.url)
        arguments = self.obj.metadata['new']
        data = OrderedDict()
        for key, value in zip(arguments, args):
            data[key] = value
            if key in kwargs:
                raise Exception('invalid')
        data.update(kwargs)
        return objects.Request('POST', url, {}, {}, data)

    def delete(self, name):
        url = "{}/id/{}".format(self.url, name)
        return objects.Request('DELETE', url, {}, {}, None)

    def get_params(self, selector, batch):
        params = OrderedDict()
        if selector and self.selectors:
            raise Exception('no')
        if selector:
            params['where'] = selector
        if self.selectors: 
            params['where'] = objects.dump_selector(self.selectors)
        if batch:
            params['limit'] = batch
        return params

    def delete_list(self, where=None):
        url = "{}/list".format(self.url)
        params = self.get_params(where, None)
        if 'where' not in params:
            raise Exception('missing where')
        return objects.Request('DELETE', url, params, {}, None)

    def list(self, where=None, batch=None):
        url = "{}/list".format(self.url)
        params = self.get_params(where, batch)
        return objects.Request('GET', url, params, {}, None)

    def next(self, batch=None):
        # so that remote collection / selectors have
        # similar apis
        return self.list(batch)

    def where(self, **kwargs):
        new_selectors = []
        new_selectors.extend(self.selectors)
        names = self.obj.metadata['list']
        
        for name, value in kwargs.items():
            if name not in names:
                raise Exception('no')
            new_selectors.append(OrderedDict(
                key=name,
                operator="Equals",
                values=value,
            ))

        return RemoteDataset(self.kind, self.url, self.obj, new_selectors)

    def not_where(self, **kwargs):
        new_selectors = []
        new_selectors.extend(self.selectors)
        names = self.obj.metadata['list']

        for name, value in kwargs.items():
            if name not in names:
                raise Exception('no')
            new_selectors.append(OrderedDict(
                key=name,
                operator="NotEquals",
                values=value
        ))
        
        return RemoteDataset(self.kind, self.url, self.obj, new_selectors)


class RemoteList:
    def __init__(self,kind, base_url, obj):
        self.base_url = base_url
        self.kind = kind
        self.obj = obj

    def next(self, batch):
        if self.obj.metadata['continue']:
            params = OrderedDict()
            url = urljoin(self.base_url, self.obj.metadata['collection'])
            url = "{}/list".format(url)
            params['selector'] = self.obj.metadata['selector']
            params['continue'] = self.obj.metadata['continue']
            if batch:
                params['limit'] = batch

            return objects.Request('GET', url, params, {}, None)

    def values(self):
        return self.obj.items

    # __getitem__
    # length
    # iter
    # contains
    # next()

class RemoteObject:
    def __init__(self,kind, url, obj):
        self.kind = kind
        self.url = url
        self.obj = obj
        self.links = obj.metadata.get('links')
        self.attributes = obj.attributes
        self.methods = obj.metadata.get('methods')

    def __str__(self):
        return "<{} at {}>".format(self.kind, self.url)

    def __getattr__(self, name):
        if name in self.attributes:
            return self.attributes[name]
        
        if '?' in self.url:
            url, params = self.url.split('?',1)
            url = '{}/{}?{}'.format(url, name, params)
        else:
            url = '{}/{}'.format(self.url, name)

        if self.links and name in self.links:
            return RemoteFunction('GET', url, ())
        elif self.methods:
            arguments = self.methods[name]
            return RemoteFunction('POST', url, arguments)
        raise AttributeError('no')

client = Client()

def get(arg):
    return client.get(arg)

def post(arg, data=None):
    return client.post(arg, data)

def call(arg, method=None, data=None):
    return client.call(arg, method, data)

def delete(req, arg=None):
    return client.delete(req, arg)
def list(arg, where=None, batch=None):
    return client.list(arg, where=None, batch=batch)
def delete_list(req, where=None):
    return client.delete_list(req, where=where)
def create(arg, data):
    return client.create(arg, data)
