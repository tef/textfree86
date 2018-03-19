# TextFree86: Finally, a network transparent command line!

*This readme is not ready for an audience yet. I'd appreciate if you didn't link to it, thank you*

### Network transparent means more than just SSH

Take an imaginary CLI tool, that inserts some JSON into a database:

```
$ insert-into-database record.json
$ insert-into-database records.json --overwrite
```

Running it from a different machine is a little clumsy, but possible:

```
$ scp record.json:user@remote.host .
$ ssh user@remote.host insert-into-database record.json
```

Similarly, running a command inside a container can be a little frustating

```
$ container-exec --flag-i-forget-every-time run insert-into-database ... # uh wait what do I do here
```

What you want is a command that parses the input on your machine, but does the work on another. Inevitably, you end up writing another command line program to achieve this.

```
$ remote-insert-into-database record.json  # run a remote command with a local file
```

TextFree86 is a framework that comes with a reusable program to do this for you. Write a local CLI tool, get a remote CLI tool for free.

### Writing a remote CLI is Effort, so don't do it.

There are a couple of well worn strategies for writing a new remote command-line tool:

- Hack the scripts. A new local script that pipes the file over SSH, and a new remote script to read from the pipe instead of a file. 
- Tidy them up. Pull out the command and embed it into a web service. Expose an API, probably JSON, and write another command line tool. 

TextFree86 does both of these for you.

All TextFree86 programs can take input over a pipe, rather than as arguments, and comes with a `textfree86` tool to call it. 

```
local.host$ alias remote-insert-into-database='textfree86 "ssh datatbase insert-into-database ---pipe"'
local.host$ remote-insert-into-database record.json    # use a local file, but running a remote command
```

A TextFree86 command also knows how to expose itself over HTTP*:

```
remote.host$ insert-into-database --serve
```

... and the `textfree86` program takes URLs too*:

```
local.host$ alias remote-insert-into-database='textfree86 http://remote.host/insert-into-database'
local.host$ remote-insert-into-database record.json
```

[Note: * Pipes work now, but HTTP support will come later]

### But wait, there's more!

A TextFree86 program can do more than *accept* input over a pipe, it can *describe* the input it accepts too.

In other words, tab completion works out of the box!

```
local.host$ complete -o nospace -C remote-insert-into-database
local.host$ remote-insert-into-database --over<TAB>
--overwrite
```

There are even use cases where TextFree86 exhibits a little more than just novelty and trickery: A TextFree86 program run inside a container can be run like a program outside of one, reading and writing file arguments, environment variables, or configuration files. 

The most useful feature of `textfree86` is that you don't need to update the `textfree86` program every time the remote command line changes. Instead of hardcoding how each program works, `textfree86` knows enough about command line parsing, and the remote command knows how to describe what input it needs.

That's what 'network transparent' means, but TextFree86 is more than just running a program over a network.

TextFree86 is about running remote or sandboxed programs, without having to use a different tool for each one.

## A real example program:

```
import subprocess
from textfree86 import cli

cmd = cli.Command('logdetails','write the uptime, uname, etc to a given file')
@cmd.run('--uptime? --uname? output:outfile') # this describes how to parse cmd line args
def cmd_run(uptime, uname, output): # uptime, uname are boolean, output is a filehandle
    out = []
    if uptime:
        p= subprocess.run("uptime", stdout=subprocess.PIPE)
        output.write(p.stdout)
        out.append("uptime")
    if uname:
        p= subprocess.run("uname", stdout=subprocess.PIPE)
        output.write(p.stdout)
        out.append("uname")
    if out:
        return "Wrote {} to log".format(",".join(out))
    else:
        return "Wrote nothing to log, try --uname/--uptime"

cmd.main(__name__) 
```

## How do I use the Library?

Please note: Although TextFree86 implementation requires Python 3.6, the underlying protocol does not.

### Another Example Program

A textfree86 program consists of `cli.Commands()`, chained together, used to decorate functions to dispatch:

```
cmd = cli.Command('florb','florb the morps')
@cmd.run("one [two] [three...]")
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

### Subcommands

`Command` can be nested, giving a `cmd one <args>` `cmd two <args>` like interface:
``` 
root = cli.Command('example', 'my program')

