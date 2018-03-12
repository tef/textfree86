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
                return wire.Action("help", action.path, {})
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
                        key, value = arg[2:], ()
                    if key not in flags:
                        flags[key] = []
                    flags[key].append(value)
                else:
                    options.append(arg)

            if 'help' in flags:
                return wire.Action("help", path, {})

            check_options = True

            for name in self.options['flags']:
                if name not in flags:
                    args[name] = None
                    continue

                key, values = name, flags.pop(name)
                if not values:
                    return wire.Action("error", path, args, errors=("missing value for option flag {}".format(k),))
                if len(values) > 1:
                    return wire.Action("error", path, args, errors=("duplicate values for {}: {}".format(key, ", ".join(repr(v) for v in values)),))
                elif key in self.options['flags']:
                    args[key] = try_num(value)

            if flags:
                return wire.Action("error", path, args, errors=("unknown option flags: --{}".format("".join(flags)),))


            if self.options['positional']:
                for name in self.options['positional']:
                    if not options: 
                        return wire.Action("error", path, args, errors=("missing option: {}".format(name),))

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
                return wire.Action("error", path, args, errors=("unrecognised option: {!r}".format(" ".join(options)),))

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
            self.positional = None
            self.optional = None
            self.tail = None
            self.flags = None
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

        def run(self, positional=None, optional=None, tail=None, flags=None):
            self.positional = positional.split() if positional is not None else []
            self.optional = optional.split() if optional is not None else []
            self.tail = tail if tail else None
            self.flags = flags.split() if flags is not None else []
            self.nargs = sum([
                (len(self.positional) if self.positional else 0),
                (len(self.optional) if self.optional else 0),
                (1 if self.tail else 0),
                (len(self.flags) if self.flags else 0),
            ])

            def decorator(fn):
                self.run_fn = fn

                args = list(self.run_fn.__code__.co_varnames[:self.run_fn.__code__.co_argcount])
                if args and args[0] == 'context': args.pop(0)
                args = [a for a in args if not a.startswith('_')]
                
                if not any((self.positional, self.optional, self.tail, self.flags)):
                    self.positional = args
                    self.optional, self.tail, self.flags = None, None, None
                    self.nargs = len(args)
                else:
                    if self.nargs != len(args):
                        raise Exception('bad option definition')

                return fn
            return decorator

        def render(self):
            long_description =self.run_fn.__doc__ if self.run_fn else self.short
            return wire.Command(
                name = self.name,
                prefix = self.prefix,
                subcommands = {k: v.render() for k,v in self.subcommands.items()},
                short = self.short,
                long = long_description,
                options = {
                    'positional':self.positional,
                    'optional': self.optional,
                    'tail': self.tail,
                    'flags': self.flags,
                }
            )
                
    #end Command

    def main(root):
        argv = sys.argv[1:]
        environ = os.environ

        obj = root.render()

        action = obj.invoke([], argv, environ)
    
        if action.mode == "help":
            result = obj.help(action.path)
        elif action.mode == "error":
            print("error: {}".format(", ".join(action.errors)))
            result = obj.help(action.path, usage=True)
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

add = root.subcommand('add', "adds two numbers")

@add.run(positional="a b",)
def add_cmd(context, a, b):
    return a+b

echo = root.subcommand('echo', "echo")
@echo.run(positional="", optional="", tail="line", flags='reverse')
def add_cmd(context, line, reverse):
    if reverse:
        return (" ".join(line))[::-1]
    return " ".join(line)

ev = root.subcommand('cat', "line at a time echo")
@ev.run()
async def eval_cmd(context):
    async for msg in context.stdin():
        await context.stdout.write(msg)

if __name__ == '__main__':
    cli.main(root)
