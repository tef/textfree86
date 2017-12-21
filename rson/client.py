import requests

def fetch(method, url, params, headers, data):
    result = requests.request(method, url, params=params, headers=headers,data=data)

    return result.content
