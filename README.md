# catbus, a client-server framework


## serving a function
```
from catbus import server
from datetime import datetime, timezone

ns = server.Namespace() # Where our objects and methods live

@ns.add()
def now():
    return datetime.now(timezone.utc)


thread = server.Server(ns.app(), port=8888)

try:
    thread.start()
    print("Running on ",thread.url)
    while True:
        pass
finally:
    thread.stop()
```

## calling a function

```
from catbus import client

service = client.get('http://127.0.0.1:8888/')

now = client.call(service.now())

print('Time on remote service is {}'.format(now))
```

## serving a singleton 
```
@ns.add()
class Store(server.Singleton):
    def __init__(self):
        self.sum = 0

    def add(self, n):
        self.sum += n
        
    def total(self):
        return self.sum
```

## calling a singleton

```

store = client.get(service.Store())

for x in (1,2,3):
    client.call(store.add(x))

total = client.call(store.total())

print(total)
```



