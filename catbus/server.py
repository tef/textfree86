"""catbus.server
a http server that routes requests to the
mapped objects, handling transforming them
into rson wire objects
"""
import threading
import types
import socket
import traceback
import sys
import inspect
import uuid

from collections import OrderedDict
from urllib.parse import urljoin, urlencode
from wsgiref.simple_server import make_server, WSGIRequestHandler

from werkzeug.utils import redirect as Redirect
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException

from . import objects

def funcargs(m):
    args =  m.__code__.co_varnames[:m.__code__.co_argcount]
    args = [a for a in args if not a.startswith('_')]
    if args and args[0] == 'self': args.pop(0)
    return args

def make_resource(obj, url):
    cls = obj.__class__

    links, methods = extract_methods(cls)
    attributes = extract_attributes(obj)

    metadata = OrderedDict(
        url = url,
        links = links,
        methods = methods,
    )

    return objects.Resource(
        kind = cls.__name__,
        metadata = metadata,
        attributes = attributes,
    )

def extract_methods(cls):
    links = []
    all_methods = getattr(cls, 'rpc', False)
    methods = OrderedDict()
    for k,v in cls.__dict__.items():
        if not getattr(v, 'rpc', all_methods): continue
        if k.startswith('_'): continue

        if getattr(v, 'safe', False):
            links.append(k)
        else:
            methods[k] = funcargs(v)
    return links, methods

def extract_attributes(obj):
    attributes = OrderedDict()
    for k,v in obj.__dict__.items():
        if k.startswith('_'): continue
        
        attributes[k]= v
    return attributes



def rpc(safe=False):
    def _fn(fn):
        fn.rpc = True
        fn.safe = safe
        return fn
    return _fn

def waiter():
    def _fn(fn):
        fn.rpc = True
        fn.waiter = None
        def _wait():
            def _decorator(wait_fn):
                fn.waiter = wait_fn
                return fn
            return _decorator
        fn.ready = _wait
        return fn
    return _fn

class RequestHandler:
    def invoke(self, obj, args=None, params=None, safe=False):
        if not safe:
            if args:
                return obj(**args)
            else:
                return obj()
        else:
            if not obj.safe:
                raise objects.MethodNotAllowed()
            return obj()

    def invoke_waiter(self, waiter, obj, params):
        params = {key: objects.parse(value) for key,value in params.items()}
        # if waiter is a fn
        if obj is None:
            out = waiter(**params)
        else:
            out = waiter(obj, **params)

        # if waiter is a waiter, call.resolve()

        if isinstance(out, Waiter):
            out.from_resolve = True
        return out

class Embed:
    pass
    
class Waiter(Embed):
    suffix = '/wait'

    def __init__(self, **args):
        self.args = args
        self.from_resolve = False

    def embed(self, prefix, name):
        params = {key: objects.dump(value) for key, value in self.args.items()}
        if not self.from_resolve:
            name = "{}{}".format(name,self.suffix) 
        url = "{}{}?{}".format(prefix, name,urlencode(params))
        metadata = OrderedDict()
        metadata["url"] = url
        return objects.Waiter(
            metadata = metadata,
        )

class FunctionHandler(RequestHandler):
    def __init__(self, name, function):
        self.fn = function
        self.name = name

    def on_request(self, context, request):
        method, path, params, data = request.method, request.url, request.params, request.data
        path = path[len(self.name)+1:]
        if path == 'wait':
            if method == 'GET':
                return self.invoke_waiter(self.fn.waiter, None, params)
            else:
                return MethodNotAllowed()
        elif path:
            raise objects.NotFound()

        if method == 'GET':
            return self.invoke(self.fn, safe=True)
        elif method == 'POST':
            return self.invoke(self.fn, args=data)
        raise objects.MethodNotAllowed()

    def url(self, prefix):
        return prefix+self.name

    def link(self, prefix):
        if getattr(self.fn, 'safe', False):
            return objects.Link(self.url(prefix))
        else:
            return objects.Form(self.url(prefix), arguments=funcargs(self.fn))

    def embed(self, prefix, o=None):
        return self.link(prefix)


