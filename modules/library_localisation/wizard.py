import datetime
from trytond.wizard import Wizard, StateView, StateTransition, StateAction, Button
from trytond.model import ModelView, fields
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder, Date, Eval, Less
from trytond.pool import Pool, PoolMeta


__all__ = [
    'MoveExemplaryOnShelf',
    'MoveExemplaryOnShelfSelection',
    'StoreExemplary',
    'StoreExemplarySelect',
    'TakeOutExemplary',
    'TakeOutExemplarySelect',
    'CreateExemplaries',
    'CreateExemplariesParameters',
    'QuarantineLockDownExemplary',
    'QuarantineLockDownExemplarySelect',
    'QuarantineUnleashExemplary',
    'QuarantineUnleashExemplarySelect',
    'Return',
    ]

class MoveExemplaryOnShelf(Wizard):
    'Move Exemplary on Shelf'
    __name__ = 'library.localisation.move'

    start_state = 'select'
    select = StateView('library.localisation.move.select', 'library_localisation.move_exemplaries_shelf_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Move', 'move', 'tryton-go-next', default=True)])
    move = StateTransition()
    open_shelves = StateAction('library.act_exemplary')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'invalid_model': 'This action should be started from an exemplary or a shelf.',
                })

    def default_select(self,name):
        if Transaction().context.get('active_model', '') == 'library.book.exemplary':
            return {
                'exemplaries': Transaction().context.get('active_ids'),
                }
        elif Transaction().context.get('active_model', '') == 'library.localisation.shelf':
            shelves = Pool().get('library.localisation.shelf').browse(
                Transaction().context.get('active_ids'))
            return {
                'exemplaries': [e.id for s in shelves for e in s.exemplaries],
                }
        self.raise_user_error('invalid_model')

    def transition_move(self):
        Exemplary = Pool().get('library.book.exemplary')
        Exemplary.write(list(self.select.exemplaries), {
                'shelf': self.select.shelf})
        return 'open_shelves'

    def do_open_shelves(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [x.id for x in self.select.exemplaries])])
        return action, {}


class MoveExemplaryOnShelfSelection(ModelView):
    'Select Exemplary and Shelf'
    __name__ = 'library.localisation.move.select'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True)
    shelf = fields.Many2One('library.localisation.shelf', 'Shelf',
        required=True)


class StoreExemplary(Wizard):
    'Store Exemplary in Storehouse'
    __name__ = 'library.storehouse.put_in'

    start_state = 'select'
    select = StateView('library.storehouse.put_in.select',
        'library_localisation.store_exemplaries_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Store', 'store', 'tryton-go-next', default=True)])
    store = StateTransition()
    open_storehouse = StateAction('library_localisation.act_storehouse')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'invalid_model': 'This action should be started from an '
                'exemplary.',
                'exemplary_unavailable': 'The following exemplaries are '
                'unavailable: \n%(exemplaries)s',
                'invalid_date': 'The date of entrance in the storehouse can\'t'
                ' be done before an exemplary acquisition (%(date)s).'
                })

    def default_select(self,name):
        if Transaction().context.get('active_model', '') == \
            'library.book.exemplary':
            Exemplary = Pool().get('library.book.exemplary')
            exemplaries = Exemplary.browse(Transaction().context.get('active_ids'))
            exemplary_unavailable = []
            exemplaries_to_move = []
            for e in exemplaries:
                if e.is_available:
                    exemplaries_to_move.append(e.id)
                else:
                    exemplary_unavailable.append(e.rec_name)
            if len(exemplary_unavailable) > 0:
                self.raise_user_warning('exemplary_unavailable_warning' + str(
                    exemplary_unavailable), 'exemplary_unavailable',
                {'exemplaries': ', '.join(exemplary_unavailable)})
            return {
                'exemplaries': exemplaries_to_move,
                'entrance_date': datetime.date.today()
                }
        else:
            self.raise_user_error('invalid_model')

    def transition_store(self):
        minimum_entrance_date = min(
            [e.acquisition_date for e in self.select.exemplaries])
        if minimum_entrance_date > self.select.entrance_date:
            self.raise_user_error('invalid_date',
                {'date': minimum_entrance_date})
        Storehouse = Pool().get('library.storehouse')
        stocks = []
        for e in self.select.exemplaries:
            stocks.append(
                Storehouse(exemplary=e, entrance_date=self.select.entrance_date))
        Storehouse.save(stocks)
        self.select.stocks = stocks
        return 'open_storehouse'

    def do_open_storehouse(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [x.id for x in self.select.stocks])])
        return action, {}

class StoreExemplarySelect(ModelView):
    'Select Exemplary to store'
    __name__ = 'library.storehouse.put_in.select'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True, domain=[('is_available', '=', True)])
    entrance_date = fields.Date('Entrance Date', required=True, domain=[
            ('entrance_date', '<=', Date())])
    stocks = fields.Many2Many('library.storehouse', None, None, 'Stocks', readonly=True)


