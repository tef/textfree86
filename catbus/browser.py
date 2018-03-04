import os
import sys
import time

from urllib.parse import urljoin

import requests

from . import dom, client

VERBS = set('get set create delete update list call exec tail log watch wait'.split())

def parse_arguments(args):
    if not args:
        return []

    actions = []
    while args:
        if args[0] in VERBS:
            verb = args.pop(0) 
        else:
            verb = None
    
        if not args:
            raise Exception('missing')

        path = args.pop(0).split(':')
        for p in path[:-1]:
            if p: actions.append(Action(p, None, None))

        if not args:
            actions.append(Action(path[-1], verb, []))
            return actions
        else:
            path = path[-1]


        arguments = []
        while args:
            arg = args[0]
            if arg in VERBS:
                break
            arg = args.pop(0)
            if arg.startswith('--'):
                key, value = arg[2:].split('=',1)
                value = try_num(value)
                arguments.append((key, value))
            else:
                arguments.append(arg)

        actions.append(Action(path, verb, arguments))
    return actions

def try_num(num):
    try:
        f = float(num)
        n = str(f)
        if num == n:
            return f
        i = int(num)
        n = str(i)
        if num == n:
            return i
        return num
    except:
        return num

class Action:
    def __init__(self, path, verb, arguments):
        self.path = path
        self.verb = verb
        self.arguments = arguments

def cli(c, endpoint, args):

    actions = parse_arguments(args)

    obj = c.Get(endpoint)

    for action in actions[:-1]:
        if isinstance(obj, client.Navigable):
            request = obj.perform(action)
            # print('DEBUG', action.path, request.url)
        else:
            raise Exception('can\'t navigate to {}'.format(action.path))
        obj = c.Call(request)

    if actions:
        action = actions[-1]
        attr = getattr(obj, action.path)
        if isinstance(attr, client.Navigable):
            request = obj.perform(action)
            # print('DEBUG', action.path, request.url)
            obj = c.Call(request)
        elif not action.verb:
            obj = attr
    if isinstance(obj, client.RemoteWaiter):
        obj  = c.Wait(obj)

    if isinstance(obj, client.Navigable):
        obj = obj.display()
    print(obj)
    return -1

    
