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
        async with conn.cursor(aiomysql.DictCursor) as cur: # returns results as dictionary
            # SQL占位符：？，MySQL占位符： %s
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
                await cur.execute(sql.replace('?', '%s'), args)
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
        self.primary_key = primary_key # boolean
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super(StringField, self).__init__(name, ddl, primary_key, default)


class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()
        fields = []
        primaryKey = None

        
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info(' found mapping: %s ===> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    if primary_key:
                        raise StandardError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else: 
                    fields.append(k)
        if not primaryKey:
            raise StandardError('Primary key not found.')

        if k in mappings.keys():
            attrs.pop(k)

        escaped_fields = [lambda s: '`{}`'.format(s) for s in fields]
        

        attrs['__mappings__'] = mappings 
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        attrs['__fields__'] = fields # 主键以外的属性名
        attrs['__select__'] = 'SELECT `%s`, %s FROM `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'INSERT INTO `%s` (%s, `%s`) VALUES (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))

        
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

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        # find objects by where clause.
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]


    pass

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failded to insert record: affected rows: %s' % rows)




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




