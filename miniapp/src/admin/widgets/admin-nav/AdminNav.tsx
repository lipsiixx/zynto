import { NavLink } from 'react-router-dom'

interface Props {
  isSuperadmin: boolean
  /** false — вход через Start/меню (не /admin ?admin_entry=full): скрываем
   *  «Пользователи», роуты /a/users* всё равно редиректят на дашборд. */
  fullAccess: boolean
}

// Phase 2: добавлены разделы управления ботом (промокоды/тарифы/пользователи/
// рассылка/настройки), «Админы» показывается только суперадмину — сам
// бэкенд-эндпоинт всё равно отдаёт 404 остальным (инвариант скрытности из
// контракта), это лишь скрытие пункта меню.
export function AdminNav({ isSuperadmin, fullAccess }: Props) {
  return (
    <nav className="admin-nav">
      <NavLink to="/a/dashboard" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
        Дашборд
      </NavLink>
      {fullAccess && (
        <NavLink to="/a/users" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
          Пользователи
        </NavLink>
      )}
      <NavLink to="/a/manage-users" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
        Управление
      </NavLink>
      <NavLink to="/a/promo" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
        Промокоды
      </NavLink>
      <NavLink to="/a/tariffs" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
        Тарифы
      </NavLink>
      <NavLink to="/a/broadcast" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
        Рассылка
      </NavLink>
      <NavLink to="/a/stats" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
        Статистика
      </NavLink>
      {fullAccess && (
        <NavLink to="/a/graph" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
          Граф
        </NavLink>
      )}
      <NavLink to="/a/settings" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
        Настройки
      </NavLink>
      {isSuperadmin && (
        <NavLink to="/a/admins" className={({ isActive }) => `admin-nav-item${isActive ? ' active' : ''}`}>
          Админы
        </NavLink>
      )}
    </nav>
  )
}
