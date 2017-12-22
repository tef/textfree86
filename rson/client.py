from functools import singledispatch
import requests

from . import format, objects

@singledispatch
def resolve(obj, base_url):
    return obj

@resolve.register(tuple)
@resolve.register(list)
def resolve_list(obj, base_url):
    return obj.__class__(resolve(x) for x in obj)


@resolve.register(objects.Link)
@resolve.register(objects.Form)
@resolve.register(objects.Service)
def resolve_link(obj, base_url):
    return obj.resolve(base_url, resolve)


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

    if data is not None:
        data = format.dump(data)
    result = requests.request(method, url, params=params, headers=headers,data=data)

    obj = format.parse(result.text)

    return resolve(obj, result.url)
