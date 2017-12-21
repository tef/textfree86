from rson import client, server

from werkzeug.wrappers import Request, Response


def test():
    def app(request):
        return Response('hello')

    s = server.Server(server.WSGIApp(app), port=8888)
    s.start()
    print(s.url)

    try:
        print(client.fetch('get',s.url, {}, {},None))
    finally:
        s.stop()



if __name__ == '__main__':
    test()
