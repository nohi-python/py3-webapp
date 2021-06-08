import asyncio
from asyncio import get_event_loop
from unittest import TestCase

import orm
from models import User, Blog, Comment


async def test(loop):
    print('=====1.1=======')
    await orm.create_pool(loop, user='root', password='root1234', db='py_test')
    print('=====2.1=======')
    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')
    print('=====3.1=======')
    await u.save()


async def query_user(loop):
    await orm.create_pool(loop, user='root', password='root1234', db='py_test')
    use = await User.findAll()
    for x in use:
        print(x)


# for x in test():
#     pass


class TestWww(TestCase):
    def test_db(self):
        loop = asyncio.get_event_loop()
        get_event_loop().run_until_complete(test(loop))

    def test_queryUser(self):
        loop = asyncio.get_event_loop()
        get_event_loop().run_until_complete(query_user(loop))
