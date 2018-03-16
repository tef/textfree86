# TextFree86: Finally, a network transparent getopt(3)

This readme is semi-fictional. It is not ready for an audience yet. I'd appreciate if you didn't link to it, thank you.

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

(soon!)

The `textfree86` program doesn't need any configuration beyond the URL and any credentials to access the remote CLI.

The `florb` command doesn't need much configuration, either:

```
from textfree86 import cli

cmd = cli.Command('florb','florb the morps')
@cmd.run()
def cmd_run():
    return 'Hello, World'
```

and `florb help` and `florb --help` work too. 

## But... Why?

One friend: "why have protocols when you have to write a new client for each service"

Another: "Oh! This is like docker run, without docker!"

You could implement this as a simpler script: Dump the raw arguments into HTTP, and print the output. This works up until you want tab completion, or passing in files to the command.

Both of these things require the client to know a little bit more about parsing the command line, or be given instructions by the server on how to do it. When the client knows in advance, it has to be updated with every change to the service.

Instead, `textfree86` only needs one URL (and maybe credentials) to run a command.

## Again, Why?

Let's say you've written a deployment script, `deploy.py`. 

- You want other people to use it,
- ... but you're having trouble getting everyone to use the same copy

Now? You run your deploy script as a service, and everyone uses the same CLI, but remotely.

## An Example Program

A textfree86 program consists of `cli.Commands()`, chained together, used to decorate functions to dispatch:

```
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

## Parsing Command Line arguments.

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


### Files, Paths, Directories (Sort of) 

Files can also be sent as command line arguments, or written to as output from the program.

```
@subcommand.run("data:infile output:outfile")
def subcommand_run(data, output):
    for line in data.readlines():
        output.write(line)
```

### Environment Variables, Local Configuration (Not Yet)

Instead of positional options or option flags, program configuration can be stored in environment variables, or local files. These can be overridden by option flags too.

A command `cmd subcommand` with environment setting `env`, can read from `CMD_SUBCOMMAND_ENV` or `--env=<...>` on the command line.

An option should be able to default to using a known file, too.

### Stdin/Stdout (Not Yet)

The `textfree86` program wraps up any input, streams it to the remote server, and streams back any output.

### Bash Completion (Sort-of)

```
complete -o nospace,default -c <command> <command>
```

Currently only option flag names are completed

## Network Mode (Not Yet)

With the command/subcommand classes, the CLI framework looks like a Router inside a web framework. Bash completion means being able to expose options without running the command.

The `textfree86` client asks for the completition information, parses the command line arguments, sends them across the network, and prints the responses. 

```
$ textfree86 http://address/ -- help
```

### Server

### Proxy

### Offline Client

### API (Not Yet)

This project evolved from writing a CLI debugger for networked services. As I started writing option parsers inside the client, I realised I'd made a huge mistake. 

Even so, one day:

```
import textfree86

cmd = cli.RemoteCommand(url)

print(cmd.subcommand(name=1, name=2))
```

If you're after something more like this, you might be curious about the RPC systems that this CLI kit evolved from.

