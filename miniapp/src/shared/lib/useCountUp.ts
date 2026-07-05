import { useEffect, useRef, useState } from 'react'
import { prefersReducedMotion } from './useReducedMotion'

/**
 * Плавный «набег» числа: 0 → target на маунте, затем от предыдущего значения
 * при изменении target. rAF + ease-out cubic; при reduced-motion или скрытой
 * вкладке значение ставится мгновенно.
 */
export function useCountUp(target: number, duration = 600): number {
  const [value, setValue] = useState(0)
  const prev = useRef(0)

  useEffect(() => {
    const from = prev.current
    prev.current = target
    if (from === target || prefersReducedMotion() || document.hidden) {
      setValue(target)
      return
    }
    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / duration)
      const eased = 1 - (1 - p) ** 3
      setValue(Math.round(from + (target - from) * eased))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])

  return value
}
