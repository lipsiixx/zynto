// Обёртка над Telegram HapticFeedback. Вне Telegram (dev в браузере) или на
// старых клиентах API отсутствует — все вызовы становятся no-op.
const hf = () => window.Telegram?.WebApp?.HapticFeedback

export const haptics = {
  /** Лёгкий удар — тап по навигации/карточке */
  tap: () => {
    try { hf()?.impactOccurred('light') } catch { /* API недоступен */ }
  },
  /** Смена выбора — табы, свайп между страницами, слайдер */
  select: () => {
    try { hf()?.selectionChanged() } catch { /* API недоступен */ }
  },
  /** Успешное действие — покупка, копирование, активация */
  success: () => {
    try { hf()?.notificationOccurred('success') } catch { /* API недоступен */ }
  },
  /** Ошибка действия */
  error: () => {
    try { hf()?.notificationOccurred('error') } catch { /* API недоступен */ }
  },
}
