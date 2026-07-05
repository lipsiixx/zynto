import type { CSSProperties } from 'react'

interface Props {
  /** Высота, px */
  h: number
  /** Ширина: px или CSS-значение (default 100%) */
  w?: number | string
  /** Скругление: px или CSS-значение (default var(--radius-sm)) */
  r?: number | string
  style?: CSSProperties
}

/** Мерцающая заглушка загрузки. Держи ≤8 штук на экран — shimmer не бесплатный. */
export function Skeleton({ h, w = '100%', r, style }: Props) {
  return <div className="skeleton" style={{ height: h, width: w, borderRadius: r, ...style }} />
}
