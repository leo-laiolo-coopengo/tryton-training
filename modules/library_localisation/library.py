import datetime
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import If, Eval, Date


__all__ = [
    'Shelf',
    'Room',
    'Floor',
    'Storehouse',
    'Exemplary',
    ]


class Shelf(ModelSQL, ModelView):
    'Shelf'
    __name__ = 'library.localisation.shelf'
    _rec_name = 'section'

    section = fields.Char('Section', required=True)
    exemplaries = fields.One2Many('library.book.exemplary', 'shelf', 'Exemplaries')
    room = fields.Many2One('library.localisation.room', 'Room', required=True, ondelete='CASCADE')

    def get_rec_name(self, name):
        return '%s : %s (%s)' % (self.section, self.room.name, self.room.floor.rec_name)


class Room(ModelSQL, ModelView):
    'Room'
    __name__ = 'library.localisation.room'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    shelves = fields.One2Many('library.localisation.shelf', 'room', 'Shelves')
    floor = fields.Many2One('library.localisation.floor', 'Floor', required=True, ondelete='CASCADE')

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
            If(~Eval('exit_date'), [],
                [('exit_date', '<=', Date()),
                    ('exit_date', '>=', Eval('entrance_date'))])],
        depends=['entrance_date'])
    exemplary = fields.Many2One('library.book.exemplary', 'Exemplary', required=True, ondelete='CASCADE')

    @classmethod
    def default_entrance_date(cls):
        return datetime.date.today()

class Exemplary(metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    shelf = fields.Many2One('library.localisation.shelf', 'Shelf', ondelete='RESTRICT')
