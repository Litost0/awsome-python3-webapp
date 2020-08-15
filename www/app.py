import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web



HOST = '127.0.0.1'
PORT = 9000

routes = web.RouteTableDef()

# Handling request to app by routers in a decorator way
# Router: used for dispatching URLs to handler HTTP method + path
@routes.get('/')
async def handler(request):
    # handler: a coroutine
    # take Request instance as its only param
    # return a Response instance
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


def init():
    app = web.Application()
    app.add_routes(routes)
    logging.info('Server started at http://{}:{}'.format(HOST, PORT))
    web.run_app(app, host=HOST, port=PORT)

init()

# Another way of handling request

# async def handler(request):
#     ...

# def init():
#     app = web.Application()
#     app.add_routes([web.get('/', handler)])
#     web.run_app(app, host=HOST, port=PORT)


# The depreciated method:

# def index(request):
#     # 处理url
#     return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')

# async def init(loop):
#     app = web.Application(loop=loop)
#     app.router.add_route('GET', '/', index)
#     srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
#     logging.info('server started at http://127.0.0.1:9000...')
#     return srv


# loop = asyncio.get_event_loop()
# loop.run_until_complete(init(loop))
# loop.run_forever()






