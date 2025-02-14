from trytond.pool import Pool

from . import library
from . import wizard


def register():
    Pool.register(
        module='library_localisation', type_='model')

    Pool.register(
        module='library_localisation', type_='wizard')