class TakeOutExemplary(Wizard):
    'Take Exemplary out of Storehouse'
    __name__ = 'library.storehouse.take_out'

    start_state = 'select'
    select = StateView('library.storehouse.take_out.select',
        'library_localisation.take_out_exemplaries_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Take out', 'take_out', 'tryton-go-next', default=True)])
    take_out = StateTransition()
    open_exemplaries = StateAction('library.act_exemplary')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'invalid_model': 'This action should be started from an '
                'exemplary.',
                'exemplary_out_storehouse': 'The following exemplaries are not '
                'in storehouse: \n%(exemplaries)s',
                'past_stock': 'The choosen stocks aren\'t actuals: \n'
                '%(stocks)s',
                'no_shelf': 'The following exemplaries have no attributed '
                'shelf. Please use "Move Exemplaries" to give them one.\n'
                '%(exemplaries)s',
                })

    def default_select(self,name):
        # TODO UX: can't take out a book that doesn't have any shelf -> warn + select shelf? Reuse MoveShelf?
        if Transaction().context.get('active_model', '') == \
            'library.storehouse':
            Stockhouse = Pool().get('library.storehouse')
            stocks = Stockhouse.browse(Transaction().context.get('active_ids'))
            past_stocks = []
            stocks_to_move = []
            no_shelf = []
            for s in stocks:
                if s.exit_date:
                    past_stocks.append(s.rec_name)
                elif not(s.exemplary.shelf):
                    no_shelf.append(s.exemplary.rec_name)
                else:
                    stocks_to_move.append(s.id)
            if len(past_stocks) > 0:
                self.raise_user_warning('past_stock_warning' + str(
                    past_stocks), 'past_stock',
                {'stocks': ', '.join(past_stocks)})
            elif len(no_shelf) > 0:
                self.raise_user_warning('no_shelf_warning' + str(
                    no_shelf), 'no_shelf',
                {'exemplaries': ', '.join(no_shelf)})
            return {
                'stocks': stocks_to_move,
                'exit_date': datetime.date.today()
                }
        else:
            self.raise_user_error('invalid_model')

    def transition_take_out(self):
        Storehouse = Pool().get('library.storehouse')
        Storehouse.write(list(self.select.stocks), {
                'exit_date': self.select.exit_date})
        return 'open_exemplaries'

    def do_open_exemplaries(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [x.exemplary.id for x in self.select.stocks])])
        return action, {}

class TakeOutExemplarySelect(ModelView):
    'Select Exemplary to take_out'
    __name__ = 'library.storehouse.take_out.select'

    exit_date = fields.Date('Exit Date', required=True, domain=[
        ('exit_date', '<=', Date()),
        ('exit_date', '>=', Eval('entrance_date'))])
    stocks = fields.Many2Many('library.storehouse', None, None, 'Stocks',
        required=True, domain=[('exit_date', '=', None),
            ('exemplary.shelf', '!=', None)])


class CreateExemplaries(metaclass=PoolMeta):
    __name__ = 'library.book.create_exemplaries'

    def transition_create_exemplaries(self):
        if (self.parameters.acquisition_date and
                self.parameters.acquisition_date > datetime.date.today()):
            self.raise_user_error('invalid_date')
        Exemplary = Pool().get('library.book.exemplary')
        to_create = []
        while len(to_create) < self.parameters.number_of_exemplaries:
            exemplary = Exemplary()
            exemplary.book = self.parameters.book
            exemplary.acquisition_date = self.parameters.acquisition_date
            exemplary.acquisition_price = self.parameters.acquisition_price
            exemplary.identifier = self.parameters.identifier_start + str(
                len(to_create) + 1)
            if len(to_create) >= self.parameters.number_in_storehouse:
                exemplary.shelf = self.parameters.shelf
            to_create.append(exemplary)
        Exemplary.save(to_create)
        self.parameters.exemplaries = to_create
        return 'open_exemplaries'

class CreateExemplariesParameters(metaclass=PoolMeta):
    __name__ = 'library.book.create_exemplaries.parameters'

    number_in_storehouse = fields.Integer('Number in the storehouse',
        required=True, domain=[
            ('number_in_storehouse', '<=', Eval('number_of_exemplaries')),
            ('number_in_storehouse', '>=', 0)],
        help='The number of exemplaries that will be placed in the '
        'storehouse.')
    shelf = fields.Many2One('library.localisation.shelf', 'Shelf', states={
        'required': Less(Eval('number_in_storehouse', 0), Eval('number_of_exemplaries', 0))})


