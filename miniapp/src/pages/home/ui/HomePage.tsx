import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "@/app/AppContext";
import { getInstructionPhotoUrl } from "@/entities/message";
import { HistoryRetentionControl } from "@/features/history-retention";
import { useCountUp } from "@/shared/lib/useCountUp";
import { Skeleton } from "@/shared/ui";

// ── Countdown ─────────────────────────────────────────────────────────────

function calcRemaining(expiresAt: string): {
  d: number;
  h: number;
  m: number;
  s: number;
  total: number;
} {
  const diff = Math.max(0, new Date(expiresAt).getTime() - Date.now());
  const total = Math.floor(diff / 1000);
  const d = Math.floor(total / 86400);
  const h = Math.floor((total % 86400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return { d, h, m, s, total };
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

function moodEmoji(pct: number): string {
  if (pct > 80) return "😄";
  if (pct > 60) return "🙂";
  if (pct > 40) return "😐";
  if (pct > 20) return "😟";
  if (pct > 5) return "😩";
  return "😱";
}

function barColor(pct: number): string {
  if (pct > 60) return "var(--green)";
  if (pct > 40) return "var(--yellow)";
  if (pct > 20) return "#e07d2a";
  return "var(--red)";
}

function SubProgressBar({ pct }: { pct: number }) {
  const color = barColor(pct);
  return (
    <div className="sub-bar-track">
      <div
        className="sub-bar-fill"
        style={{
          width: `${Math.max(pct, 2)}%`,
          background: color,
          boxShadow: `0 0 8px ${color}88`,
        }}
      />
    </div>
  );
}

function Countdown({
  expiresAt,
  startedAt,
}: {
  expiresAt: string;
  startedAt: string | null;
}) {
  const [rem, setRem] = useState(() => calcRemaining(expiresAt));

  useEffect(() => {
    const id = setInterval(() => setRem(calcRemaining(expiresAt)), 1000);
    return () => clearInterval(id);
  }, [expiresAt]);

  if (rem.total <= 0) {
    return <div className="countdown-expired">Подписка истекла</div>;
  }

  // Процент оставшегося времени
  const totalSec = startedAt
    ? (new Date(expiresAt).getTime() - new Date(startedAt).getTime()) / 1000
    : null;
  const pct =
    totalSec && totalSec > 0
      ? Math.min(100, Math.max(0, (rem.total / totalSec) * 100))
      : null;

  const isUrgent = rem.d === 0 && rem.h === 0 && rem.m < 30;

  return (
    <div className="countdown-wrap">
      <div className="countdown-label">До истечения подписки</div>

      {rem.d >= 3 ? (
        <div className="countdown-days">
          {rem.d}{" "}
          {rem.d % 10 === 1 && rem.d !== 11
            ? "день"
            : rem.d % 10 <= 4 && (rem.d < 11 || rem.d > 14)
              ? "дня"
              : "дней"}
          {rem.h > 0 && <span className="countdown-days-h"> {rem.h} ч</span>}
        </div>
      ) : (
        <>
          {rem.d > 0 && <div className="countdown-days-sm">{rem.d} д </div>}
          <div
            className={`countdown-clock${isUrgent ? " countdown-urgent" : ""}`}
          >
            {pad(rem.h)}:{pad(rem.m)}:{pad(rem.s)}
          </div>
        </>
      )}

      {pct !== null && (
        <div className="sub-bar-row">
          <span className="sub-bar-emoji">{moodEmoji(pct)}</span>
          <SubProgressBar pct={pct} />
        </div>
      )}
    </div>
  );
}

function LifetimeBadge() {
  return (
    <div className="countdown-wrap">
      <div className="countdown-label">Статус подписки</div>
      <div className="countdown-lifetime">♾ Навсегда</div>
    </div>
  );
}

function HowToConnect() {
  const [open, setOpen] = useState(false);
  const [imgError, setImgError] = useState(false);

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <button className="how-connect-toggle" onClick={() => setOpen((o) => !o)}>
        <span>📋 Как подключить бота?</span>
        <span className={`how-connect-chevron${open ? " open" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="how-connect-body">
          {!imgError && (
            <img
              src={getInstructionPhotoUrl()}
              alt="Инструкция по подключению"
              className="how-connect-photo"
              onError={() => setImgError(true)}
              loading="lazy"
            />
          )}
          <div className="how-connect-steps">
            <div className="how-connect-step">
              <span className="step-num">1</span>
              <span>
                Открой <b>Настройки → Аккаунт</b>
                <br />
                <span style={{ color: "var(--text3)", fontSize: 12 }}>
                  iOS: Профиль → Изменить
                </span>
              </span>
            </div>
            <div className="how-connect-step">
              <span className="step-num">2</span>
              <span>
                Найди раздел <b>«Автоматизация чатов»</b>
              </span>
            </div>
            <div className="how-connect-step">
              <span className="step-num">3</span>
              <span>
                Добавь <b>@zynto_bot</b> и нажми <b>«Добавить»</b>
              </span>
            </div>
          </div>
          <div className="text-xs text3" style={{ marginTop: 8 }}>
            ✅ После подключения бот пришлёт подтверждение
          </div>
        </div>
      )}
    </div>
  );
}

function HistoryRetentionCard({
  hours,
  onSaved,
  showToast,
}: {
  hours: number;
  onSaved: (hours: number) => void;
  showToast: (msg: string, type?: "success" | "error" | "info") => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <button className="how-connect-toggle" onClick={() => setOpen((o) => !o)}>
        <span>⚙️ Срок хранения</span>
        <span className={`how-connect-chevron${open ? " open" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="how-connect-body">
          <div className="text-xs text3" style={{ marginBottom: 14 }}>
            Как долго хранить историю сообщений и присылать уведомления об
            удалённых и изменённых
          </div>
          <HistoryRetentionControl
            currentHours={hours}
            onSaved={onSaved}
            showToast={showToast}
          />
        </div>
      )}
    </div>
  );
}

function NoSubBlock() {
  const navigate = useNavigate();
  return (
    <div className="no-sub-block">
      <div className="no-sub-emoji">😔</div>
      <div className="no-sub-title">Подписка не оформлена</div>
      <div className="no-sub-text">
        Без подписки удалённые и изменённые сообщения не сохраняются.
        <br />
        Оформи подписку — и больше ничего не потеряешь.
      </div>
      <button
        className="btn btn-primary"
        style={{ marginTop: 20 }}
        onClick={() => navigate("/subscription")}
      >
        💳 Оформить подписку
      </button>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────

export function HomePage() {
  const { me, refreshMe, showToast } = useApp();
  const navigate = useNavigate();

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  if (!me) {
    return (
      <div className="page">
        <div className="card" style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Skeleton h={56} w={56} r="50%" />
          <div style={{ flex: 1 }}>
            <Skeleton h={16} w="55%" />
            <Skeleton h={12} w="35%" style={{ marginTop: 8 }} />
          </div>
        </div>
        <div className="card">
          <Skeleton h={60} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card" style={{ padding: "14px 16px", marginBottom: 0 }}>
              <Skeleton h={22} w={22} r="50%" />
              <Skeleton h={20} w="50%" style={{ marginTop: 8 }} />
              <Skeleton h={10} w="70%" style={{ marginTop: 6 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const { summary, subscription, monitoring_active } = me;
  const initials = me.full_name
    ? me.full_name
        .split(" ")
        .slice(0, 2)
        .map((w) => w[0])
        .join("")
        .toUpperCase()
    : "?";

  const hasActive = subscription.has_active;
  const isLifetime = subscription.status === "lifetime";

  return (
    <div className="page">
      {/* Profile */}
      <div
        className="card card-glow"
        style={{ display: "flex", alignItems: "center", gap: 14 }}
      >
        <div className="avatar" style={{ width: 56, height: 56, fontSize: 20 }}>
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="bold truncate" style={{ fontSize: 17 }}>
            {me.full_name}
          </div>
          {me.username && <div className="text-sm text3">@{me.username}</div>}
        </div>
      </div>

      {/* Subscription countdown / no-sub */}
      {hasActive && isLifetime && <LifetimeBadge />}
      {hasActive && !isLifetime && subscription.expires_at && (
        <div className="card">
          <Countdown
            expiresAt={subscription.expires_at}
            startedAt={subscription.started_at ?? null}
          />
          <button
            className="btn btn-secondary"
            style={{ marginTop: 14, fontSize: 13 }}
            onClick={() => navigate("/subscription")}
          >
            Продлить подписку
          </button>
        </div>
      )}
      {!hasActive && <NoSubBlock />}

      {/* Monitoring status */}
      {hasActive && (
        <div
          className="card"
          style={{ display: "flex", alignItems: "center", gap: 12 }}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: monitoring_active ? "var(--green)" : "var(--text3)",
              boxShadow: monitoring_active ? "0 0 8px var(--green)" : "none",
              flexShrink: 0,
            }}
          />
          <div>
            <div className="semibold text-sm">
              {monitoring_active
                ? "Мониторинг активен"
                : "Мониторинг не подключён"}
            </div>
            <div className="text-xs text3">
              {monitoring_active
                ? "Слежу за удалёнными и изменёнными сообщениями"
                : "Подключи бизнес-аккаунт в Telegram"}
            </div>
          </div>
        </div>
      )}

      {/* How to connect — показываем когда мониторинг не активен */}
      {hasActive && !monitoring_active && <HowToConnect />}

      {/* Срок хранения истории и уведомлений */}
      {hasActive && (
        <HistoryRetentionCard
          hours={me.history_retention_hours}
          onSaved={() => refreshMe()}
          showToast={showToast}
        />
      )}

      {/* Stats */}
      {hasActive && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 10,
              marginBottom: 12,
            }}
          >
            <StatCard label="Контактов" value={summary.contacts} icon="👥" />
            <StatCard
              label="Сообщений"
              value={summary.total_messages}
              icon="💬"
            />
            <StatCard
              label="Удалено"
              value={summary.deleted}
              icon="🗑"
              accent="var(--red)"
            />
            <StatCard
              label="Изменено"
              value={summary.edited}
              icon="✏️"
              accent="var(--yellow)"
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={() => navigate("/contacts")}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
            </svg>
            Открыть историю
          </button>
        </>
      )}

      {/* Реферальная программа — доступна всем, и без подписки */}
      <div
        className="card card-tap"
        style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 12, cursor: "pointer" }}
        onClick={() => navigate("/referral")}
      >
        <div style={{ fontSize: 26, flexShrink: 0 }}>👥</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="semibold text-sm">Пригласи друга</div>
          <div className="text-xs text3">
            Получай бесплатные дни за каждую оплату по твоей ссылке
          </div>
        </div>
        <div className="text3" style={{ fontSize: 18, flexShrink: 0 }}>›</div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number;
  icon: string;
  accent?: string;
}) {
  const shown = useCountUp(value);
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 22, marginBottom: 6 }}>{icon}</div>
      <div
        className="bold"
        style={{ fontSize: 22, color: accent || "var(--text)" }}
      >
        {shown.toLocaleString()}
      </div>
      <div className="text-xs text2">{label}</div>
    </div>
  );
}
