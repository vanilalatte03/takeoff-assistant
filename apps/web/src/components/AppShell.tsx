import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/workflow", label: "작업 시작·이어서 하기" },
  { to: "/assist", label: "산출 탐색 보조" },
  { to: "/upload", label: "PDF 업로드" },
  { to: "/drawings", label: "도면 목록/검색" },
  { to: "/room-finishes", label: "실별 마감표" },
  { to: "/measurements", label: "산출 내역" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="주요 메뉴">
        <div className="brand">
          <span className="brand-mark">TA</span>
          <div>
            <strong>Takeoff Assistant</strong>
            <span>MVP</span>
          </div>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "active" : undefined)}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
