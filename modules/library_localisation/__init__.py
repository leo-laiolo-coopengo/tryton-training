from trytond.pool import Pool

from . import library
from . import wizard


def register():
    Pool.register(
        library.Shelf,
        library.Exemplary,
        library.Room,
        library.Floor,
        wizard.MoveExemplaryOnShelfSelection,
        module='library_localisation', type_='model')

    Pool.register(
        wizard.MoveExemplaryOnShelf,
        module='library_localisation', type_='wizard')
