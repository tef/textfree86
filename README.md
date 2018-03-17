# TextFree86: Finally, a network transparent option parser!

This readme is not ready for an audience yet. I'd appreciate if you didn't link to it, thank you.

TextFree86 is a CLI toolkit that lets people run a command on one machine, but have inputs and outputs on another.

## What?

If you have a command line program, you can expect some things to work: passing in a file name, and if you're lucky, tab completion:

```
$ ./logdetails --uptime log.1
Wrote uptime to log

$ cat log.1
 5:59  up 2 days, 13:31, 12 users, load averages: 0.83 0.93 1.05

$ complete -o nospace -C ./logdetails ./logdetails

$ ./logdetails --u<TAB>     # Using Tab Completion
--uname   --uptime  
```

If you have a command line program, and you run it via `ssh`, or `docker run`, some things just don't work the same.

```
$ ssh machine ./logdetails filename   # filename is local to that machine

$ ssh machine ./logdetails  --<TAB>   # tab completion is for ssh, not grep
```

If you use `textfree86`, well, some things **do** work the same:

```
$ ./textfree86.py ssh hostname /path/to/logdetails --pipe -- output.log --uname
Wrote uname to log

$ cat output.log    # But on the local machine!
Darwin

$ alias rlogdetails='./textfree86.py ssh hostname /path/to/logdetails --pipe --'
$ rlogdetails --help
usage: logdetails [--uptime] [--uname] <output>

$ complete -o nospace -C rlogdetails rlogdetails
$ rlogdetails --u<TAB>    # Using Tab Completion
--uname   --uptime        # Yes, this calls ssh underneath!
```

To complete the example, here's the code for `logdetails`:

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

## Why Would Anyone Do This?

Let's say you've written a deployment script, `deploy.py`. You want other people to use it, but you're having trouble getting everyone to use the same copy. 

You could replace the deploy script with an admin UI, but that might require a little more usability. You could write a service, use a RPC library, and then write a remote CLI to connect to it. You could all ssh into the same machine, but uploading/downloading configuration files is clumsy.

TextFree86 presents another option: Run the program on one machine, but connect to it from another, without having to write a new remote CLI each time.

## Why Would You Do This?

I've written a lot of Client-Server code, and as one friend stated: "Why do we have protocols anyway? You have to write a new client for each service!"

Although there are many reusable libraries, there are very few reusable tools. TextFree86 tries to demonstrate the possibilities for a reusable, somewhat generic remote CLI tool.

It currently works over a pipe, but could as easily run over TCP or HTTP too. 

```
# Running this on one machine
$ ./command --serve --port=1729


# ... and this on another
$ ./textfree86 --url http://host/command -- <args>
```

(but that isn't implemented yet, be patient)

## How do I use the Library?

### An Example Program

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

### Bash Completion

Currently: subcommand names, `--option`s

```
complete -o nospace -c <command> <command>
```

### Pipe Mode 

You can skip the ssh part:

```
$ ./textfree86.py ./script.py --pipe -- <args to script>
```

The format is `<script to run, ending with --pipe>`, `--`, `<args to script>`.

### Stretch Goals: Caching

Keeping a copy of the command description around to speed up tab completion.

### Stretch Goals: Server, Proxy

Instead of using a pipe, HTTP is an option. Using plain old GETs to find descriptions of commands, and either through long polling, or websocket to run one.

It should be possible to proxy a command, as well as proxy to commands on different machines.

### Stretch Goals: API 

I guess this means documenting my code. Oh well.