subcommand = cli.subcommand('one', 'example subcommand')

@subcommand.run(...)
def subcommand_run(...):
    ...
```

`cmd help one` `cmd one --help`, `cmd help two` `cmd two --help` will print out the manual and usage for `one` and `two` respectively.

The parameter to `run()`, is called an argspec.

### Argspec

An argspec is a string that describes how to turn CLI arguments into a dictionary of name, value pairs. For example:

- "x y z" given "1 2 3" gives {"x":1, "y":2, "z":3}
- "[x...]" given "a b c" gives {"x":["a","b","c"]}

This is used to call the function underneath, so every value in the function must be present in the argspec. When no argspec is provided, `textfree86` defaults to a string of argument names, i.e `foo(x,y,z)` gets `"x y z"`. 

The dictionary passed will contain a value for every name in the argspec. An argspec resembles a usage string, albeit with a standard formatting for flags or other command line options:

- `--name?` describes a switch, which defaults to `False`, but when present, is set to `True`, additionally, `--name=true` and `--name=false` both work.

- `--name` describes a normal flag, which defaults to `None`, and on the CLI `--name=value` sets it.

- `--name...` describes a list flag, which defaults to `[]`, and on the CLI `--name=value` appends to it

- `name` describes a positional argument. It must come after any flags and before any optional positional arguments.

- `[name]` describes an optional positional argument. If one arg is given for two optional positional args, like `[x] [y]`, then the values are assigned left to right.

- `[name...]` describes a tail positonal argument. It defaults to `[]`, and all remaining arguments are appended to it.

A short argspec has four parts, `<flags> <positional> [<optional positional>]* [<tail positional>...]`

### Long Argspec

Passing a multi-line string allows you to pass in short descriptions of the arguments, using `# ...` at the end of each line.

```
demo = cli.Command('demo', 'cli example programs')
@demo.run('''
    --switch?       # a demo switch
    --value:str     # pass with --value=...
    --bucket:int... # a list of numbers
    pos1            # positional
    [opt1]          # optional 1
    [opt2]          # optional 2
    [tail...]       # tail arg
''')
def run(switch, value, bucket, pos1, opt1, opt2, tail):
    """a demo command that shows all the types of options"""
    return [switch, value, bucket, pos1, opt1, opt2, tail]
```

### Argument Types

A field can contain a parsing instruction, `x:string` or `x:int`

- `int`, `integer`
- `float`, `num`, `number`
- `str`, `string`
- `bool`, `boolean` (accepts 'true', 'false')

Example `arg1:str arg2:int` describes a progrm that would accept `foo 123` as input, passing `{'arg1': 'foo', 'arg2': 123}` to the function.

An untyped field tries to convert the argument to an integer or floating point number, losslessly, and if successful, uses that.

This might be a bad idea, but it is up to the client on how best to interpret arguments.  

### Files

Files can also be sent as command line arguments, or written to as output from the program.

This function gets two file handle like objects passed in:

```
@subcommand.run("data:infile output:outfile")
def subcommand_run(data, output):
    for line in data.readlines():
        output.write(line)
```

### Stretch Goals: Environment Variables, Paths, Config Files

Maybe `cmd subcommand --foo='...'` could use `foo:env` as the argspec to  from `CMD_SUBCOMMAND_FOO` or `--env=<...>` on the command line. Similarly, types for directories, or config files.

### Stretch Goals: Stdin/Stdout/Stderr and Streams

Files work by sending over the entire contents before and after, but a different approach is needed for streams. Please Wait.

## Using it

### Pipe Mode 

You can skip the ssh part:

```
$ ./textfree86.py './script.py --pipe' <args> <to> <script>
$ ./textfree86.py ./script.py --pipe -- <args> <to> <script>
```

### Stretch Goals: Caching

Keeping a copy of the command description around to speed up tab completion.

### Stretch Goals: Server, Proxy

Instead of using a pipe, HTTP is an option. Using plain old GETs to find descriptions of commands, and either through long polling, or websocket to run one.

It should be possible to proxy a command, as well as proxy to commands on different machines.

### Stretch Goals: API 

I guess this means documenting my code. Oh well.

