import { useRef, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { haptics } from '@/shared/lib/haptics'
import { useSwipeNav } from '@/shared/lib/useSwipeNav'

/** Порядок вкладок = порядок в BottomNav; свайп ходит по этому массиву. */
const TAB_ORDER = ['/', '/contacts', '/network', '/subscription', '/activate']

type SwipeMode =
  | { mode: 'none' }
  | { mode: 'tabs'; index: number }
  | { mode: 'back'; to: string }

function resolveSwipeMode(pathname: string): SwipeMode {
  // /a/* — хеш принадлежит второму (админскому) роутеру, не вмешиваемся
  if (pathname.startsWith('/a')) return { mode: 'none' }
  // Canvas графа панорамируется пальцем: ВХОД в сеть свайпом с соседних
  // вкладок работает, выход — только тапом по меню
  if (pathname === '/network') return { mode: 'none' }
  const idx = TAB_ORDER.indexOf(pathname)
  if (idx >= 0) return { mode: 'tabs', index: idx }
  if (/^\/contacts\/[^/]+$/.test(pathname)) return { mode: 'back', to: '/contacts' }
  if (pathname === '/referral') return { mode: 'back', to: '/' }
  return { mode: 'none' }
}

/** Координата пути для направления анимации: глубина + индекс вкладки-родителя. */
function coord(pathname: string): { depth: number; index: number } {
  const idx = TAB_ORDER.indexOf(pathname)
  if (idx >= 0) return { depth: 0, index: idx }
  if (pathname.startsWith('/contacts/')) return { depth: 1, index: TAB_ORDER.indexOf('/contacts') }
  if (pathname === '/referral') return { depth: 1, index: 0 }
  return { depth: 0, index: 0 }
}

function computeDir(prev: string, next: string): 'fwd' | 'back' {
  const a = coord(prev)
  const b = coord(next)
  if (a.depth !== b.depth) return b.depth > a.depth ? 'fwd' : 'back'
  return b.index >= a.index ? 'fwd' : 'back'
}

/**
 * Обёртка вокруг <Routes>: анимация входа страницы (направление выводится
 * из пары путей — свайп, тап по меню и BackButton не требуют координации)
 * + свайп-навигация. Для /a/* рендерит children как есть: без key и анимации,
 * чтобы не трогать защиту от hashchange-цикла двух роутеров (см. App.tsx).
 */
export function PageViewport({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const ref = useRef<HTMLDivElement>(null)
  const prevPath = useRef<string | null>(null)

  const path = location.pathname
  const isAdmin = path.startsWith('/a')

  const prev = prevPath.current
  const dir = prev !== null && prev !== path ? computeDir(prev, path) : null
  if (!isAdmin && prev !== path) prevPath.current = path

  const swipe = resolveSwipeMode(path)
  useSwipeNav(ref, {
    enabled: swipe.mode !== 'none',
    onSwipe: dir => {
      if (swipe.mode === 'tabs') {
        const next = swipe.index + (dir === 'left' ? 1 : -1)
        if (next < 0 || next >= TAB_ORDER.length) return false
        haptics.select()
        navigate(TAB_ORDER[next])
        return true
      }
      if (swipe.mode === 'back' && dir === 'right') {
        haptics.select()
        navigate(swipe.to)
        return true
      }
      return false
    },
  })

  if (isAdmin) return <>{children}</>

  return (
    <div ref={ref} key={path} className={`pv${dir ? ` pv-enter-${dir}` : ''}`}>
      {children}
    </div>
  )
}
