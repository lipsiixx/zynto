"""FSM состояния для пользователей."""
from aiogram.fsm.state import State, StatesGroup


class ActivateCodeStates(StatesGroup):
    waiting_code = State()


class SearchHistoryStates(StatesGroup):
    waiting_query = State()


class GiftSubscriptionStates(StatesGroup):
    waiting_tariff = State()
