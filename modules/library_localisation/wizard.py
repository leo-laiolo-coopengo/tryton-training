from trytond.wizard import Wizard, StateView, StateTransition, StateAction, Button
from trytond.model import ModelView, fields
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder
from trytond.pool import Pool


__all__ = [
    'MoveExemplaryOnShelf',
    'MoveExemplaryOnShelfSelection',
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
                'invalid_model': 'This action should be started from a book',
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

    exemplaries = fields.Many2Many('library.book.exemplary', None, None, 'Exemplaries', required=True)
    shelf = fields.Many2One('library.localisation.shelf', 'Shelf', required=True)
