from catbus import client, server

import collections
from datetime import datetime, timezone

def make_server():
    n = server.Namespace(name="test")
    @n.add()
    def echo(x):
        return x

    @n.add()
    @server.rpc(safe=True)
    def test():
        return echo

    @n.add()
    class MyEndpoint(server.Service):
        # no self, all methods exposed.

        def rpc_one(a,b):
            return a+b

        def rpc_two(a,b):
            return a*b

        def rpc_three():
            return None

        def now():
            return datetime.now(timezone.utc)


    # A singleton object

    @n.add()
    class Total(server.Singleton):
        def __init__(self):
            self.sum = 0

        def add(self, n):
            self.sum += n
            return self
        
        @server.rpc(safe=True)
        def total(self):
            return self.sum

   # A collection of instances

    jobs = collections.OrderedDict()

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


    @n.add()
    class Counter(server.Token):
        # Tokens exist as /name?state urls, not stored on server
        # re-creates a Counter with every request & calls methods
        # before disposing it

        def __init__(self, num=0):
            self.num = num

        def next(self):
            return Counter(self.num+1)

        def value(self):
            return self.num

    return server.Server(n.app(), port=8888)

def test():
    server_thread = make_server()
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        s= client.Get(server_thread.url+"/test/")
        print(s)
        print(s.echo)

        r = client.Call(s.echo(1))
        print(r)

        test = client.Call(s.test())
        print(test)
        
        x = client.Call(test(x=1))
        print(x)

        print(s.MyEndpoint())
        e = client.Get(s.MyEndpoint())

        print(client.Call(e.rpc_one(1,2)))

        print(client.Call(e.rpc_two(3,b=4)))
        
        print(client.Call(e.rpc_three()))

        print(client.Call(e.now()))

        counter = client.Call(s.Counter(10))
        counter = client.Call(counter.next())
        counter = client.Call(counter.next())
        counter = client.Call(counter.next())
        print(counter)
        print('nice')
        value = client.Post(counter.value())

        total = client.Call(s.Total())

        print(client.Call(total.total()))

        client.Call(total.add(5))
        client.Call(total.add(5))
        client.Call(total.add(5))

        print(client.Call(total.total()))

        print(value, counter.num)

        job = client.Create(s.Job,dict(name="butt"))
            # client.Call(s.Job.create(...))

        print(job, job.url, job.methods, job.attributes)

        for j in client.List(s.Job):
            print(j)

        print(client.Delete(job))
    finally:
        server_thread.stop()



if __name__ == '__main__':
    test()
