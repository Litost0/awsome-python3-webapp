import functools, logging, asyncio, inspect
from aiohttp import web
from apis import APIError


def get(path):

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
The followings are some functions that will be used in the RequestHandler
'''
def get_required_kw_args(fn):
    # get KEYWORD_ONLY params with empty default value
    # like params after *args
    # return: tuple of names of required keyword args
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    # get KEYWORD_ONLY params
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True
    return False

def has_var_kw_arg(fn):
    # check if fn has VAR_KEYWORD params (like **kw)
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False

def has_request_arg(fn):
    # check if fn has an argument called 'request''
    # The request argument must be the last named argument
    found = False
    params = inspect.sigature(fn).parameters
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_KEYWORD and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_POSITIONAL):
            raise ValueError('the request argument must be the last named argument')
    return found


class RequestHandler(object):
    '''
    The aim of RequestHandler: Get params from urls, Turn request into respond.   
    The URL handling function is wrapped as an instance of RequestHandler class which is callable

    class RequestHandler(object):

        def __init__(self, app, fn):
            self._app = app
            self._fn = fn
            ...

        async def __call__(self, request):
            kw = []
            # must be a coroutine to satisfy the aiohttp API's request
            #...before call the fn, we need to check the parameters
            #...request.method could be 'GET' or 'POST'
            #...and we should have valid request.content_type
            await self._fn(**kw) 
    
    Attributes:
    _app: aiohttp.web.Application
    _fn: handler function (coroutine)
    _has_**_args and other attrs: some checkers defined above


    '''

    # 可以理解为views.py里面的View类？

    def __init__(self, app, fn):
        self._app = app
        self._func = fn # URL dispatching function
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)


    async def __call__(self, request):
        kw = None
        if self._has_var_kw_args or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupport Content-Type {}'.format(request.content_type))
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k,v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]

        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unnamed kws:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in rqeuest.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: {}'.format(k))
                kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: {}'.format(name))
        logging.info('call with args:{}'.format(str(kw)))

        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)



def add_route(app, fn):

    '''
    Register a URL handling function

    def add_route(app, fn): 
        app: aiohttp.web.Application instance
        fn: RequestHandler function      
        # ...check if fn has required attributes
        # ...check if fn is a coroutine
        return app.router.add_route(method, path, handler)

    return: Route instance
    '''

    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__path__', None)
    if method is None or path is None:
        raise ValueError('method @get or @post not found in {}'.format(str(fn)))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    return app.router.add_route(method, path, RequestHandler(app, fn))



def add_routes(app, module_name):

    '''
    Regisiter all URL handling functions that defined in a module

    def add_routes(app, module_name):
        app: aiohttp.web.Application instance
        fn: RequestHandler function
        #...parse the module path
        #...iteratively find the handler functions fn in that module
        add_route(app, fn)

    return: None
    '''

    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(),[name]), name)

    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__path__', None)
            if method and path:
                add_route(app, fn)
    


if __name__ == '__main__':

    pass
    
    # mod = __import__('orm')
    # print(dir(mod))
    # mod_2 = __import__('orm', globals(), locals())
    # print(dir(mod_2))




















