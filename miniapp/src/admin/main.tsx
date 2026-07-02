import { createRoot, type Root } from 'react-dom/client'
import { useCallback, useState } from 'react'
import { RoleChooser } from '@/admin/chooser/RoleChooser'
import './styles.css'

interface MountCtx {
  token: string
}

function AdminRoot({ ctx }: { ctx: MountCtx }) {
  const [dismissed, setDismissed] = useState(false)

  const handleDismiss = useCallback(() => {
    // Возвращаем пользователя на главный экран основного приложения — иначе
    // основной HashRouter останется на "/a/..." (см. исключение "/a/*" в
    // App.tsx) и покажет пустую страницу до следующей навигации.
    window.location.hash = '/'
    setDismissed(true)
  }, [])

  if (dismissed) return null

  return <RoleChooser token={ctx.token} onDismiss={handleDismiss} />
}

function mount(container: HTMLElement, ctx: MountCtx): () => void {
  const root: Root = createRoot(container)
  root.render(<AdminRoot ctx={ctx} />)
  return () => root.unmount()
}

export default { mount }
