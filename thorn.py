import os
import sys
import types

def try_num(arg):
    try:
        i = int(arg)
        if str(i) == arg: return i
    except:
        pass
    try:
        f = float(arg)
        if str(f) == arg: return f
    except:
        pass
    return arg

def extract_args(template, argv):
    return args

def parse_argspec(argspec):
    positional = []
    optional = []
    tail = None
    flags = []
    args = argspec.split()

    nargs = len(args) 
    while args: # flags
        if not args[0].startswith('--'): break
        arg = args.pop(0)
        if arg.endswith(('...', '?')): raise Exception('badarg')
        flags.append(arg[2:])

    while args: # positional
        if args[0].endswith(('...', '?')): break
        arg = args.pop(0)
        if arg.startswith('--'): raise Exception('badarg')
        positional.append(arg)

    while args: # optional
        if args[0].endswith('...'): break
        arg = args.pop(0)
        if arg.startswith('--'): raise Exception('badarg')
        if not arg.endswith('?'): raise Exception('badarg')
        optional.append(arg[:-1])

    if args: # tail
        arg = args.pop(0)
        if arg.startswith('--'): raise Exception('badarg')
        if arg.endswith('?'): raise Exception('badarg')
        if not arg.endswith('...'): raise Exception('badarg')
        tail = arg[:-3]

    if args:
        raise Exception('bad argspec')

    return nargs, {'positional': positional, 'optional': optional , 'tail': tail, 'flags': flags }


class wire:
    class Result:
        def __init__(self, exit_code, value):
            self.exit_code = exit_code
            self.value = value
            
    class Action:
        def __init__(self, mode, command, argv, errors=()):
            self.mode = mode
            self.path = command
            self.argv = argv
            self.errors = errors

    class Command:
        def __init__(self, prefix, name, subcommands, short, long, options):
            self.prefix = prefix
            self.name = name
            self.subcommands = subcommands
            self.short, self.long = short, long
            self.options = options


        def invoke(self, path,argv, environ):
            if argv and argv[0] == "help":
                action = self.invoke(path, argv[1:], environ)
                return wire.Action("help", action.path, {'manual': True})
            if argv and argv[0] in self.subcommands:
                return self.subcommands[argv[0]].invoke(path+[argv[0]], argv[1:], environ)

            options = []
            flags = {}
            args = {}

            for arg in argv:
                if arg.startswith('--'):
                    if '=' in arg:
                        key, value = arg[2:].split('=',1)
                    else:
                        key, value = arg[2:], None
                    if key not in flags:
                        flags[key] = []
                    flags[key].append(value)
                else:
                    options.append(arg)

            if 'help' in flags:
                return wire.Action("help", path, {'usage':True})

            if not self.options:
                return wire.Action("help", path, {'usage':True})

            for name in self.options['flags']:
                if name not in flags:
                    args[name] = None
                    continue

                key, values = name, flags.pop(name)
                if not values or values[0] is None:
                    return wire.Action("error", path, {'usage':True}, errors=("missing value for option flag {}".format(key),))
                if len(values) > 1:
                    return wire.Action("error", path, {'usage':True}, errors=("duplicate option flag for: {}".format(key, ", ".join(repr(v) for v in values)),))

                args[key] = try_num(value)

            if flags:
                return wire.Action("error", path, {'usage': True}, errors=("unknown option flags: --{}".format("".join(flags)),))


            if self.options['positional']:
                for name in self.options['positional']:
                    if not options: 
                        return wire.Action("error", path, {'usage':'True'}, errors=("missing option: {}".format(name),))

                    args[name] = try_num(options.pop(0))

            if self.options['optional']:
                for name in self.options['optional']:
                    if not options: 
                        args[name] = None
                    else:
                        args[name] = try_num(options.pop(0))

            if self.options['tail']:
                tail = []
                while options:
                    tail.append(try_num(options.pop(0)))

                args[self.options['tail']] = tail

            if not options:
                return wire.Action("call", path, args)
            else:
                return wire.Action("error", path, {'usage':True}, errors=("unrecognised option: {!r}".format(" ".join(options)),))

        def help(self, path, *, usage=False):
            if path and path[0] in self.subcommands:
                return self.subcommands[path[0]].help(path[1:], usage=usage)
            else:
                if usage:
                    return self.usage()
                return self.manual()
            
        def manual(self):
            output = []
            full_name = list(self.prefix)
            full_name.append(self.name)
            output.append("{}{}{}".format(" ".join(full_name), (" - " if self.short else ""), self.short))

            output.append("")

            output.append(self.usage())
            output.append("")

            if self.long:
                output.append('description:')
                output.append(self.long)
                output.append("")

            if self.subcommands:
                output.append("commands:")
                for cmd in self.subcommands.values():
                    output.append("\t{.name}\t{}".format(cmd, cmd.short))
                output.append("")
            return "\n".join(output)

        def usage(self):
            args = []
            if self.subcommands:
                args.append('<command>')
            if self.options:
                if self.options['flags']:
                    args.extend("[--{0}=<{0}>]".format(o) for o in self.options['flags'])
                if self.options['positional']:
                    args.extend("<{}>".format(o) for o in self.options['positional'])
                if self.options['optional']:
                    args.extend("[<{}>]".format(o) for o in self.options['optional'])
                if self.options['tail']:
                    args.append("[<{}>...]".format(self.options['tail']))

            full_name = list(self.prefix)
            full_name.append(self.name)
            return "usage: {} {}".format(" ".join(full_name), " ".join(args))


