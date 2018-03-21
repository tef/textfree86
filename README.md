## TextFree86: A network transparent command line framework.

*This readme is not ready for an audience yet. I'd appreciate if you didn't link to it, thank you*

TextFree86 is tool (& library) for running remote or sandboxed command-line programs. It's a little like using SSH, but a lot more powerful. To understand the difference between them, it's best to start with an example.

### Network transparent means more than just SSH

Take an imaginary CLI tool, that inserts some JSON into a database:

```
local.host$ insert-into-database records.json # a file on local.host
local.host$ insert-into-database records.json --overwrite
```

Unfortunately, the database isn't on our machine, so we must connect to another and run the program again. It's a little clumsier: Although we can access the database, we can't access `record.json` now. 

```
$ scp record.json:user@remote.host . # copy the file over, before running it
$ ssh user@remote.host insert-into-database record.json
```

Or sometimes, the problem is running a command inside a sandbox:

```
$ container-exec --flag-i-forget-every-time run insert-into-database ... # uh wait what do I do here
```

This is the problem that TextFree86 tries to solve: letting you run a command line tool, from anywhere, as if it were a local command line. What we'd like is some command that runs the remote code, but passes in files from our current machine:

```
local.host$ remote-insert-into-database record.json  # run a remote command with a local file
```

Admittedly, now we have two problems. We must maintain `remote-insert-into-database`, and when we add a new feature to `insert-into-database`, we have to update the `remote-` client too.

TextFree86 solves this problem too: You don't have to write `remote-insert-database`. You just need to tell `textfree86` how to run the command, and the rest is handled for you:

```
local.host$ alias remote-insert-into-database='textfree86 "ssh remote host insert-into-database --pipe"'
local.host$ remote-insert-into-database record.json    # use a local file, but running a remote command
```

How it works is very similar to how a human uses a command line program: it runs `--help` first, asking the program at the remote end to describe the options it takes, uses this to parse the command line, streams the files listed to the remote end, and waits for the output.

... and the argument description is also enough to provide tab completion!

```
local.host$ complete -o nospace -C remote-insert-into-database remote-insert-into-database
local.host$ remote-insert-into-database --over<TAB>
--overwrite
```

In the above example:

- the alias is resolved to `textfree86` and run
- which in turn runs `ssh remote.host`
- which starts `insert-into-database --pipe`, on the remote machine
- `textfree86` asks it for the parsing description, and uses it to work out the possible completions

The `textfree86` client doesn't know much about the command at the other end of the pipe, just that it should answer the three basic commands: return the help and option parsing data, spawn a command with the parsed arguments, and poll it to get output. 

Really, 'Network transparent' is just a fancy way of saying 'client-server': the `textfree86` program is a generic front-end client, and the server is the command line program on the remote machine, speaking the same protocol. (For the curious, it's a type-length-value encoding, for the most part)



## The `textfree86` Python Library

Please note: Although TextFree86 implementation requires Python 3.6, the underlying protocol does not.

### An Example Program

A textfree86 program consists of `cli.Commands()`, chained together, used to decorate functions to dispatch:

```
cmd = cli.Command('florb','florb the morps')
@cmd.run("one [two] [three...]")
def cmd_run(one, two, three):
    print([one, two, three])
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

### Stdout/Stderr

Output from stdout/stderr, or from calls to `print()` are forwarded to the client. The client prints it to stderr locally.

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

