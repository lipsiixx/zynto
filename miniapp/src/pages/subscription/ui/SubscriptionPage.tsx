import { useEffect, useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import type { Tariff, TributeProduct } from "@/entities/tariff";
import { getTariffs, getTributeProducts } from "@/entities/tariff";
import { BuyButton } from "@/features/buy-subscription";
import { useApp } from "@/app/AppContext";
import { Skeleton } from "@/shared/ui";

// Траектории разлетающихся звёзд вокруг карточки с акцией (см. .sale-star в
// app/styles.css) — задержки staggered, чтобы на карточке был лёгкий
// непрерывный "искрящийся" эффект, а не одна общая вспышка раз в N секунд.
const SALE_STAR_OFFSETS: { tx: number; ty: number; delay: number }[] = [
  { tx: -115, ty: -34, delay: 0 },
  { tx: 108, ty: -46, delay: 0.7 },
  { tx: -70, ty: 42, delay: 1.4 },
  { tx: 96, ty: 40, delay: 2.1 },
  { tx: -24, ty: -58, delay: 2.8 },
  { tx: 30, ty: 54, delay: 3.5 },
];

function openSbpLink(url: string) {
  const tg = window.Telegram?.WebApp;
  if (tg?.openLink) {
    tg.openLink(url, { try_instant_view: false });
  } else {
    window.open(url, "_blank");
  }
}

function fmtDuration(days: number | null) {
  if (days === null || days === 0) return "♾ Навсегда";
  if (days === 1) return "1 день";
  if (days < 30) return `${days} дней`;
  if (days < 365) {
    const m = Math.round(days / 30);
    return m === 1 ? "1 месяц" : `${m} месяца`;
  }
  const y = Math.round(days / 365);
  return y === 1 ? "1 год" : `${y} года`;
}

function SubStatusCard() {
  const { me } = useApp();
  if (!me) return null;
  const { subscription: s } = me;

  let label = "";
  let accent = "var(--text2)";
  if (s.status === "lifetime") {
    label = "♾ Подписка навсегда";
    accent = "var(--purple-l)";
  } else if (s.status === "active") {
    const d = s.expires_at
      ? new Date(s.expires_at).toLocaleDateString("ru", {
          day: "2-digit",
          month: "long",
          year: "numeric",
        })
      : "";
    label = `✅ Активна до ${d}`;
    accent = "var(--green)";
  } else if (s.status === "expired") {
    label = "❌ Истекла";
    accent = "var(--red)";
  } else {
    label = "Нет подписки";
    accent = "var(--text3)";
  }

  return (
    <div className="card" style={{ textAlign: "center", padding: 20 }}>
      <div style={{ fontSize: 13, color: "var(--text2)", marginBottom: 6 }}>
        Текущий статус
      </div>
      <div style={{ fontSize: 17, fontWeight: 700, color: accent }}>
        {label}
      </div>
    </div>
  );
}

export function SubscriptionPage() {
  const { showToast } = useApp();
  const navigate = useNavigate();
  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [loading, setLoading] = useState(true);
  const [tributeProducts, setTributeProducts] = useState<TributeProduct[]>([]);

  useEffect(() => {
    getTariffs()
      .then((r) => setTariffs(r.data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    getTributeProducts()
      .then(setTributeProducts)
      .catch(() => setTributeProducts([]));
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Подписка</h1>
      </div>

      <SubStatusCard />

      <div className="mt-16">
        {tributeProducts.length > 0 && (
          <>
            <div className="text-sm text2 mb-12">💳 Оплата через СБП</div>
            {tributeProducts.map((p) => (
              <div key={p.tribute_product_id} className="card" style={{ marginBottom: 12 }}>
                <div className="row-between">
                  <div>
                    <div className="semibold" style={{ fontSize: 16 }}>{p.name}</div>
                    <div className="text-xs text2 mt-8">{fmtDuration(p.duration_days)}</div>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0, marginLeft: 12 }}>
                    <div className="bold" style={{ fontSize: 20, color: "var(--purple-l)" }}>
                      {p.price > 0
                        ? `${(p.price / 100).toLocaleString("ru-RU")} ₽`
                        : "Бесплатно"}
                    </div>
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  style={{ marginTop: 12, width: "100%" }}
                  onClick={() => openSbpLink(p.web_link)}
                >
                  Оплатить через СБП
                </button>
              </div>
            ))}
            <div className="divider" style={{ margin: "16px 0" }} />
          </>
        )}

        <div className="text-sm text2 mb-12">⭐ Оплата звёздами</div>
        {loading ? (
          <>
            {[0, 1, 2].map((i) => (
              <div key={i} className="card" style={{ marginBottom: 12 }}>
                <div className="row-between">
                  <div style={{ flex: 1 }}>
                    <Skeleton h={16} w="45%" />
                    <Skeleton h={11} w="30%" style={{ marginTop: 8 }} />
                  </div>
                  <Skeleton h={20} w={64} />
                </div>
                <Skeleton h={46} style={{ marginTop: 12 }} />
              </div>
            ))}
          </>
        ) : tariffs.length === 0 ? (
          <div className="empty-state">
            <div className="icon">😔</div>
            <div>Нет доступных тарифов</div>
          </div>
        ) : (
          tariffs.map((t) => {
            const onSale = t.discount_percent != null;
            return (
              <div
                key={t.id}
                className={`card${onSale ? " sale-card" : ""}`}
                style={{ marginBottom: 12 }}
              >
                {onSale && (
                  <>
                    <div className="sale-badge">🔥 АКЦИЯ</div>
                    <div className="sale-stars" aria-hidden="true">
                      {SALE_STAR_OFFSETS.map((o, i) => (
                        <span
                          key={i}
                          className="sale-star"
                          style={
                            {
                              "--tx": `${o.tx}px`,
                              "--ty": `${o.ty}px`,
                              animationDelay: `${o.delay}s`,
                            } as CSSProperties
                          }
                        >
                          ⭐
                        </span>
                      ))}
                    </div>
                  </>
                )}
                <div className="row-between">
                  <div>
                    <div className="semibold" style={{ fontSize: 16 }}>
                      {t.name}
                    </div>
                    <div className="text-xs text2 mt-8">
                      {fmtDuration(t.duration_days)}
                    </div>
                    {t.description && (
                      <div className="text-xs text3 mt-8">{t.description}</div>
                    )}
                  </div>
                  <div
                    style={{ textAlign: "right", flexShrink: 0, marginLeft: 12 }}
                  >
                    {onSale ? (
                      <>
                        <div className="sale-price-old">
                          {t.original_price_stars} ⭐
                        </div>
                        <div
                          className="row gap-8"
                          style={{ justifyContent: "flex-end", marginTop: 2 }}
                        >
                          <div className="bold sale-price-new">
                            {t.price_stars} ⭐
                          </div>
                          <span className="badge badge-yellow">
                            −{t.discount_percent}%
                          </span>
                        </div>
                      </>
                    ) : (
                      <div
                        className="bold"
                        style={{ fontSize: 20, color: "var(--purple-l)" }}
                      >
                        {t.price_stars} ⭐
                      </div>
                    )}
                  </div>
                </div>
                <BuyButton
                  tariff={t}
                  onSuccess={(msg) => showToast(msg, "success")}
                  onError={(msg) => showToast(msg, "error")}
                />
              </div>
            );
          })
        )}

        <button
          className="btn btn-secondary mt-16"
          onClick={() => navigate("/activate")}
        >
          🎟 Активировать промокод
        </button>
      </div>
    </div>
  );
}
