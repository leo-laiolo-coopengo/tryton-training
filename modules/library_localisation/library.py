import datetime

from sql import Null
from sql.operators import NotIn

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import If, Eval, Date
from trytond.transaction import Transaction


__all__ = [
    'Shelf',
    'Room',
    'Floor',
    'Storehouse',
    'Exemplary',
    'Book',
    'Quarantine',
    ]


class Shelf(ModelSQL, ModelView):
    'Shelf'
    __name__ = 'library.localisation.shelf'
    _rec_name = 'section'

    section = fields.Char('Section', required=True)
    exemplaries = fields.One2Many('library.book.exemplary', 'shelf',
        'Exemplaries')
    room = fields.Many2One('library.localisation.room', 'Room', required=True,
        ondelete='CASCADE')

    def get_rec_name(self, name):
        return '%s : %s (%s)' % (self.section, self.room.name,
            self.room.floor.rec_name)


class Room(ModelSQL, ModelView):
    'Room'
    __name__ = 'library.localisation.room'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    shelves = fields.One2Many('library.localisation.shelf', 'room', 'Shelves')
    floor = fields.Many2One('library.localisation.floor', 'Floor',
        required=True, ondelete='CASCADE')

    def get_rec_name(self, name):
        return '%s (%s)' % (self.name, self.floor.rec_name)

class Floor(ModelSQL, ModelView):
    'Floor'
    __name__ = 'library.localisation.floor'
    _rec_name = 'number'

    number = fields.Integer('Number', required=True)
    rooms = fields.One2Many('library.localisation.room', 'floor', 'Rooms')

    def get_rec_name(self, name):
        if (self.number == 0):
            return 'RDC'
        else:
            return str(self.number)


class Storehouse(ModelSQL, ModelView):
    'Storehouse'
    __name__ = 'library.storehouse'

    entrance_date = fields.Date('Entrance Date', required=True, domain=[
            ('entrance_date', '<=', Date())])
    exit_date = fields.Date('Exit Date', domain=[
            If(~Eval('exit_date'), [], [('exit_date', '<=', Date()),
                    ('exit_date', '>=', Eval('entrance_date'))])],
        depends=['entrance_date'])
    exemplary = fields.Many2One('library.book.exemplary', 'Exemplary',
        required=True, ondelete='CASCADE')

    @classmethod
    def default_entrance_date(cls):
        return datetime.date.today()

    def get_rec_name(self, name):
        if self.exit_date:
            return '%s (%s-%s) S' % \
                (self.exemplary.rec_name, self.entrance_date, self.exit_date)
        else:
            return '%s (%s) S' % (self.exemplary.rec_name, self.entrance_date)


class Quarantine(ModelSQL, ModelView):
    'Quarantine'
    __name__ = 'library.quarantine'

    entrance_date = fields.Date('Entrance Date', required=True, domain=[
            ('entrance_date', '<=', Date())])
    exit_date = fields.Date('Exit Date', domain=[
            If(~Eval('exit_date'), [],
                [('exit_date', '<=', Date()),
                    ('exit_date', '>=', Eval('entrance_date'))])],
        depends=['entrance_date'])
    expected_exit_date = fields.Function(
        fields.Date('Expected exit date', help='The date at which the '
            'exemplary is supposed to be cleaned'),
        'getter_expected_exit_date', searcher='search_expected_exit_date')
    exemplary = fields.Many2One('library.book.exemplary', 'Exemplary',
        required=True, ondelete='CASCADE')

    @classmethod
    def default_entrance_date(cls):
        return datetime.date.today()

    def getter_expected_exit_date(self, name):
        return self.entrance_date + datetime.timedelta(days=7)

    def get_rec_name(self, name):
        if self.exit_date:
            return '%s (%s-%s) Q' % \
                (self.exemplary.rec_name, self.entrance_date, self.exit_date)
        else:
            return '%s (%s) Q' % (self.exemplary.rec_name, self.entrance_date)

    @classmethod
    def search_expected_exit_date(cls, name, clause):
        _, operator, value = clause
        if isinstance(value, datetime.date):
            value = value + datetime.timedelta(days=-7)
        if isinstance(value, (list, tuple)):
            value = [(x + datetime.timedelta(days=-7) if x else x)
                for x in value]
        return [('entrance_date', operator, value)]


