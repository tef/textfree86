from rson import client, server

from werkzeug.wrappers import Request, Response


def test():
    r = server.Router()
    @r.add()
    def echo(x):
        return x

    s = server.Server(r.app(), port=8888)
    s.start()
    print(s.url)

    try:
        c = client.get(s.url)
        r = client.post(c.echo(x=1))
        print(r)
    finally:
        s.stop()



if __name__ == '__main__':
    test()
