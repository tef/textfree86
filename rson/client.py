from functools import singledispatch
from collections import OrderedDict

import requests

from . import format, objects

HEADERS={'Content-Type': format.CONTENT_TYPE}

@singledispatch
def resolve(obj, base_url):
    return obj

@resolve.register(objects.Hyperlink)
def resolve_link(obj, base_url):
    return obj.resolve(base_url)


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
        resolve(obj, result.url)
        return obj
    obj = format.parse(result.text, transform)

    return obj

