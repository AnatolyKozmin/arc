/**
 * Ранний bootstrap для Telegram Mini App.
 * Не подписываемся на viewportChanged + expand: на части клиентов это даёт цикл
 * «изменился вьюпорт → expand → снова событие» и зависание при навигации.
 * @see https://core.telegram.org/bots/webapps — ready(), expand()
 */
export function bootstrapTelegramWebApp() {
  const tg = window.Telegram?.WebApp
  if (!tg) return
  try {
    tg.ready?.()
    tg.expand?.()
  } catch (_) {}
}

bootstrapTelegramWebApp()
