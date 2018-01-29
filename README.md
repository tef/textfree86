# catbus, a client-server framework

"why have protocols when you have to write a new client for each service"

catbus is a client-server framework for RPC, CRUD, and Socket-like APIs, with a reusable client.

There is no codegen or schema used in the following examples:

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

## serving a class, and instances

```
jobs = {}
@n.add()
class Job():
    Handler = server.Collection.dict_handler('name', jobs)

    def __init__(self, name):
        self.name = name
        self.state = 'run'

    @server.rpc()
    def stop(self):
        self.state = 'stop'

    @server.rpc()
    def start(self):
        self.state = 'run'

    def hidden(self):
        return 'Not exposed over RPC'

```

## accessing a collection

```
job = client.create(s.Job.create(name="helium"))

for j in client.list(s.Job):
    client.call(j.stop())

job = client.get(s.Job, key="helium")
client.delete(job)
```

## long polling

```
waiter = client.Call(s.expensive(123))

value = client.Wait(waiter, poll_seconds=0.5)
```


```
@n.add()
@server.waiter()
def expensive(value):
    return server.Waiter(value=value,count=3)

@expensive.ready()
def expensive(value, count):
    if count > 0:
        return server.Waiter(value=value, count=count-1)
    else:
        return value
```

## exposing a table

```
@namespace.add()
class Person(Model):
    class Meta: database = db

    uuid = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(index=True)
    job = CharField(index=True)

    Handler = server.Model.PeeweeHandler

    @server.rpc()
    def hello(self):
        return "Hello, {}!".format(self.name)

```

```
for p in client.List(s.Person.where(job='foo')):
    print(" Calling p.hello()", client.Call(p.hello()))

```


```
client.Delete(s.Person.where(job='foo'))
```
