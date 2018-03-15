# TextFree86: Finally, a network transparent getopt(3)

This readme is semi-fictional.

TextFree86 is a CLI framework that lets you run your command line program across the network.

Take a `textfree86` program,

```
$ florb
Hello, World!
```

... serve it over the network, 

```
$ florb :serve --port=1729
```

... and run it from another machine, using the standalone `textfree86` command!

```
$ alias remoteflorb='textfree86 http://1.2.3.4:1729/florb/ --'
$ remoteflorb
Hello, world!
```

* soon!

The `textfree86` program doesn't need any configuration beyond the URL and any credentials to access the remote CLI.

# Writing a CLI (This works)

```
from textfree86 import cli

cmd = cli.Command('florb','florb the morps')
@cmd.run()
def cmd_run():
    return 'Hello, World'
```

# Parsing Command-Line Options (and this)

`.run()` takes a string describing how to parse the command line argument.

A short argspec has four parts, `<--flags> <positional> <optional positional?> <tail positional...>`

For example, `one two? three...` describes one positional, one optional, and a tail option:

```
@cmd.run("one two? three...")
def cmd_run(one, two, three):
    return [one, two, three]
```

gives this output:

```
$ florb one 
["one", None, []]

$ florb one two three four
["one", "two", ["three", "four]]
```

If needed, these options can be passed as flags: 

```
$ florb --one=one --two=two --three=three --three=four
["one", "two", ["three", "four]]
```

Of course, `florb help` and `florb --help` work. 


## Argspec

The simplest argspec for `foo(x,y,z)` is `"x y z"`. An argspec describes how to build up a dictionary of arguments, to pass to the function.  The dictionary contains a value for every argument, `None`, `[]`, or `False` if not present.

- `--flag?` describes a switch, which defaults to `False`, but when present, is set to `True`, additionally, `--flag=true` and `--flag=false` both work.

- `--flag` describes a normal flag, which defaults to `None`, and `--flag=value` sets it.

- `--flag...` describes a list flag, which defaults to `[]`, and each `--flag=value` appends to it

- `x` describes a positional argument. It must come after any flags and before any optional positional arguments.

- `x?` describes an optional positional argument. If one arg is given for two optional positional args, like `x? y?`, then the values are assigned left to right.

- `x...` describes a tail positonal argument. It defaults to `[]`, and all remaining arguments are appended to it.

## Long Argspec

Passing a multi-line string allows you to pass in short descriptions of the arguments.

```
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
def run(switch, value, bucket, pos1, opt1, opt2, tail):
    """a demo command that shows all the types of options"""
    return [switch, value, bucket, pos1, opt1, opt2, tail]
```

## Argument Types

A field can contain a parsing instruction, `x:string` or `x:int`

- `int`, `integer`
- `float`, `num`, `number`
- `str`, `string`
- `bool`, `boolean` (accepts 'true', 'false')

Example `arg1:str arg2:int` describes a progrm that would accept `foo 123` as input, passing `{'arg1': 'foo', 'arg2': 123}` to the function.

An untyped field tries to convert the argument to an integer or floating point number, losslessly, and if successful, uses that.

This might be a bad idea, but it is up to the client on how best to interpret arguments.  


## Subcommands

`Command` can be nested, giving a `cmd one <args>` `cmd two <args>` like interface:
``` 
root = cli.Command('example', 'my program')

subcommand = cli.subcommand('one', 'example subcommand')

@subcommand.run(...)
def subcommand_run(...):
    ...
```

`cmd help one` `cmd one --help`, `cmd help two` `cmd two --help` will print out the manual and usage for `one` and `two` respectively.


# Command Completion (Not yet)

Using `cmd :complete <command line>` or `cmd :complete` and setting the Bash Completion environment variables will return a list of possible completions.


# Network Mode (Not Yet)

With the command/subcommand classes, the CLI framework looks like a Router inside a web framework. Bash completion means being able to expose options without running the command.

The `textfree86` client asks for the completition information, parses the command line arguments, sends them across the network, and prints the responses.

# Stdin/Stdout (Not Yet)

Using a mixture of websockets and HTTP, the `textfree86` program wraps up any input, streams it to the remote server, and streams back any output.

# Environment Variables, Local Configuration (Not Yet)

Instead of positional options or option flags, program configuration can be stored in environment variables, or local files. These can be overridden by option flags too.

A command `cmd subcommand` with environment setting `env`, can read from `CMD_SUBCOMMAND_ENV` or `--env=<...>` on the command line.

An option should be able to default to using a known file, too.

# Files, Paths, Directories 

Like streams, Files can also be sent as command line arguments, or written to as output from the program.

