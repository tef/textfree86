from rson import client, server

def make_server():
    r = server.Router(prefix="/test/")
    @r.add()
    def echo(x):
        return x

    @r.add()
    def test():
        return echo

    @r.add()
    class MyEndpoint(server.Service):
        def rpc_one(a,b):
            return a+b

        def rpc_two(a,b):
            return a*b

        def rpc_three():
            return None

    @r.add()
    class Counter(server.Token):
        def __init__(self, num=0):
            self.num = num

        def next(self):
            return Counter(self.num+1)

        def value(self):
            return self.num

    @r.add()
    class Job():
        class Handler(server.Model.Handler):
            jobs = {}
            def lookup(self, name):
                return self.jobs[name]

            def create(self, name):
                j = self.jobs[name] = Job(name)
                return j

            def delete(self, name):
                self.jobs.pop(name)

        name = server.Model.key()

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
            pass

    return server.Server(r.app(), port=8888)

def test():
    server_thread = make_server()
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        s= client.get(server_thread.url+"/test/")
        print(s)
        print(s.echo)

        r = client.call(s.echo(1))
        print(r)

        test = client.call(s.test())
        print(test)
        
        x = client.call(test(x=1))
        print(x)

        print(s.MyEndpoint())
        e = client.get(s.MyEndpoint())

        print(client.call(e.rpc_one(1,2)))

        print(client.call(e.rpc_two(3,b=4)))
        
        print(client.call(e.rpc_three()))

        counter = client.call(s.Counter(10))
        counter = client.call(counter.next())
        counter = client.call(counter.next())
        counter = client.call(counter.next())
        print(counter)
        print('nice')
        value = client.post(counter.value())


        print(value, counter.num)

        job = client.call(s.Job(name="butt"))

        print(job, job.url, job.methods)
    finally:
        server_thread.stop()



if __name__ == '__main__':
    test()
