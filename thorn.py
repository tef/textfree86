import os
import sys
import types

class Result:
    def __init__(self, exit_code, value):
        self.exit_code = exit_code
        self.value = value

class Command:
    def __init__(self, name):
        self.name = name
        self.subcommands = {}
        self.run_fn = None
        self.short = None

    def Subcommand(self, name):
        cmd = Command(name)
        self.subcommands[name] = cmd
        return cmd

    def run(self, short=None):
        def decorator(fn):
            self.run_fn = fn
            self.short = short
            return fn
        return decorator

    def route(self, argv, environ):
        if argv and argv[0] in self.subcommands:
            return self.subcommands[argv[0]].route(argv[1:], environ)
        elif self.run_fn:
            return self.run_fn({}, *argv)
        else:
            return Result(-1, self.usage())

    def short_description(self):
        return self.short 

    def long_description(self):
        if self.run_rn:
            return self.run_fn.__doc__


    def usage(self):
        output = []
        output.append("usage: {0.name} <options>".format(self))
        if self.subcommands:
            output.append("")
            for cmd in self.subcommands.values():
                output.append("{.name}\t{}".format(cmd, cmd.short_description()))
        return "\n".join(output)
    
    def main(self):
        argv = sys.argv
        environ = os.environ
        result = self.route(argv[1:], environ)
        
        exit_code = 0
        if isinstance(result, Result):
            exit_code = result.exit_code
            result = result.value
        if isinstance(result, types.GeneratorType):
            for r in result:
                print(r)
        else:
            print(result)
        sys.exit(exit_code)



root = Command('example')

add = root.Subcommand('add')

@add.run("adds two numbers")
def add_cmd(context, a, b):
    return a+b

mul = root.Subcommand('mul')
@mul.run("multiplier")
def add_cmd(context, a,b):
    """multiplies two numbers, slow"""
    yield "nearly"
    yield a*b

ev = root.Subcommand('echo')

@ev.run()
async def eval_cmd(context):
    async for msg in context.stdin():
        await context.stdout.write(msg)

if __name__ == '__main__':
    root.main()
