const QUERY = '(prefers-reduced-motion: reduce)'

/** Разовая проверка (для не-реактивных мест: rAF-анимации, жесты). */
export function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(QUERY).matches
}
