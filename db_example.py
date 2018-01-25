from catbus import client, server

import collections
import uuid
from datetime import datetime, timezone

from peewee import *

db = SqliteDatabase('people.db')

namespace = server.Namespace()

@namespace.add()
class Person(Model):
    class Meta: database = db

    uuid = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(index=True)

    Handler = server.Model.PeeweeHandler

    @server.rpc()
    def hello(self):
        return "Hello, {}!".format(self.name)

def test():
    db.connect()
    db.create_tables([Person], safe=True)

    server_thread = server.Server(namespace.app(), port=8888)
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        test_client(server_thread.url)
    finally:
        server_thread.stop()


def test_client(url):
    s= client.get(url)

    print('Creating...')
    person = client.create(s.Person,dict(name="butt"))

    print('Created',person)

    print('Listing...')

    total = 0
    for p in client.list(s.Person, batch=3):
        print(" Person", p)
        print(" Calling p.hello()", client.call(p.hello()))
        total += 1
        if p.uuid != person.uuid:
            print(client.delete(p))

    print('Total', total)
    print('Deleting...')
    client.delete(person)
    print('Deleted')
if __name__ == '__main__':
    test()
