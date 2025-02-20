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
        library.Book,
        library.Quarantine,
        wizard.MoveExemplaryOnShelfSelection,
        wizard.StoreExemplarySelect,
        wizard.TakeOutExemplarySelect,
        wizard.CreateExemplariesParameters,
        wizard.QuarantineUnleashExemplarySelect,
        wizard.QuarantineLockDownExemplarySelect,
        module='library_localisation', type_='model')

    Pool.register(
        wizard.MoveExemplaryOnShelf,
        wizard.StoreExemplary,
        wizard.TakeOutExemplary,
        wizard.CreateExemplaries,
        wizard.QuarantineLockDownExemplary,
        wizard.QuarantineUnleashExemplary,
        wizard.Return,
        module='library_localisation', type_='wizard')