class Exemplary(metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    shelf = fields.Many2One('library.localisation.shelf', 'Shelf',
        ondelete='RESTRICT')
    stocks = fields.One2Many('library.storehouse', 'exemplary', 'Storehouses')
    quarantines = fields.One2Many('library.quarantine', 'exemplary',
        'Quarantines')
    is_in_storehouse = fields.Function(fields.Boolean('Is in Storehouse'),
        'getter_is_in_stock', searcher='search_is_in_stock')
    is_in_quarantine = fields.Function(fields.Boolean('Is in Quarantine'),
        'getter_is_in_stock', searcher='search_is_in_stock')
    is_borrowed = fields.Function(fields.Boolean('Is Borrowed'),
        'getter_is_borrowed', searcher='search_is_borrowed')

    @classmethod
    def create(cls, values):
        records = super().create(values)
        cls.move_in_storehouse(records)
        return records

    @classmethod
    def write(cls, records, values, *args):
        super().write(records, values, *args)
        actions = iter((records, values) + args)
        all_records = []
        for r, _ in zip(actions, actions):
            if r:
                all_records += r
        cls.move_in_storehouse(all_records)

    @classmethod
    def getter_is_borrowed(cls, exemplaries, name=None):
        checkout = Pool().get('library.user.checkout').__table__()
        cursor = Transaction().connection.cursor()
        result_checkout = {x.id: False for x in exemplaries}
        cursor.execute(*checkout.select(checkout.exemplary,
                where=(checkout.return_date == Null)
                & checkout.exemplary.in_([x.id for x in exemplaries])))
        for exemplary_id, in cursor.fetchall():
            result_checkout[exemplary_id] = True
        return result_checkout

    @classmethod
    def getter_is_in_stock(cls, exemplaries, name):
        if name == 'is_in_storehouse':
            stock = Pool().get('library.storehouse').__table__()
        else:
            stock = Pool().get('library.quarantine').__table__()
        cursor = Transaction().connection.cursor()
        result = {x.id: False for x in exemplaries}
        cursor.execute(*stock.select(stock.exemplary,
            where=(stock.exit_date == Null) &
                stock.exemplary.in_([x.id for x in exemplaries])))
        for exemplary_id, in cursor.fetchall():
            result[exemplary_id] = True
        return result

    @classmethod
    def getter_is_available(cls, exemplaries, name):
        result_checkout = cls.getter_is_borrowed(exemplaries)
        result_storehouse = cls.getter_is_in_stock(exemplaries,
            'is_in_storehouse')
        result_quarantine = cls.getter_is_in_stock(exemplaries,
            'is_in_quarantine')

        result = {}
        for e in exemplaries:
            result[e.id] = not(result_checkout[e.id]) and \
                not(result_storehouse[e.id]) and \
                not(result_quarantine[e.id])
        return result

    @classmethod
    def search_is_borrowed(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        checkout = Pool().get('library.user.checkout').__table__()
        exemplary = cls.__table__()
        query = exemplary.join(checkout, 'LEFT OUTER',
            condition=(exemplary.id == checkout.exemplary)
            ).select(exemplary.id,
            where=(checkout.return_date == Null) & (checkout.id != Null))
        return [('id', 'in' if value else 'not in', query)]

    @classmethod
    def search_is_in_stock(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        if name == 'is_in_storehouse':
            stock = pool.get('library.storehouse').__table__()
        else:
            stock = pool.get('library.quarantine').__table__()
        exemplary = cls.__table__()
        query = exemplary.join(stock, 'LEFT OUTER',
            condition=(exemplary.id == stock.exemplary)
            ).select(exemplary.id,
            where=(stock.exit_date == Null) & (stock.id != Null))
        return [('id', 'in' if value else 'not in', query)]

    @classmethod
    def search_is_in_quarantine(cls, name, clause):
        return cls.search_is_in_stock('is_in_quarantine', clause)

    @classmethod
    def search_is_available(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        storehouse = pool.get('library.storehouse').__table__()
        quarantine = pool.get('library.quarantine').__table__()
        exemplary = cls.__table__()
        query = exemplary.join(checkout, 'LEFT OUTER',
            condition=(checkout.exemplary == exemplary.id)
            ).join(storehouse, 'LEFT OUTER',
            condition=(storehouse.exemplary == exemplary.id)
            ).join(quarantine, 'LEFT OUTER',
            condition=(quarantine.exemplary == exemplary.id)
            ).select(exemplary.id,
            where=((checkout.return_date == Null) & (checkout.id != Null)) | \
                ((storehouse.exit_date == Null) & (storehouse.id != Null)) | \
                ((quarantine.exit_date == Null) & (quarantine.id != Null)))
        return [('id', 'in' if not value else 'not in', query)]

    @classmethod
    def move_in_storehouse(cls, records=None):
        Storehouse = Pool().get('library.storehouse')
        stocks = []
        for e in records:
            if not(e.shelf or e.is_in_storehouse):
                stocks.append(Storehouse(exemplary=e,
                    entrance_date=datetime.date.today()))
        if len(stocks) > 0:
            Storehouse.save(stocks)
            # raise UserWarning('The following exemplaries were placed in the '
            # 'storehouse because they had no attributed shelf: \n%s' % stocks)
        return


class Book(metaclass=PoolMeta):
    __name__ = 'library.book'

    @classmethod
    def getter_is_available(cls, books, name):
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = pool.get('library.book.exemplary').__table__()
        storehouse = pool.get('library.storehouse').__table__()
        quarantine = pool.get('library.quarantine').__table__()
        book = cls.__table__()

        sub_query = exemplary.join(checkout, 'LEFT OUTER',
            condition=(checkout.exemplary == exemplary.id)
            ).join(storehouse, 'LEFT OUTER',
            condition=(storehouse.exemplary == exemplary.id)
            ).join(quarantine, 'LEFT OUTER',
            condition=(quarantine.exemplary == exemplary.id)
            ).select(exemplary.id,
            where=((checkout.return_date == Null) & (checkout.id != Null)) | \
                ((storehouse.exit_date == Null) & (storehouse.id != Null)) | \
                ((quarantine.exit_date == Null) & (quarantine.id != Null)))

        query = book.join(exemplary,
            condition=(exemplary.book == book.id)
            ).select(book.id,
            where=(NotIn(exemplary.id, sub_query)))

        result = {x.id: False for x in books}
        cursor = Transaction().connection.cursor()
        cursor.execute(*query)
        for book_id, in cursor.fetchall():
            result[book_id] = True
        return result

    @classmethod
    def search_is_available(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = pool.get('library.book.exemplary').__table__()
        storehouse = pool.get('library.storehouse').__table__()
        quarantine = pool.get('library.quarantine').__table__()
        book = cls.__table__()

        sub_query = exemplary.join(checkout, 'LEFT OUTER',
            condition=(checkout.exemplary == exemplary.id)
            ).join(storehouse, 'LEFT OUTER',
            condition=(storehouse.exemplary == exemplary.id)
            ).join(quarantine, 'LEFT OUTER',
            condition=(quarantine.exemplary == exemplary.id)
            ).select(exemplary.id,
            where=((checkout.return_date == Null) & (checkout.id != Null)) | \
                ((storehouse.exit_date == Null) & (storehouse.id != Null)) | \
                ((quarantine.exit_date == Null) & (quarantine.id != Null)))

        query = book.join(exemplary,
            condition=(exemplary.book == book.id)
            ).select(book.id,
            where=(NotIn(exemplary.id, sub_query)))
        return [('id', 'in' if value else 'not in', query)]