class Service:
    rpc = True

    def __init__(self):
        pass

    def __getattribute__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        return getattr(object.__getattribute__(self, '__class__'),name)

    class Handler(RequestHandler):
        def __init__(self, name, service):
            self.service = service
            self.name = name

        def on_request(self, context, request):
            method, path, params, data = request.method, request.url, request.params, request.data
            path = path[len(self.name)+1:].split('/')
            if path and path[0]:
                obj_method = path[0]

                if obj_method.startswith('_'): 
                    raise objects.Forbidden()

                fn = getattr(self.service, obj_method)

                if len(path) > 1 and path[1]:
                    if path[1] == 'wait':
                        if method != 'GET':
                            raise objects.MethodNotAllowed()
                        return self.invoke_waiter(fn.waiter, None, params)
                    else:
                        raise objects.NotFound()
            
                if method == 'GET':
                    return self.invoke(fn, params=params, safe=True)
                elif method == 'POST':
                    return self.invoke(fn, args=data)
                else:
                    raise objects.MethodNotAllowed()

            else:
                if method == 'GET':
                    return self.service()
                else:
                    raise objects.MethodNotAllowed()

        def url(self, prefix):
            return prefix+self.name

        def link(self, prefix):
            return objects.Link(self.url(prefix))

        def embed(self,prefix, o=None):
            if o is None or o is self.service:
                return self.link(prefix)

            links, methods = extract_methods(self.service)

            metadata = OrderedDict(
                url = self.url(prefix),
                links = links,
                methods = methods,
            )

            return objects.Service(
                kind = self.service.__name__,
                metadata = metadata,
                attributes = {},
            )

class Token:
    rpc = True
    class Handler(RequestHandler):
        def __init__(self, name, view):
            self.view = view
            self.name = name

        def on_request(self, context, request):
            method, path, params, data = request.method, request.url, request.params, request.data
            path = path[len(self.name)+1:]
            if path.startswith('_'): 
                raise objects.Forbidden()
            if '/' in path:
                raise objects.NotFound()

            if params:
                obj =  self.lookup(params)

                if not path:
                    if method == 'GET':
                        return obj
                    raise objects.MethodNotAllowed()

                fn = getattr(obj, path)

                if method == 'GET':
                    return self.invoke(fn, safe=True)
                elif method == 'POST':
                    return self.invoke(fn, args=data)
                else:
                    raise objects.MethodNotAllowed()
            else:
                if path:
                    raise objects.NotImplemented()

                if method == 'GET':
                    return self.view
                elif method == 'POST':
                    return self.view(**data)
                raise objects.MethodNotAllowed()

        def lookup(self, params):
            params = {key: objects.parse(value) for key,value in params.items() if not key.startswith('_')}
            obj = self.view(**params)
            return obj

        def url(self, prefix):
            return prefix + self.name

        def link(self, prefix):
            args = funcargs(self.view.__init__)
            return objects.Form(self.url(prefix), arguments=args)

        def embed(self, prefix, o=None):
            if o is None or o is self.view:
                return self.link(prefix)
            params = {key: objects.dump(value) for key, value in o.__dict__.items()}
            url = "{}?{}".format(self.url(prefix), urlencode(params))

            return make_resource(o, url)

class Singleton:
    rpc = True

    def __init__(self):
        pass

    class Handler(RequestHandler):
        def __init__(self, name, cls):
            self.cls = cls
            self.name = name
            self.obj = self.cls()

        def on_request(self, context, request):
            method, path, params, data = request.method, request.url, request.params, request.data
            path = path[len(self.name)+1:]
            if path:
                if path.startswith('_'): 
                    raise objects.Forbidden()
                if '/' in path:
                    path, subpath = path.split('/',1)
                else:
                    subpath = None

                fn = getattr(self.obj, path)
                
                if subpath:
                    if subpath == 'wait':
                        if method == 'GET':
                            return self.invoke(fn.waiter, params)
                        else:
                            raise objects.MethodNotAllowed()
                    raise objects.NotFound()

                if method == 'GET':
                    return self.invoke(fn, params=params, safe=True)
                elif method == 'POST':
                    return self.invoke(fn, args=data)
                else:
                    raise objects.MethodNotAllowed()
            else:
                if method == 'GET':
                    return self.obj
                else:
                    raise objects.MethodNotAllowed()

        def url(self, prefix):
            return prefix + self.name

        def link(self, prefix):
            return objects.Link(self.url(prefix))

        def embed(self,prefix, o):
            if o is None or o is self.cls:
                return self.link(prefix)
            return make_resource(o, self.url(prefix))

