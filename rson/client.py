from functools import singledispatch
from urllib.parse import urljoin
from collections import OrderedDict

import requests

from . import format, objects

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

    def call(self, request, data=None):
        request = unwrap_request('POST', request, data)

        return self.fetch(request)

    def delete(self, request, arg=None):
        if isinstance(request, RemoteSelector):
            request = request.delete(arg)
            print(request.url, request.data)
        elif isinstance(request, objects.Request):
            pass
        else:
            url = getattr(request, 'url', request)

            raise Exception('no')

        return self.fetch(request)

    def create(self, request, data):
        if isinstance(request, RemoteSelector):
            request = request.create(**data)
            print(request.url, request.data)
        elif instance(obj, objects.Request):
            pass
        else:
            url = getattr(request, 'url', request)

            raise Exception('no')

        return self.fetch(request)

    def update(self, request, data):
        raise Exception('no')
    
    
    def list(self, request, limit=None):

        if isinstance(request, RemoteSelector):
            request = request.list(limit)
        elif instance(obj, objects.Request):
            pass
        else:
            url = getattr(request, 'url', request)

            raise Exception('no')

        # while ... keep returning them
        return self.fetch(request)

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

            url = urljoin(result.url, obj.url)

            if isinstance(obj, objects.Link):
                if obj.value:
                    return lambda: obj.value
                return RemoteFunction('GET', url, [])
            if isinstance(obj, objects.Form):
                return RemoteFunction('POST', url, obj.arguments)
            if isinstance(obj, objects.Collection):
                return RemoteSelector(obj.kind, url, obj.arguments)
            if isinstance(obj, objects.Resource):
                return RemoteObject(obj.kind, url, obj)
            if isinstance(obj, objects.List):
                return RemoteList(obj.kind, url, obj)

            return obj

        obj = objects.parse(result.text, transform)

        return obj

class RemoteFunction:
    def __init__(self, method, url, arguments):
        self.method = method
        self.url = url
        self.arguments = arguments

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
        return objects.Request('POST', self.url, {}, {}, data)

class RemoteSelector:
    def __init__(self, kind,  url, arguments, selectors=()):
        self.kind = kind
        self.url = url
        self.arguments = arguments
        self.selectors = selectors

    def __str__(self):
        return "<Link to {}>".format(self.url)

    def lookup(self, name):
        url = "{}/id/{}".format(self.url, name)
        return objects.Request('GET', url, {}, {}, None)
    
    def create(self, *args, **kwargs):
        url = "{}/new".format(self.url)
        data = OrderedDict()
        for key, value in zip(self.arguments, args):
            data[key] = value
            if key in kwargs:
                raise Exception('invalid')
        data.update(kwargs)
        return objects.Request('POST', url, {}, {}, data)

    def delete(self, name):
        url = "{}/delete/{}".format(self.url, name)
        return objects.Request('POST', url, {}, {}, None)

    def get_params(self,limit):
        params = OrderedDict()
        params['selector'] = '*'
        if limit:
            params['limit'] = limit
        return params

    def delete_list(self, selector, limit):
        url = "{}/delete".format(self.url)
        params = self.get_params(limit)
        return objects.Request('POST', url, params, {}, None)

    def list(self, limit=None):
        url = "{}/list".format(self.url)
        params = self.get_params(limit)
        return objects.Request('GET', url, params, {}, None)

    def next(self, limit=None):
        # so that remote collection / selectors have
        # similar apis
        return self.list(limit)

    def where(self, **kwargs):
        new_selectors = list(self.selectors)
        
        for name, value in kwargs:
            new_selectors.append(OrderedDict(
                key=name,
                operator="Equals",
                values=value,
            ))

        return RemoteSelector(self.kind, self.url, self.arguments, new_selectors)

    def not_where(self, **kwargs):
        new_selectors = list(self.selectors)

        for name, value in kwargs:
            new_selectors.append(OrderedDict(
                key=name,
                operator="NotEquals",
                values=value
        ))
        
        return RemoteSelector(self.kind, self.url, self.arguments, new_selectors)


class RemoteList:
    def __init__(self,kind, url, obj):
        self.kind = kind
        self.url = url
        self.obj = obj

    def next(self):
        params = OrderedDict()

        return object.Request('GET', self.url, params, {}, None)

    def values(self):
        return self.obj['items']

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

def call(arg, data=None):
    return client.call(arg, data)

def delete(req, arg=None):
    return client.delete(req, arg)
def list(arg):
    return client.list(arg)
def create(arg, data):
    return client.create(arg, data)
