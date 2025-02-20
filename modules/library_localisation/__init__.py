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
        wizard.MoveExemplaryInStorehouseSelect,
        wizard.TakeOutExemplarySelect,
        wizard.CreateExemplariesParameters,
        wizard.MoveExemplaryOutQarantineSelect,
        wizard.MoveExemplaryInQarantineSelect,
        module='library_localisation', type_='model')

    Pool.register(
        wizard.MoveExemplaryOnShelf,
        wizard.MoveExemplaryInStorehouse,
        wizard.TakeOutExemplary,
        wizard.CreateExemplaries,
        wizard.MoveExemplaryInQarantine,
        wizard.MoveExemplaryOutQarantine,
        wizard.Return,
        module='library_localisation', type_='wizard')
