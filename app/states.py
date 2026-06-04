from aiogram.fsm.state import StatesGroup, State
class CreateMatch(StatesGroup):
    category=State(); photo=State(); title=State(); start=State(); end=State(); confirm=State()
class TrustedMatch(StatesGroup):
    category=State(); photo=State(); title=State(); start=State(); end=State(); confirm=State()
class SuggestMatch(StatesGroup):
    category=State(); title=State(); date=State(); photo=State()
class AddWord(StatesGroup): word=State()
class SetRules(StatesGroup): text=State()
class SetStartText(StatesGroup): text=State()
class SetStartPhoto(StatesGroup): photo=State()
class Broadcast(StatesGroup): target=State(); text=State(); category=State()
class RoleEdit(StatesGroup): add_admin=State(); del_admin=State(); add_trusted=State(); del_trusted=State()
class CloseMatch(StatesGroup): score=State()
class AddHash(StatesGroup): media=State()

class VoteScore(StatesGroup): score=State()
