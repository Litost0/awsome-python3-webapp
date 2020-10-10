import functools, logging, asyncio, inspect
from aiohttp import web

'''
We want to realize a Flask-style URL dispatcher, which links the URL to the view:

An example:
@app.route('/', methods=['GET', 'POST'])
def home():
    return '<h1>Home</h1>'


Routing URL: define decorator @get and @post
@get and @post decorate the function which serves as a field of RequestHandler object.
The RequestHandler is callable, its __call__ function returns the function that can be decorated
by @get and @post
'''

def get(path):
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__path__ = path
        return wrapper
    return decorator

def post(path):

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__path__ = path
        return wrapper
    return decorator

'''
The URL handling function is wrapped as an instance of RequestHandler class which is callable:

class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._fn = fn

    async def __call__(self):
        await self._fn


The aim of RequestHandler: 

'''
class RequestHandler(object):

    def __init__(self, app, fn,):
        self._app = app
        self._fn = fn
        pass

    def __call__(self, request):

        pass


def add_route(app, fn):
    pass


if __name__ == '__main__':
    class Foo():

        def __init__(self, field):
            self._field = field
        
        def __call__(self, adder):
            return self._field + adder

    def function(a,b,c,d):
        pass

    print(inspect.signature(function).parameters)