from rson import client, server

def test():
    r = server.Router()
    @r.add()
    def echo(x):
        return x

    @r.add()
    def test(x,y):
        return x+y

    @r.add()
    def butt(x):
        return x+1, butt

    server_thread = server.Server(r.app(), port=8888)
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        s= client.get(server_thread.url)

        r = client.post(s.echo(x=1))
        print(r)

        r = client.post(s.test(x=1, y=1))
        print(r)
        
        x, butt = client.post(s.butt(x=1))
        print(x)

        r = client.post(butt(x=x))
    finally:
        server_thread.stop()



if __name__ == '__main__':
    test()
