from trytond.pool import Pool

from . import library
from . import wizard


def register():
    Pool.register(
        library.Shelf,
        library.Exemplary,
        library.Room,
        library.Floor,
        library.Storehouse,
        wizard.MoveExemplaryOnShelfSelection,
        wizard.StoreExemplarySelect,
        wizard.TakeOutExemplarySelect,
        module='library_localisation', type_='model')

    Pool.register(
        wizard.MoveExemplaryOnShelf,
        wizard.StoreExemplary,
        wizard.TakeOutExemplary,
        module='library_localisation', type_='wizard')
