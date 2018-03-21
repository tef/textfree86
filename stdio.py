#!/usr/bin/env python3
from textfree86 import cli
import sys, time

cmd = cli.Command('stdio', 'cli example programs')

cat = cmd.subcommand('cat', 'print files')

@cat.run("files:infile...")
def cat_run(files):
    if files:
        for file in files:
            sys.stdout.buffer.write(file.read())
    else:
        line = sys.stdin.buffer.readline()
        while line:
            sys.stdout.buffer.write(line)
            line = sys.stdin.buffer.readline()

cmd.main(__name__)

