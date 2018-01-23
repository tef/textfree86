from catbus import client, server

import collections
from datetime import datetime, timezone

from peewee import *

db = SqliteDatabase('people.db')

class Person(Model):
    name = CharField()

    class Meta:
        database = db

    class Handler(server.Model.PeeweeHandler):
        pass

db.connect()
db.create_tables([Person], safe=True)

def make_server():
    n = server.Namespace()

    n.register(Person)

    return server.Server(n.app(), port=8888)

def test():
    server_thread = make_server()
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        s= client.get(server_thread.url)

        person = client.create(s.Person,dict(name="butt"))
            # client.call(s.Job.create(...))

        print(person, person.url, person.methods, person.attributes)

        for j in client.list(s.Person):
            print(j)

        print(client.delete(person))
    finally:
        server_thread.stop()



if __name__ == '__main__':
    test()
