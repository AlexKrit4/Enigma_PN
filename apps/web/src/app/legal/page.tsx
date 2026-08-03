const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";
const DOMAIN = process.env.NEXT_PUBLIC_DOMAIN || "bigwinzone.ru";
const SUPPORT = "@alexkr1t";

export default function LegalPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-6 py-16 text-mist">
      <a href="/" className="text-sm text-accent">
        ← На главную
      </a>
      <h1 className="font-display mt-8 text-4xl">Публичная оферта (шаблон)</h1>
      <p className="mt-4 text-mist/70">
        Документ-шаблон для {BRAND} ({DOMAIN}). Перед продажей согласуйте с юристом.
      </p>
      <div className="prose prose-invert mt-10 space-y-4 text-sm leading-7 text-mist/80">
        <p>
          1. Исполнитель предоставляет Пользователю доступ к сервису VPN/прокси (подписка для клиента Happ) на условиях
          выбранного тарифа.
        </p>
        <p>
          2. Оплата производится через ЮMoney. Доступ активируется автоматически после подтверждения платежа
          HTTP-уведомлением.
        </p>
        <p>
          3. Пользователь обязуется соблюдать законодательство своей юрисдикции и не использовать сервис для незаконной
          деятельности.
        </p>
        <p>
          4. Пробный период предоставляется один раз на аккаунт. Возврат средств — по правилам, опубликованным
          Исполнителем.
        </p>
        <p>
          5. Поддержка: {SUPPORT}. Сайт: https://{DOMAIN}.
        </p>
        <p>6. Политика конфиденциальности: обрабатываются Telegram ID, данные заказов и технические логи доступа.</p>
      </div>
    </main>
  );
}