class Collection:
    class List(Embed):
        suffix = '/list'
        def __init__(self, name, items, selector, next):
            self.name = name
            self.items = items
            self.selector = selector
            self.next = next

        def embed(self, prefix, name):
            metadata = OrderedDict()
            metadata["collection"] = "{}{}{}".format(prefix, self.name, self.suffix)
            metadata["selector"] = self.selector
            metadata["continue"] = self.next

            return objects.List(
                kind = self.name,
                items = self.items,
                metadata = metadata,
            )
    def dict_handler(name, d=None):
        if d is None:
            d = OrderedDict()
        class Handler(Collection.Handler):
            items = d
            key = name

            def key_for(self, obj):
                return getattr(obj, self.key)

            def lookup(self, name):
                return self.items[name]

            def create(self, data):
                name = data[self.key]
                j = self.items[name] = self.cls(**data)
                return j

            def delete(self, name):
                self.items.pop(name)

            def list(self, selector, limit, next):
                return Collection.List(
                    name=self.name, 
                    items=list(self.items.values()),
                    selector=selector,
                    next=None,
                )


        return Handler

    class Handler(RequestHandler):
        def __init__(self, name, cls):
            self.cls = cls
            self.name = name

        def on_request(self, context, request):
            method, path, params, data = request.method, request.url, request.params, request.data
            col_method, path = path[len(self.name)+1:], None

            if '/' in col_method:
                col_method, path = col_method.split('/',1)

            if col_method =='id':
                if '/' in path:
                    id, obj_method = path.split('/',1)
                else:
                    id, obj_method = path, None

                if obj_method and obj_method.startswith('_'):
                    raise objects.Forbidden()
                
                if not obj_method:
                    if method == 'GET':
                        return self.lookup(id)
                    elif method == 'DELETE':
                        self.delete(id)
                        return None
                    else:
                        raise objects.MethodNotAllowed()
                elif '/' in obj_method:
                    obj_method, subpath = obj_method.split('/',1)

                    obj = self.lookup(id)
                    fn = getattr(obj, obj_method)

                    if subpath == 'wait':
                        if method != 'GET':
                            raise MethodNotAllowed()
                        return self.invoke_waiter(fn.waiter, obj,  params)
                    else:
                        raise objects.NotFound()
                else:
                    obj = self.lookup(id)
                    fn = getattr(obj, obj_method)

                    if method == 'GET':
                        return self.invoke(fn, params=params, safe=True)
                    elif method == 'POST':
                        return self.invoke(fn, data)
                    else:
                        raise objects.MethodNotAllowed()

            elif col_method =='list':
                if method == 'GET':
                    selector = params.get('where',None)
                    limit = params.get('limit')
                    next = params.get('continue')
                    if limit:
                        limit = int(limit)
                    selector = objects.parse_selector(selector)
                    return self.list(selector, limit, next)
                elif method == 'DELETE':
                    selector = params['where']
                    selector = objects.parse_selector(selector)
                    self.delete_list(selector)
                    return
                else:
                    raise objects.MethodNotAllowed()
            elif col_method == 'new':
                if method != 'POST':
                    raise objects.MethodNotAllowed()
                return self.create(data)
            elif col_method == 'delete':
                if method != 'POST':
                    raise objects.MethodNotAllowed()
                return self.delete(path)
            elif col_method == '':
                if method != 'GET':
                    raise objects.MethodNotAllowed()
                return self.cls

            raise objects.NotImplelmented(method)

        def url(self, prefix):
            return prefix+self.name

        def link(self, prefix):
            metadata = OrderedDict(
                url = self.url(prefix),
                new=self.create_args(),
                list=self.selector_args(),
                key=self.key
            )
            return objects.Dataset(
                kind=self.cls.__name__,
                metadata = metadata
            )
                    
        def create_args(self):
            return funcargs(self.cls.__init__)

        def selector_args(self):
            return ()

        def embed(self, prefix, o=None):
            if o is None or o is self.cls:
                return self.link(prefix)

            url = self.url_for(prefix, o)

            links, methods = self.extract_methods(self.cls)

            attributes = self.extract_attributes(o)

            metadata = OrderedDict(
                id = self.key_for(o),
                collection = self.url(prefix),
                url = url,
                links = links,
                methods = methods,
            )

            return objects.Resource(
                kind = self.cls.__name__,
                metadata = metadata,
                attributes = attributes,
            )

        def extract_methods(self, obj):
            return extract_methods(obj)

        def extract_attributes(self, obj):
            return extract_attributes(obj)

        def url_for(self, prefix, o):
            return "{}{}/id/{}".format(prefix,self.name,self.key_for(o))

        # override

        def key_for(self, obj):
            raise Exception('unimplemented')

        def lookup(self, key):
            raise Exception('unimplemented')

        def create(self, data):
            raise Exception('unimplemented')

        def delete(self, name):
            raise Exception('unimplemented')

        def delete_list(self, selector):
            raise Exception('unimplemented')

        def list(self, selector, limit, next):
            raise Exception('unimplemented')

        def watch(self, selector):
            raise Exception('unimplemented')