class cli:
    class Command:
        def __init__(self, name, short):
            self.name = name
            self.prefix = [] 
            self.subcommands = {}
            self.run_fn = None
            self.short = short
            self.options = None
            self.nargs = 0

        def subcommand(self, name, short):
            cmd = cli.Command(name, short)
            cmd.prefix.extend(self.prefix)
            cmd.prefix.append(self.name)
            self.subcommands[name] = cmd
            return cmd

        def call(self, path, argv):
            if path and path[0] == 'help':
                return self.help(path[1:])
            elif path and path[0] in self.subcommands:
                return self.subcommands[path[0]].call(path[1:], argv)
            elif self.run_fn and len(argv) == self.nargs:
                return self.run_fn({}, **argv)
            else:
                return wire.Result(-1, "bad options")

        def run(self, argspec=None):

            if argspec is not None:
                self.nargs, self.options = parse_argspec(argspec)

            def decorator(fn):
                self.run_fn = fn

                args = list(self.run_fn.__code__.co_varnames[:self.run_fn.__code__.co_argcount])
                if args and args[0] == 'context':
                    args.pop(0)
                args = [a for a in args if not a.startswith('_')]
                
                if not self.options:
                    self.options = {'positional': args, 'optional': [] , 'tail': None, 'flags': []}
                    self.nargs = len(args)
                else:
                    if self.nargs != len(args):
                        raise Exception('bad option definition')

                return fn
            return decorator

        def render(self):
            long_description =self.run_fn.__doc__ if self.run_fn else None
            return wire.Command(
                name = self.name,
                prefix = self.prefix,
                subcommands = {k: v.render() for k,v in self.subcommands.items()},
                short = self.short,
                long = long_description,
                options = self.options, 
            )
                
    #end Command

    def main(root):
        argv = sys.argv[1:]
        environ = os.environ

        obj = root.render()

        action = obj.invoke([], argv, environ)
    
        if action.mode == "help":
            result = obj.help(action.path, usage=action.argv.get('usage'))
        elif action.mode == "error":
            print("error: {}".format(", ".join(action.errors)))
            result = obj.help(action.path, usage=action.argv.get('usage'))
        elif action.mode == "call":
            result = root.call(action.path, action.argv)

        if isinstance(result, wire.Result):
            exit_code = result.exit_code
            result = result.value
        else:
            exit_code = -len(action.errors)

        if isinstance(result, types.GeneratorType):
            for r in result:
                print(r)
        else:
            print(result)

        sys.exit(exit_code)

root = cli.Command('example', 'cli example programs')

nop = root.subcommand('nop', 'nothing')

add = root.subcommand('add', "adds two numbers")

@add.run("a b")
def add_cmd(context, a, b):
    return a+b

echo = root.subcommand('echo', "echo")
@echo.run("--reverse line...")
def echocmd(context, line, reverse):
    """echo all arguments"""
    if reverse:
        return (" ".join(line))[::-1]
    return " ".join(str(x) for x in line)

ev = root.subcommand('cat', "line at a time echo")
@ev.run()
async def eval_cmd(context):
    async for msg in context.stdin():
        await context.stdout.write(msg)

if __name__ == '__main__':
    cli.main(root)
