from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta, Pool


__all__ = [
    'Shelf',
    'Room',
    'Exemplary',
    ]

class Shelf(ModelSQL, ModelView):
    'Shelf'
    __name__ = 'library.localisation.shelf'

    section = fields.Char('Section', required=True)
    exemplaries = fields.One2Many('library.book.exemplary', 'shelf', 'Exemplaries')
    room = fields.Many2One('library.localisation.room', 'Room', required=True)

class Room(ModelSQL, ModelView):
    'Room'
    __name__ = 'library.localisation.room'

    name = fields.Char('Name', required=True)
    shelfs = fields.One2Many('library.localisation.shelf', 'room', 'Shelfs')

class Exemplary(metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    shelf = fields.Many2One('library.localisation.shelf', 'Shelf')