class Model:
    class PeeweeHandler(Collection.Handler):
        def __init__(self, name, cls):
            self.pk = cls._meta.primary_key
            self.key = self.pk.name
            self.fields = cls._meta.fields
            self.create_fields = list(k for k,v in self.fields.items() if not v.primary_key)
            self.indexes = [self.pk.name]
            self.indexes.extend(k for k,v in self.fields.items() if v.index or v.unique) 
            Collection.Handler.__init__(self, name, cls)


        def create_args(self):
            return self.create_fields

        def selector_args(self):
            return self.indexes

        def extract_attributes(self, obj):
            attr = OrderedDict()
            for name in self.fields:
                a = getattr(obj, name)
                if isinstance(a, uuid.UUID):
                    a = a.hex
                attr[name] = a
            return attr

        def key_for(self, obj):
            name = self.pk.name
            attr = getattr(obj, name)
            if isinstance(attr, uuid.UUID):
                attr = attr.hex
            return attr

        def lookup(self, name):
            return self.cls.get(self.pk == name)

        def create(self, data):
            return self.cls.create(**data)

        def delete(self, name):
            self.cls.delete().where(self.pk == name).execute()

        def delete_list(self, selector):
            self.select_on(self.cls.delete(), selector).execute()

        def select_on(self, items, selector):
            for s in selector:
                print(selector,s)
                key, operator, values = s.key, s.__class__, s.value
                field = self.fields[key]
                if operator == objects.Operator.Equals:
                    items = items.where(field == values)
                elif operator == objects.Operator.NotEquals:
                    items = items.where(field != values)
                else:
                    raise Exception('unsupported')
            return items

        def list(self, selector, limit, next):
            items = self.cls.select()
            pk = self.pk
            next_token = None
            if selector:
                items = self.select_on(items, selector)

            if limit or next:
                items = items.order_by(pk)
                if next:
                    items = items.where(pk > next)
                if limit:
                    items = items.limit(limit)

                items = list(items)
                if items:
                    next_token = self.key_for(items[-1])
            else:
                items = list(items)

            return Collection.List(
                name=self.name, 
                selector=objects.dump_selector(selector),
                items=items,
                next=next_token
            )

class Namespace:
    def __init__(self, name=""):
        self.handlers = OrderedDict()
        self.paths = OrderedDict()
        self.service = None
        if name:
            prefix="/{}/".format(name)
        else:
            prefix="/"
        self.prefix=prefix

    def register(self,obj, handler):
        obj.Handler = handler
        return self.add()(obj)

    def add(self, name=None):
        def _add(obj):
            if isinstance(obj, types.FunctionType):
                obj.Handler = FunctionHandler
            self.add_handler(name, obj.Handler, obj)
            return obj

        return _add

    def add_handler(self, name, handler, obj):
        n = obj.__name__ if name is None else name
        self.handlers[n] = handler(n, obj)
        self.paths[obj]=n
        self.service = None

    def index(self):
        if self.service is None:
            attrs = OrderedDict()
            for name,o in self.handlers.items():
                attrs[name] = o.link(prefix=self.prefix)
            self.service = objects.Service('Index',
                metadata={'url':self.prefix},
                attributes=attrs,
            )
        return self.service

    def handle(self, request):
        path = request.path[:]
        if path == self.prefix or path == self.prefix[:-1]:
            out = self.index()
        elif path:
            p = len(self.prefix)
            path = path[p:]
            name = path.split('/',1)[0].split('.',1)[0]
            if name in self.handlers:
                data  = request.data.decode('utf-8')
                if data:
                    args = objects.parse(data)
                else:
                    args = None

                params = request.args

                context = {}
                request = objects.Request(
                    method=request.method,
                    url=path,
                    params=params, 
                    headers={},
                    data=args,
                )

                out = self.handlers[name].on_request(context, request)
            else:
                raise objects.NotFound(path)
        
        def transform(o):
            if isinstance(o, type) or isinstance(o, types.FunctionType):
                if o in self.paths:
                    return self.handlers[self.paths[o]].embed(self.prefix, o)
            elif o.__class__ in self.paths:
                return self.handlers[self.paths[o.__class__]].embed(self.prefix, o)
            elif isinstance(o, Embed):
                return o.embed(self.prefix, path)
            return o

        if out is None:
            return Response('', status='204 None')

        result = objects.dump(out, transform)
        return Response(result, content_type=objects.CONTENT_TYPE) 
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
