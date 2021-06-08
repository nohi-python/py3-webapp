#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import re
import time

from aiohttp import web

from apis import APIValueError, APIError, Page
from coroweb import get, post
from models import User, Blog, next_id

__author__ = 'Michael Liao'

from config import configs

' url handlers '

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


@get('/')
async def index(request):
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }


@get('/blog')
async def blog(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time() - 7200),
        Blog(id='4', name='Tale Swift', summary=summary, created_at=time.time() - 7200),
        Blog(id='5', name='Learn GO', summary=summary, created_at=time.time() - 47200),
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }


@get('/register')
async def register(request):
    return {
        '__template__': 'register.html'
    }


@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }


@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy='created_at desc')
    for u in users:
        u.passwd = '******'
    return dict(users=users)


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


@post('/api/users')
async def api_register_user(*, email, name, passwd):
    logging.debug('api_register_user email[%s] name[%s]' % (email, name))
    if not name or not name.strip():
        raise APIValueError('name')
    elif not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    elif not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    # 根据邮箱查询
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image='https://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    # 保存
    await user.save()

    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    elif not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        logging.debug('email[%s] not exist' % email)
        raise APIValueError('email', 'email not exist.')
    user = users[0]

    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    logging.debug('user.passwd:%s' % user.passwd)
    logging.debug('sha1.hexdigest():%s' % sha1.hexdigest())
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/manage/blog/create')
def to_create_blog():
    return {
        'action': '/api/blog',
        '__template__': 'manage_blog_edit.html'
    }


@get('/api/blog/{id}')
async def apiblog(request, *, id):
    user = request.__user__
    logging.debug('apiblog, id=%s' % id)
    blog = await Blog.findAll('id=?', [id])
    return blog
    # r = web.Response()
    # r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    # user.passwd = '******'
    # r.content_type = 'application/json'
    # r.body = json.dumps(blog, ensure_ascii=False).encode('utf-8')
    # return r


@post('/api/blog')
async def api_create_blog(request, *, name, summary, content):
    print('request.__user__.id %s' % request.__user__.id)
    if not name or not name.strip():
        raise APIValueError(name, '标题不能为空')
    if not summary or not summary.strip():
        raise APIValueError(summary, 'summary不能为空')
    if not content or not content.strip():
        raise APIValueError(content, 'content不能为空')

    # id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    # user_id = StringField(ddl='varchar(50)')
    # user_name = StringField(ddl='varchar(50)')
    # user_image = StringField(ddl='varchar(500)')
    # name = StringField(ddl='varchar(50)')
    # summary = StringField(ddl='varchar(200)')
    # content = TextField()
    # created_at = FloatField(default=time.time)
    cookie_str = request.cookies.get(COOKIE_NAME)
    if cookie_str:
        user = await cookie2user(cookie_str)
        if user:
            logging.info('set current user: %s' % user.email)
            request.__user__ = user
    id = next_id()
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image
                , name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog
    # return {
    #         '__template__': 'manage_blogs.html',
    #         'page_index': get_page_index('1')
    #     }


@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }


@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)