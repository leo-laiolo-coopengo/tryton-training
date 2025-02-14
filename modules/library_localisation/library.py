from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta, Pool


__all__ = [
    'Shelf',
    'Room',
    'Floor',
    'Exemplary',
    ]


class Shelf(ModelSQL, ModelView):
    'Shelf'
    __name__ = 'library.localisation.shelf'
    _rec_name = 'section'

    section = fields.Char('Section', required=True)
    exemplaries = fields.One2Many('library.book.exemplary', 'shelf', 'Exemplaries')
    room = fields.Many2One('library.localisation.room', 'Room', required=True)

    def get_rec_name(self, name):
        return '%s : %s (%s)' % (self.section, self.room.name, self.room.floor.rec_name)


class Room(ModelSQL, ModelView):
    'Room'
    __name__ = 'library.localisation.room'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    shelves = fields.One2Many('library.localisation.shelf', 'room', 'Shelves')
    floor = fields.Many2One('library.localisation.floor', 'Floor', required=True)

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


class Exemplary(metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    shelf = fields.Many2One('library.localisation.shelf', 'Shelf')
