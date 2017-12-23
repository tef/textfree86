from rson import client, server

def test():
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

    @r.add()
    class Counter(server.Model):
        @property
        def key(self):
            return str(self.num)

        @key.setter
        def key(self, key):
            self.num = int(key)

        def next(self):
            self.num+=1
            return self

        def value(self):
            return self.num

    server_thread = server.Server(r.app(), port=8888)
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        s= client.get(server_thread.url+"/test/")

        r = client.post(s.echo(1))
        print(r)

        test = client.post(s.test())
        print(test)
        
        x = client.post(test(x=1))
        print(x)

        print(s.MyEndpoint())
        e = client.get(s.MyEndpoint())

        print(client.post(e.rpc_one(1,2)))

        print(client.post(e.rpc_two(3,b=4)))

        counter = client.post(s.Counter(10))
        counter = client.post(counter.next())
        counter = client.post(counter.next())
        counter = client.post(counter.next())
        value = client.post(counter.value())


        print(value)
    finally:
        server_thread.stop()



if __name__ == '__main__':
    test()
