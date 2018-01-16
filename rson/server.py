import threading
import types
import socket
import traceback
import sys
import inspect

from collections import OrderedDict
from urllib.parse import urljoin, urlencode
from wsgiref.simple_server import make_server, WSGIRequestHandler

from werkzeug.utils import redirect as Redirect
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed

from . import format, objects

def funcargs(m):
    return m.__code__.co_varnames[:m.__code__.co_argcount]

def make_resource(obj, url, all_methods=False):
    cls = obj.__class__
    attributes = OrderedDict()
    methods = OrderedDict()
    links = []

    for k,v in obj.__dict__.items():
        if k.startswith('__'): continue
        
        attributes[k]= v

    if isinstance(obj, Service):
        start = 0
    else:
        start = 1

    for k,v in obj.__class__.__dict__.items():
        if not getattr(v, 'rpc', all_methods): continue
        if k.startswith('__'): continue
        if v == model_key: continue

        if getattr(v, 'safe', False):
            links.append(k)
        else:
            methods[k] = funcargs(v)[start:]

    return objects.Resource(
        kind = cls.__name__,
        url = url,
        attributes = attributes,
        links = links,
        methods = methods,
    )


def rpc(safe=False):
    def _fn(fn):
        fn.rpc = True
        fn.safe = safe
        return fn
    return _fn

class RequestHandler:
    pass
    
class FunctionHandler(RequestHandler):
    def __init__(self, url, function):
        self.fn = function
        self.url = url

    def GET(self, path, params):
        return self.fn

    def POST(self, path, params, data):
        return self.fn(**data)

    def link(self):
        return objects.Form(self.url, arguments=funcargs(self.fn))

    def embed(self, o=None):
        return objects.Form(self.url, arguments=funcargs(self.fn))

class Service:
    def __init__(self):
        pass

    class Handler(RequestHandler):
        def __init__(self, url, service):
            self.service = service
            self.url = url

        def GET(self, path, params):
            return self.service()

        def POST(self, path, paramsm, data):
            path = path[len(self.url)+1:]
            if path[:2] == '__': 
                return
            return self.service.__dict__[path](**data)

        def link(self):
            return objects.Link(self.url)

        def embed(self,o=None):
            if o is None or o is self.service:
                return self.link()
            return make_resource(o, self.url, all_methods=True)

class View:
    class Handler(RequestHandler):
        def __init__(self, url, view):
            self.view = view
            self.url = url

        def GET(self, path, params):
            params = {key: format.parse(value) for key,value in params.items()}
            return self.view(**params)

        def POST(self, path, params, data):
            if params:
                obj = self.GET(path, params)

                path = path[len(self.url)+1:]
                if path[:2] == '__': 
                    return
                return getattr(obj, path)(**data)
            return self.view(**data)

        def link(self):
            args = funcargs(self.view.__init__)[1:]
            return objects.Form(self.url, arguments=args)

        def embed(self,o=None):
            if o is None or o is self.view:
                return self.link()
            params = {key: format.dump(value) for key, value in o.__dict__.items()}
            url = "{}?{}".format(self.url, urlencode(params))

            return make_resource(o, url, all_methods=True)

@property
def model_key(self):
    return self.id
@model_key.setter
def model_key(self,value):
    self.id = value

class Model:
    @staticmethod
    def key():
        return model_key 

    class Handler(RequestHandler):
        def __init__(self, url, model):
            self.model = model
            self.url = url

        def GET(self, path, params):
            path = path[len(self.url)+1:]
            if path:
                return self.lookup(path)
            else:
                return self.link()

        def POST(self, path, params, data):
            path = path[len(self.url)+1:]
            if path:
                path, method = path.split('/',1)
                return self.invoke(obj, method, data)
            else:
                return self.create(**data)

        def link(self):
            return objects.Selector(
                    kind=self.model.__name__,
                    url=self.url, 
                    arguments=funcargs(self.create)[1:])

        def embed(self,o=None):
            if o is None or o is self.model:
                return self.link()

            url = self.url_for(o)
            return make_resource(o, url, all_methods=False)

        def url_for(self, o):
            return "{}/{}".format(self.url,o.id)

        def lookup(self, key):
            obj = self.model()
            obj.id = path

        def list(self, selector, next=None):
            pass

        def watch(self, selector):
            pass

class Router:
    def __init__(self, prefix="/"):
        self.handlers = OrderedDict()
        self.paths = OrderedDict()
        self.service = None
        if prefix[-1] != '/': prefix += "/"
        self.prefix=prefix

    def add(self, name=None):
        def _add(obj):
            if isinstance(obj, types.FunctionType):
                obj.Handler = FunctionHandler
            self.add_handler(name, obj.Handler, obj)
            return obj

        return _add

    def add_handler(self, name, handler, obj):
        n = obj.__name__ if name is None else name
        self.handlers[n] = handler(self.prefix+n, obj)
        self.paths[obj]=n
        self.service = None

    def index(self):
        if self.service is None:
            attrs = OrderedDict()
            for name,o in self.handlers.items():
                attrs[name] = o.link()
            self.service = objects.Resource('Index',self.prefix,attrs)
        return self.service

    def handle(self, request):
        path = request.path[:]
        if path == self.prefix or path == self.prefix[:-1]:
            out = self.index()
        elif path:
            p = len(self.prefix)
            name = path[p:].split('/',1)[0].split('.',1)[0]
            if name in self.handlers:
                data  = request.data.decode('utf-8')
                if data:
                    args = format.parse(data)
                else:
                    args = None

                params = request.args

                if request.method == 'GET':
                    out = self.handlers[name].GET(path, params)
                else:
                    out = self.handlers[name].POST(path, params, args)
            else:
                raise NotFound(path)
        
        def transform(o):
            if isinstance(o, type) or isinstance(o, types.FunctionType):
                if o in self.paths:
                    return self.handlers[self.paths[o]].embed(o)
            elif o.__class__ in self.paths:
                return self.handlers[self.paths[o.__class__]].embed(o)

            return o

        if out is None:
            return Response('', status='204 None')

        result = format.dump(out, transform)
        return Response(result, content_type=format.CONTENT_TYPE) 
    def app(self):
        return WSGIApp(self.handle)

class WSGIApp:
    def __init__(self, handler):
        self.handler = handler

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self.handler(request)
        except (StopIteration, GeneratorExit, SystemExit, KeyboardInterrupt):
            raise
        except HTTPException as r:
            response = r
            self.log_error(r, traceback.format_exc())
        except Exception as e:
            trace = traceback.format_exc()
            self.log_error(e, trace)
            response = self.error_response(e, trace)
        return response(environ, start_response)

    def log_error(self, exception, trace):
        print(trace, file=sys.stderr)

    def error_response(self, exception, trace):
        return Response(trace, status='500 not ok (%s)'%exception)

class QuietWSGIRequestHandler(WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        pass

class Server(threading.Thread):
    def __init__(self, app, host="", port=0, request_handler=QuietWSGIRequestHandler):
        threading.Thread.__init__(self)
        self.daemon=True
        self.running = True
        self.server = make_server(host, port, app,
            handler_class=request_handler)

    @property
    def url(self):
        return u'http://%s:%d/'%(self.server.server_name, self.server.server_port)

    def run(self):
        self.running = True
        while self.running:
            self.server.handle_request()

    def stop(self):
        self.running =False
        if self.server and self.is_alive():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(self.server.socket.getsockname()[:2])
                s.send(b'\r\n')
                s.close()
            except IOError:
                import traceback
                traceback.print_exc()
        self.join(5)
