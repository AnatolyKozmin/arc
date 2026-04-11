/** Ключ sessionStorage — совпадает с inline-скриптом в index.html */
export const ARK_TG_INIT_STORAGE_KEY = 'ark_tg_init_data_raw'

/**
 * Достаёт tgWebAppData из текущего URL (hash / query / regex).
 * Нужно при каждом опросе: клиент Telegram иногда заполняет initData с задержкой,
 * а фрагмент может быть вида "#/route&tgWebAppData=...".
 */
export function peekTgWebAppDataFromLocation() {
  try {
    const href = window.location.href || ''
    const hash = window.location.hash || ''
    const search = (window.location.search || '').replace(/^\?/, '')

    let fragment = hash.startsWith('#') ? hash.slice(1) : hash
    if (fragment.startsWith('/')) {
      const i = fragment.indexOf('tgWebAppData=')
      if (i !== -1) fragment = fragment.slice(i)
    }

    for (const part of [fragment, search, [fragment, search].filter(Boolean).join('&')]) {
      if (!part) continue
      const p = new URLSearchParams(part)
      const v = p.get('tgWebAppData')
      if (v && String(v).trim()) return String(v)
    }

    const m = href.match(/[#?&]tgWebAppData=([^&]+)/)
    if (m && m[1]) {
      try {
        return decodeURIComponent(m[1])
      } catch {
        return m[1]
      }
    }
  } catch (_) {}
  return ''
}

/** Сырой initData для POST /auth/telegram: WebApp API → URL → sessionStorage */
export function getInitDataRaw() {
  const fromApi = window.Telegram?.WebApp?.initData
  if (fromApi && String(fromApi).trim()) return String(fromApi)

  const fromLoc = peekTgWebAppDataFromLocation()
  if (fromLoc) {
    try {
      sessionStorage.setItem(ARK_TG_INIT_STORAGE_KEY, fromLoc)
    } catch (_) {}
    return fromLoc
  }

  try {
    const fromStore = sessionStorage.getItem(ARK_TG_INIT_STORAGE_KEY)
    if (fromStore && String(fromStore).trim()) return String(fromStore)
  } catch (_) {}
  return ''
}
