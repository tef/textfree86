from rson import client, server

def test():
    r = server.Router()
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
        num = server.Field()

        def next(self):
            return Counter(num)

        def value(self):
            return num

    server_thread = server.Server(r.app(), port=8888)
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        s= client.get(server_thread.url)

        r = client.post(s.echo(x=1))
        print(r)

        test = client.post(s.test())
        print(test)
        
        x = client.post(test(x=1))
        print(x)

        e = client.get(s.MyEndpoint())

        print(client.post(e.rpc_one(a=1,b=2)))

        print(client.post(e.rpc_two(a=3,b=4)))
    finally:
        server_thread.stop()



if __name__ == '__main__':
    test()
