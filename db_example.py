from catbus import client, server

import sys
import collections
import uuid
from datetime import datetime, timezone

from peewee import *

db = SqliteDatabase('people.db')

registry = server.Registry()

@registry.add()
class Person(Model):
    class Meta: database = db

    uuid = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(index=True)
    job = CharField(index=True)

    Handler = server.Model.PeeweeHandler

    @server.rpc()
    def hello(self):
        return "Hello, {}!".format(self.name)

def test():
    db.connect()
    db.create_tables([Person], safe=True)

    server_thread = server.Server(registry.app(), port=8888)
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        test_client(server_thread.url)
    finally:
        server_thread.stop()


def run():
    db.connect()
    db.create_tables([Person], safe=True)

    server_thread = server.Server(registry.app(), port=8888)
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        while True: pass
    finally:
        server_thread.stop()

def test_client(url):
    s= client.Get(url)

    print('Creating...')
    people = []
    for name in ('Dave', 'Eve', 'Sam'):
        person = client.Create(s.Person, value=dict(name=name, job="bar"))
        people.append(person)

    for name in ('Mar', 'Jet', 'Pol'):
        person = client.Create(s.Person, value=dict(name=name, job="foo"))

    print()

    print('Listing All...')

    total = 0
    for p in client.List(s.Person, batch=1):
        print(" Person", p.name)
        total += 1

    print('Total', total)
    print()

    print('Listing Subset...')

    total = 0
    for p in client.List(s.Person.where(job='foo')):
        print(" Calling p.hello()", client.Call(p.hello()))
        total += 1

    print('Total', total)
    print()

    print('Deleting...')
    client.Delete(s.Person.where(job='foo'))

    print('Listing All...')

    total = 0
    for p in client.List(s.Person, batch=3):
        print(" Person", p.name)
        total += 1

    print('Total', total)
    print()

    for person in people:
        client.Delete(person)
    print('Deleted')

    	
    print('Listing All...')

    total = 0
    for p in client.List(s.Person, batch=3):
        print(" Person", p.name)
        total += 1

    print('Total', total)
    print()

if __name__ == '__main__':
    if 'run' in sys.argv:
        run()
    else:
        test()
