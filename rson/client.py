import requests

from . import format

def get(url):
    return fetch('GET', url, {}, {}, None)


def fetch(method, url, params, headers, data):

    if data is not None:
        data = format.dump(data)
    result = requests.request(method, url, params=params, headers=headers,data=data)

    return format.parse(result.text)
