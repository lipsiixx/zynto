export interface LoadedModule {
  mount: (el: HTMLElement, ctx: { token: string; fullAccess: boolean }) => () => void
}

export async function loadAdminModule(token: string): Promise<LoadedModule | null> {
  try {
    const res = await fetch('/v1/webapp/modules/core', { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) return null
    const { js, css } = await res.json()
    if (css) {
      const style = document.createElement('style')
      style.textContent = css
      document.head.appendChild(style)
    }
    const blob = new Blob([js], { type: 'text/javascript' })
    const url = URL.createObjectURL(blob)
    const mod = await import(/* @vite-ignore */ url)
    URL.revokeObjectURL(url)
    return mod.default
  } catch {
    return null
  }
}
