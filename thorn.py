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
    args = {}
    for name in template:
        arg = argv.pop(0)
        arg = try_num(arg)
        args[name] = arg
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
        def __init__(self, name, subcommands, short, long, arguments):
            self.name = name
            self.subcommands = subcommands
            self.short, self.long = short, long
            self.arguments = arguments


        def invoke(self, path,argv, environ):
            if argv and argv[0] == "help":
                action = self.invoke(path, argv[1:], environ)
                return wire.Action("help", action.path, action.argv)
            if argv and argv[0] in self.subcommands:
                return self.subcommands[argv[0]].invoke(path+[argv[0]], argv[1:], environ)
            if len(self.arguments) == len(argv):
                argv = extract_args(self.arguments, argv)
                return wire.Action("call", path, argv)
            else:
                return wire.Action("error", path, argv, errors=("bad_arguments",))

        def help(self, path, argv):
            if path and path[0] in self.subcommands:
                return self.subcommands[path[0]].help(path[1:], argv)
            else:
                return self.usage()
            

        def usage(self):
            output = []
            args = " ".join(self.arguments)
            output.append("usage: {0.name} {1}".format(self, args))
            if self.subcommands:
                output.append("")
                for cmd in self.subcommands.values():
                    output.append("{.name}\t{}".format(cmd, cmd.short))
            return "\n".join(output)

class cli:
    class Command:
        def __init__(self, name, short):
            self.name = name
            self.subcommands = {}
            self.run_fn = None
            self.short = short
            self.positional = None

        def subcommand(self, name, short):
            cmd = cli.Command(name, short)
            self.subcommands[name] = cmd
            return cmd

        def call(self, path, argv):
            if path and path[0] == 'help':
                return self.help(path[1:], argv)
            elif path and path[0] in self.subcommands:
                return self.subcommands[path[0]].call(path[1:], argv)
            elif self.run_fn and len(argv) == len(self.positional):
                return self.run_fn({}, **argv)
            else:
                return wire.Result(-1, self.help(path, argv))

        def run(self, positional=None):
            if positional is not None:
                self.positional = positional.split(' ')

            def decorator(fn):
                self.run_fn = fn
                if self.positional is None:
                    positional =  self.run_fn.__code__.co_varnames[:self.run_fn.__code__.co_argcount]
                    self.positional = [a for a in positional if not (a.startswith('_') or a in ('self','context','cls'))]
                return fn
            return decorator

        def render(self):
            long_description =self.run_fn.__doc__ if self.run_fn else self.short
            return wire.Command(
                name = self.name,
                subcommands = {k: v.render() for k,v in self.subcommands.items()},
                short = self.short,
                long = long_description,
                arguments = self.positional,
            )
                
    #end Command

    def main(root):
        argv = sys.argv[1:]
        environ = os.environ

        obj = root.render()

        action = obj.invoke([], argv, environ)
    
        if action.mode == "help":
            result = obj.help(action.path, action.argv)
        elif action.mode == "error":
            print("error: {}".format(" ".join(action.errors)))
            result = obj.help(action.path, action.argv)
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


root = cli.Command('example', 'example title')

add = root.subcommand('add', "adds two numbers")

@add.run(
    positional="a b",
)
def add_cmd(context, a, b):
    return int(a)+int(b)

mul = root.subcommand('mul', "multiplier")
@mul.run()
def add_cmd(context, a,b):
    """multiplies two numbers, slow"""
    yield "nearly"
    yield int(a)*int(b)

ev = root.subcommand('echo', "line at a time echo")
@ev.run()
async def eval_cmd(context):
    async for msg in context.stdin():
        await context.stdout.write(msg)

if __name__ == '__main__':
    cli.main(root)
