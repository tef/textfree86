from catbus import client, server

import collections
from datetime import datetime, timezone

from peewee import *

db = SqliteDatabase('people.db')

class Models:
    class Person(Model):
        name = CharField()

        @server.rpc()
        def hello(self):
            return "Hello, {}!".format(self.name)

        class Meta:
            database = db


db.connect()
db.create_tables([Models.Person], safe=True)



def make_server():
    n = server.Namespace()

    n.register(Models.Person, server.Model.PeeweeHandler)


    return server.Server(n.app(), port=8888)

def test():
    server_thread = make_server()
    server_thread.start()

    print("Running on ",server_thread.url)

    try:
        s= client.get(server_thread.url)

        print('Creating...')
        person = client.create(s.Person,dict(name="butt"))
            # client.call(s.Job.create(...))

        print('Created',person)

        print('Listing...')

        for j in client.list(s.Person):
            print(" Person", j.name, j.methods)
            print(client.call(j.hello()))

        print('Deleting...')
        client.delete(person)
        print('Deleted')
    finally:
        server_thread.stop()



if __name__ == '__main__':
    test()
