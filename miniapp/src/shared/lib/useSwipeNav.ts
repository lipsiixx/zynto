import { useEffect, useRef, type RefObject } from 'react'

export interface SwipeNavOptions {
  /** false — жест полностью выключен (страницы без свайпа, /a/*) */
  enabled: boolean
  /** Коммит жеста. Вернуть false, если навигации не будет (край списка вкладок). */
  onSwipe: (dir: 'left' | 'right') => boolean
}

// Элементы, с которых жест не начинается: canvas графа, слайдеры, горизонтально
// скроллируемые табы, медиа, нижнее меню и явный opt-out через data-noswipe.
const IGNORE_SELECTOR = 'canvas, input[type=range], .tabs, audio, video, .bottom-nav, [data-noswipe]'
const EDGE_GUARD = 24 // px по краям экрана — за системными жестами Telegram/iOS
const INTENT_DIST = 10 // мёртвая зона до определения направления жеста
const INTENT_RATIO = 1.4 // |dx| > |dy| * ratio → жест горизонтальный
const COMMIT_DIST = 70 // порог дистанции для навигации
const COMMIT_VELOCITY = 0.5 // px/ms — флик засчитывается и на меньшей дистанции
const PEEK_FACTOR = 0.35 // резистанс: страница сдвигается на треть пальца
const PEEK_MAX = 64 // px — максимум сдвига «подглядывания»

type GestureState = 'idle' | 'ignore' | 'pending' | 'horizontal' | 'vertical'

/**
 * Свайп-навигация: слушатели на document (переживают keyed-ремаунт обёртки),
 * transform пишется напрямую в targetRef.current без setState — ноль
 * ре-рендеров во время жеста. Все слушатели passive: preventDefault не
 * вызывается, скролл-пайплайн браузера не блокируется.
 */
export function useSwipeNav(targetRef: RefObject<HTMLElement | null>, opts: SwipeNavOptions) {
  const onSwipeRef = useRef(opts.onSwipe)
  onSwipeRef.current = opts.onSwipe

  useEffect(() => {
    if (!opts.enabled) return

    let state: GestureState = 'idle'
    let x0 = 0
    let y0 = 0
    let t0 = 0
    let dx = 0
    let raf = 0

    const applyPeek = () => {
      raf = 0
      const node = targetRef.current
      if (!node || state !== 'horizontal') return
      const peek = Math.max(-PEEK_MAX, Math.min(PEEK_MAX, dx * PEEK_FACTOR))
      node.style.transform = `translateX(${peek}px)`
    }

    const reset = (spring: boolean) => {
      if (raf) {
        cancelAnimationFrame(raf)
        raf = 0
      }
      const node = targetRef.current
      if (node) {
        if (spring && node.style.transform) {
          node.style.transition = 'transform 0.15s ease'
          node.style.transform = 'translateX(0)'
          window.setTimeout(() => {
            node.style.transition = ''
            node.style.transform = ''
            node.style.willChange = ''
          }, 160)
        } else {
          node.style.transition = ''
          node.style.transform = ''
          node.style.willChange = ''
        }
      }
      state = 'idle'
      dx = 0
    }

    const onStart = (e: TouchEvent) => {
      if (e.touches.length !== 1) {
        state = 'ignore'
        return
      }
      const t = e.touches[0]
      const target = e.target as HTMLElement | null
      if (target?.closest?.(IGNORE_SELECTOR)) {
        state = 'ignore'
        return
      }
      if (t.clientX < EDGE_GUARD || t.clientX > window.innerWidth - EDGE_GUARD) {
        state = 'ignore'
        return
      }
      x0 = t.clientX
      y0 = t.clientY
      t0 = performance.now()
      state = 'pending'
    }

    const onMove = (e: TouchEvent) => {
      if (state !== 'pending' && state !== 'horizontal') return
      const t = e.touches[0]
      const mx = t.clientX - x0
      const my = t.clientY - y0
      if (state === 'pending') {
        if (Math.abs(mx) < INTENT_DIST && Math.abs(my) < INTENT_DIST) return
        if (Math.abs(mx) > Math.abs(my) * INTENT_RATIO) {
          state = 'horizontal'
          const node = targetRef.current
          if (node) node.style.willChange = 'transform'
        } else {
          state = 'vertical'
          return
        }
      }
      dx = mx
      if (!raf) raf = requestAnimationFrame(applyPeek)
    }

    const onEnd = () => {
      if (state !== 'horizontal') {
        state = 'idle'
        return
      }
      const dt = Math.max(1, performance.now() - t0)
      const velocity = Math.abs(dx) / dt
      const commit =
        Math.abs(dx) > COMMIT_DIST ||
        (Math.abs(dx) > INTENT_DIST * 2 && velocity > COMMIT_VELOCITY)
      const dir: 'left' | 'right' = dx < 0 ? 'left' : 'right'
      if (commit && onSwipeRef.current(dir)) {
        // Навигация случится: обёртка ремаунтится с анимацией входа,
        // пружинить старый узел не нужно.
        reset(false)
      } else {
        reset(true)
      }
    }

    const onCancel = () => {
      if (state === 'horizontal') reset(true)
      else state = 'idle'
    }

    document.addEventListener('touchstart', onStart, { passive: true })
    document.addEventListener('touchmove', onMove, { passive: true })
    document.addEventListener('touchend', onEnd, { passive: true })
    document.addEventListener('touchcancel', onCancel, { passive: true })
    return () => {
      document.removeEventListener('touchstart', onStart)
      document.removeEventListener('touchmove', onMove)
      document.removeEventListener('touchend', onEnd)
      document.removeEventListener('touchcancel', onCancel)
      reset(false)
    }
  }, [opts.enabled, targetRef])
}