class QuarantineLockDownExemplary(Wizard):
    'Put Exemplary in Quarantine'
    __name__ = 'library.quarantine.lock_down'

    start_state = 'select'
    select = StateView('library.quarantine.lock_down.select',
        'library_localisation.quarantine_exemplaries_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Begin Quarantine', 'lock_down', 'tryton-go-next', default=True)])
    lock_down = StateTransition()
    open_quarantine = StateAction('library_localisation.act_quarantine')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'invalid_model': 'This action should be started from an exemplary.',
                'exemplary_unavailable': 'The following exemplaries are '
                'unavailable: \n%(exemplaries)s',
                'invalid_date': 'The date of entrance in the storehouse can\'t'
                ' be done before an exemplary acquisition (%(date)s).'
                })

    def default_select(self,name):
        if Transaction().context.get('active_model', '') == \
            'library.book.exemplary':
            Exemplary = Pool().get('library.book.exemplary')
            exemplaries = Exemplary.browse(Transaction().context.get('active_ids'))
            exemplaries_unavailable = []
            exemplaries_to_move = []
            for e in exemplaries:
                if e.is_in_quarantine or e.is_borrowed:
                    exemplaries_unavailable.append(e.rec_name)
                else:
                    exemplaries_to_move.append(e.id)
            if len(exemplaries_unavailable) > 0:
                self.raise_user_warning('exemplary_unavailable_warning' + str(
                    exemplaries_unavailable), 'exemplary_unavailable',
                {'exemplaries': ', '.join(exemplaries_unavailable)})
            return {
                'exemplaries': exemplaries_to_move,
                'entrance_date': datetime.date.today()
                }
        else:
            self.raise_user_error('invalid_model')

    def transition_lock_down(self):
        minimum_entrance_date = min(
            [e.acquisition_date for e in self.select.exemplaries])
        if minimum_entrance_date > self.select.entrance_date:
            self.raise_user_error('invalid_date',
                {'date': minimum_entrance_date})
        Quarantine = Pool().get('library.quarantine')
        stocks = []
        for e in self.select.exemplaries:
            stocks.append(
                Quarantine(exemplary=e, entrance_date=self.select.entrance_date))
        Quarantine.save(stocks)
        self.select.stocks = stocks
        return 'open_quarantine'

    def do_open_quarantine(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [x.id for x in self.select.stocks])])
        return action, {}

class QuarantineLockDownExemplarySelect(ModelView):
    'Select Exemplary to store'
    __name__ = 'library.quarantine.lock_down.select'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True, domain=[('is_in_quarantine', '=', False),
            ('is_borrowed', '=', False)])
    entrance_date = fields.Date('Entrance Date', required=True, domain=[
            ('entrance_date', '<=', Date())])
    stocks = fields.Many2Many('library.quarantine', None, None, 'Quarantine', readonly=True)


class QuarantineUnleashExemplary(Wizard):
    'Unleash Exemplary from Quarantine'
    __name__ = 'library.quarantine.unleash'

    start_state = 'select'
    select = StateView('library.quarantine.unleash.select',
        'library_localisation.unleash_exemplaries_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Finish quarantine', 'unleash', 'tryton-go-next', default=True)])
    unleash = StateTransition()
    open_exemplaries = StateAction('library.act_exemplary')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'invalid_model': 'This action should be started from an exemplary.',
                'exemplary_out_quarantine': 'The following exemplaries are not in '
                'quarantine: \n%(exemplaries)s',
                'past_stock': 'The choosen stocks aren\'t actuals: \n%(stocks)s',
                })

    def default_select(self,name):
        # TODO UX: Warn the user that books will be unleashed before the end of their quarantine
        if Transaction().context.get('active_model', '') == \
            'library.quarantine':
            Quarantine = Pool().get('library.quarantine')
            stocks = Quarantine.browse(Transaction().context.get('active_ids'))
            past_stocks = []
            stocks_to_move = []
            for s in stocks:
                if s.exit_date:
                    past_stocks.append(s.rec_name)
                else:
                    stocks_to_move.append(s.id)
            if len(past_stocks) > 0:
                self.raise_user_warning('past_stock_warning' + str(
                    past_stocks), 'past_stock',
                {'stocks': ', '.join(past_stocks)})
            return {
                'stocks': stocks_to_move,
                'exit_date': datetime.date.today()
                }
        else:
            self.raise_user_error('invalid_model')

    def transition_unleash(self):
        Quarantine = Pool().get('library.quarantine')
        Quarantine.write(list(self.select.stocks), {
                'exit_date': self.select.exit_date})
        return 'open_exemplaries'

    def do_open_exemplaries(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [x.exemplary.id for x in self.select.stocks])])
        return action, {}

class QuarantineUnleashExemplarySelect(ModelView):
    'Select Exemplary to unleash'
    __name__ = 'library.quarantine.unleash.select'

    exit_date = fields.Date('Exit Date', required=True, domain=[
        ('exit_date', '<=', Date()),
        ('exit_date', '>=', Eval('entrance_date'))])
    stocks = fields.Many2Many('library.quarantine', None, None, 'Stocks',
        required=True, domain=[('exit_date', '=', None)])

class Return(Wizard):
    'Return'
    __name__ = 'library.user.return'

    put_in_quarantine = StateTransition()

    def transition_return_(self):
        Checkout = Pool().get('library.user.checkout')
        Checkout.write(list(self.select_checkouts.checkouts), {
                'return_date': self.select_checkouts.date})
        return 'put_in_quarantine'

    def transition_put_in_quarantine(self):
        Quarantine = Pool().get('library.quarantine')
        to_create = []
        for c in self.select_checkouts.checkouts:
            to_create.append(Quarantine(entrance_date=datetime.date.today(),
                exemplary=c.exemplary))
        Quarantine.save(to_create)
        return 'end'

    def end(self):
        return 'reload'
