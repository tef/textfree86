from textfree86 import cli

demo = cli.Command('demo', 'cli example programs')

@demo.run('''
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

if __name__ == '__main__':
    cli.main(demo)
