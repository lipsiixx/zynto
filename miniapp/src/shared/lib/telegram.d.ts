interface TelegramWebAppUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  language_code?: string
  photo_url?: string
}

interface SafeAreaInset {
  top: number
  bottom: number
  left: number
  right: number
}

interface TelegramWebApp {
  initData: string
  initDataUnsafe: {
    user?: TelegramWebAppUser
    query_id?: string
    auth_date?: number
    hash?: string
  }
  colorScheme: 'dark' | 'light'
  themeParams: {
    bg_color?: string
    text_color?: string
    hint_color?: string
    link_color?: string
    button_color?: string
    button_text_color?: string
  }
  isExpanded: boolean
  viewportHeight: number
  viewportStableHeight: number
  safeAreaInset?: SafeAreaInset
  contentSafeAreaInset?: SafeAreaInset
  ready(): void
  expand(): void
  close(): void
  openLink(url: string, options?: { try_instant_view?: boolean }): void
  onEvent(eventType: string, handler: () => void): void
  offEvent(eventType: string, handler: () => void): void
  BackButton: {
    isVisible: boolean
    show(): void
    hide(): void
    onClick(cb: () => void): void
    offClick(cb: () => void): void
  }
  MainButton: {
    text: string
    color: string
    textColor: string
    isVisible: boolean
    isActive: boolean
    isProgressVisible: boolean
    setText(text: string): void
    onClick(cb: () => void): void
    offClick(cb: () => void): void
    show(): void
    hide(): void
    enable(): void
    disable(): void
    showProgress(leaveActive?: boolean): void
    hideProgress(): void
  }
  HapticFeedback: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
    notificationOccurred(type: 'error' | 'success' | 'warning'): void
    selectionChanged(): void
  }
}

interface Window {
  Telegram: {
    WebApp: TelegramWebApp
  }
}
