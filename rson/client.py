from functools import singledispatch
from urllib.parse import urljoin
from collections import OrderedDict

import requests

from . import format, objects

HEADERS={'Content-Type': format.CONTENT_TYPE}

class Client:
    def __init__(self):
        self.session=requests.session()

    def get(self, request):
        if not isinstance(request, objects.Request):
            request = objects.Request('GET', request, {}, {}, None)

        if request.method != 'GET':
            raise Exception('mismatch')
        return self.fetch(request)


    def post(self, request, data=None):
        if not isinstance(request, objects.Request):
            request = objects.Request('POST', request, {}, {}, data)

        if request.method != 'POST':
            raise Exception('mismatch')
        
        return self.fetch(request)

    def fetch(self, request):
        headers = OrderedDict(HEADERS)
        if request.headers:
            headers.update(request.headers)
        
        method = request.method
        url = request.url
        params = request.params
        
        if request.data is not None:
            data = format.dump(request.data)
        else:
            data = None

        result = self.session.request(
                method, 
                url, 
                params=params, 
                headers=headers, 
                data=data
        )

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
            if isinstance(obj, objects.Selector):
                return RemoteSelector(obj.kind, url, obj.arguments)
            if isinstance(obj, objects.Resource):
                return RemoteObject(obj.kind, url, obj)

            return obj

        obj = format.parse(result.text, transform)

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
    def __init__(self, kind,  url, arguments):
        self.kind = kind
        self.url = url
        self.arguments = arguments

    def __str__(self):
        return "<Link to {}>".format(self.url)

    def __call__(self, *args, **kwargs):
        data = OrderedDict()
        for key, value in zip(self.arguments, args):
            data[key] = value
            if key in kwargs:
                raise Exception('invalid')
        data.update(kwargs)
        return objects.Request('POST', self.url, {}, {}, data)

class RemoteObject:
    def __init__(self,kind, url, obj):
        self.kind = kind
        self.url = url
        self.obj = obj
        self.links = obj.links
        self.attributes = obj.attributes
        self.methods = obj.methods

    def __str__(self):
        return "<{} at {}>".format(self.kind, self.url)

    def __getattr__(self, name):
        if name in self.attributes:
            return self.attributes[name]
        if name in self.links:
            return RemoteFunction('GET', self.links[name], ())
        
        arguments = self.methods[name]
        if '?' in self.url:
            url, params = self.url.split('?',1)
            url = '{}/{}?{}'.format(url, name, params)
        else:
            url = '{}/{}'.format(self.url, name)
        return RemoteFunction('POST', url, arguments)

client = Client()

def get(arg):
    return client.get(arg)

def post(arg, data=None):
    return client.post(arg, data)

