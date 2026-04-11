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

/**
 * Если initData (строка) пустая, но initDataUnsafe уже заполнен (hash, user…),
 * собираем query string для бэкенда. Может не совпасть с оригинальным JSON user —
 * тогда сервер вернёт Invalid initData; в таком случае открывайте приложение через меню/inline.
 */
export function buildInitDataFromUnsafe(tg) {
  const u = tg?.initDataUnsafe
  if (!u || typeof u !== 'object') return ''
  const hash = u.hash
  const authDate = u.auth_date
  if (!hash || authDate == null) return ''

  const skip = new Set(['hash', 'signature'])
  const pairs = []
  for (const key of Object.keys(u)) {
    if (skip.has(key)) continue
    const val = u[key]
    if (val === undefined || val === null) continue
    const encoded = typeof val === 'object' ? JSON.stringify(val) : String(val)
    pairs.push([key, encoded])
  }
  pairs.sort((a, b) => a[0].localeCompare(b[0]))

  const parts = pairs.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
  parts.push(`hash=${encodeURIComponent(hash)}`)
  if (u.signature) parts.push(`signature=${encodeURIComponent(u.signature)}`)
  return parts.join('&')
}

/** Сырой initData для POST /auth/telegram: WebApp API → unsafe → URL → sessionStorage */
export function getInitDataRaw() {
  const tg = window.Telegram?.WebApp

  const fromApi = tg?.initData
  if (fromApi && String(fromApi).trim()) return String(fromApi)

  const fromUnsafe = buildInitDataFromUnsafe(tg)
  if (fromUnsafe) return fromUnsafe

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
