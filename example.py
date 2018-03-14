from textfree86 import cli

root = cli.Command('example', 'cli example programs')

nop = root.subcommand('nop', 'nothing')
@nop.run()
def nop(context):
    pass

add = root.subcommand('add', "adds two numbers")
@add.run("a b")
def add_cmd(context, a, b):
    return a+b

echo = root.subcommand('echo', "echo")
@echo.run("--reverse? line:str...")
def echocmd(context, line, reverse):
    """echo all arguments"""
    if reverse:
        return (" ".join(x for x in line))[::-1]
    return " ".join(x for x in line)

demo2 = root.subcommand('demo2', "demo of argspec")
@demo2.run('''
    --switch?       # a demo switch
    --value:str     # pass with --value=...
    --bucket:int... # a list of numbers 
    pos1            # positional
    opt1?           # optional 1
    opt2?           # optional 2
    tail...         # tail arg
''')
def run(context, switch, value, bucket, pos1, opt1, opt2, tail):
    """a demo command that shows all the types of options"""
    output = [ 
            "\tswitch:{}".format(switch),
            "\tvalue:{}".format(value),
            "\tbucket:{}".format(bucket),
            "\tpos1:{}".format(pos1),
            "\topt1:{}".format(opt1),
            "\topt2:{}".format(opt2),
            "\ttail:{}".format(tail),
    ]
    return "\n".join(output)

demo = root.subcommand('demo', "demo of argspec")
@demo.run('--switch? --value --bucket... pos1 opt1? opt2? tail...')
def run(context, switch, value, bucket, pos1, opt1, opt2, tail):
    output = [ 
            "\tswitch:{}".format(switch),
            "\tvalue:{}".format(value),
            "\tbucket:{}".format(bucket),
            "\tpos1:{}".format(pos1),
            "\topt1:{}".format(opt1),
            "\topt2:{}".format(opt2),
            "\ttail:{}".format(tail),
    ]
    return "\n".join(output)

ev = root.subcommand('cat', "line at a time echo")
@ev.run()
async def eval_cmd(context):
    async for msg in context.stdin():
        await context.stdout.write(msg)

if __name__ == '__main__':
    cli.main(root)
