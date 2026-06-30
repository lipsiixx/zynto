"""FSM состояния для админ-панели."""
from aiogram.fsm.state import State, StatesGroup


class CreateTariffStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_duration = State()
    waiting_price = State()
    waiting_sort_order = State()
    confirm = State()


class EditTariffStates(StatesGroup):
    waiting_field = State()
    waiting_value = State()


class CreatePromoStates(StatesGroup):
    waiting_type = State()
    # access-код
    waiting_duration = State()
    waiting_custom_days = State()
    # скидочный код
    waiting_discount_tariff = State()
    waiting_discount_amount = State()
    # общее
    waiting_max_uses = State()
    waiting_code_expiry = State()
    waiting_note = State()


class AddAdminStates(StatesGroup):
    waiting_identifier = State()
    confirm = State()


class BanUserStates(StatesGroup):
    waiting_reason = State()


class CleanupSettingsStates(StatesGroup):
    waiting_text_days = State()
    waiting_media_days = State()


class ManualSubscriptionStates(StatesGroup):
    waiting_tariff = State()
    waiting_days = State()
    confirm = State()


class FindUserStates(StatesGroup):
    waiting_identifier = State()


class BroadcastStates(StatesGroup):
    waiting_content = State()
    confirm = State()


class ReferralSettingsStates(StatesGroup):
    waiting_bonus_days = State()


class CourseEditStates(StatesGroup):
    waiting_video = State()
    waiting_caption = State()


class NudgeStates(StatesGroup):
    waiting_text = State()       # добавление нового сообщения
    waiting_edit_text = State()  # редактирование существующего
    waiting_interval = State()   # изменение периодичности
    waiting_grace = State()      # изменение порога (дней после истечения)


class TributeSettingsStates(StatesGroup):
    waiting_days = State()


class AboutSettingsStates(StatesGroup):
    waiting_privacy_content = State()
    waiting_terms_content = State()
    waiting_support_url = State()
