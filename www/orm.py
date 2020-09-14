import asyncio, logging
import aiomysql

def log(sql, args=()):
    logging.info('SQL: {}'.format(sql))


async def create_pool(loop, **kw):
    # creating connection pools
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
            host=kw.get('host', 'localhost'),
            port=kw.get('port', 3306),
            user=kw['user'],
            password=kw['password'],
            db=kw['db'],
            charset=kw.get('charset', 'utf8'),
            autocommit=kw.get('autocommit', True),
            maxsize=kw.get('maxsize', 10),
            minsize=kw.get('minsize', 1),
            loop=loop
    )

async def select(sql, args, size=None):
    # SQL: SELECT
    log(sql, args)
    global __pool
    async with __pool.acquire() as conn: # __pool.get() in Liao's code
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

async def execute(sql, args, autocommit=True):
    # SQL: INSERT, UPDATE, DELETE
    log(sql)
    async with __pool.acquire() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.release('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected

def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)


# -------------------------------Object Relation Model------------------------------

class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super(StringField, self).__init__(name, ddl, primary_key, default)


class BooleanField(Field):

    pass


class IntegerField(Field):

    pass


class FloatField(Field):

    pass


class TextField(Field):

    pass


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()
        fields = []
        primaryKey = None

        pass # ...
       
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))

        attrs['__mappings__'] = mappings 
        attrs['__table__'] = tableName

        
        pass # ...

        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)

        
        pass # ...

        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        pass

    def __setattr__(self, key, value):
        pass

    def getValue(self, key):
        pass

    def getValueOrDefault(self, key):
        pass
        




# ----------------------------------- For testing ----------------------------------
if __name__ == '__main__':
    
    loop = asyncio.get_event_loop()

    # async def test_example():
    #     # use await wherever you need to talk to database to keep asyncio working.
    #     conn = await aiomysql.connect(host='127.0.0.1', port=3306,
    #                                         user='root', password='password', db='mysql',
    #                                         loop=loop)
        
    #     cur = await conn.cursor()
    #     await cur.execute("SELECT Host, User FROM user")
    #     print(cur.description)
    #     r = await cur.fetchall()
    #     print(r)
    #     await cur.close()
    #     conn.close()

    # loop.run_until_complete(test_example())

    async def go():
        pool = await aiomysql.create_pool(host='127.0.0.1', port=3306,
                                        user='root', password='password', db='mysql',
                                        loop=loop, autocommit=False)

        async with pool.acquire() as conn:
            cur = await conn.cursor()
            await cur.execute("SELECT 10")
            (r,) = await cur.fetchone()
            assert r == 10

        pool.close()
        await pool.wait_closed()

    loop.run_until_complete(go())




