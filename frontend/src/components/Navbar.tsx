import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
const NAV_ITEMS = [
  { label: "홈", path: "/" },
  { label: "채팅", path: "/chat" },
  { label: "지도", path: "/map" },
];
const baseLink =
  "px-3 py-2 text-sm font-semibold rounded-lg transition-colors duration-150";
export default function Navbar() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  const renderLink = (path: string, label: string, isMobile?: boolean) => {
    const isActive = location.pathname === path;
    const activeStyles = isActive
      ? "bg-green-600 text-white shadow-sm"
      : "text-green-700 hover:bg-green-50";
    const size = isMobile ? "text-base" : "text-sm";
    return (
      <Link
        key={path}
        to={path}
        className={`${baseLink} ${activeStyles} ${size}`}
      >
        {label}
      </Link>
    );
  };
  return (
    <>
      {/* 태블릿 / 데스크탑용 상단 네비게이션 */}
      <nav className="sticky top-2 z-30 mx-auto hidden w-4/5 md:block">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between rounded-2xl border border-green-100 bg-white/80 px-4 shadow-sm backdrop-blur">
          <Link
            to="/"
            className="flex items-center gap-2 text-lg font-bold text-green-700"
          >
            <img src="/logo.svg" alt="로고" className=" w-12 h-12 object-cover" style={{clipPath: "circle(50% at 50% 50%)"}}/>
            <h2 className="text-2xl font-gowun">AIGO</h2>
          </Link>
          <div className="flex items-center gap-2">
            {NAV_ITEMS.map((item) => renderLink(item.path, item.label))}
          </div>
        </div>
      </nav>
      {/* 모바일용 상단바 (AIGO 왼쪽 + 햄버거 오른쪽) - 홈, /chat, /map 에서만 */}
      {(location.pathname === "/" ||
        location.pathname === "/chat" ||
        location.pathname === "/map") && (
        <div className="mt-4 mb-3 flex justify-center md:hidden">
          <div className="w-full max-w-6xl flex items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <img
                src="/logo.svg"
                alt="AIGO 로고"
                className="w-14 h-14 object-cover"
                style={{ clipPath: "circle(50% at 50% 50%)" }}
              />
              <div className="text-lg text-green-700 font-gowun font-extrabold">
                AIGO
              </div>
            </div>
            <button
              aria-label="메뉴 열기"
              className="hover:cursor-pointer flex h-10 w-10 flex-col items-center justify-center gap-1 rounded-xl border border-green-100 bg-white text-[#c5572f] shadow-sm transition hover:border-green-200 hover:shadow"
              onClick={() => setOpen((prev) => !prev)}
            >
              <span
                className={`h-[2px] w-6 rounded-full bg-current transition-transform duration-200 ${
                  open ? "translate-y-1.5 rotate-45" : "-translate-y-1.5"
                }`}
              />
              <span
                className={`h-[2px] w-6 rounded-full bg-current transition-opacity duration-150 ${
                  open ? "opacity-0" : "opacity-100"
                }`}
              />
              <span
                className={`h-[2px] w-6 rounded-full bg-current transition-transform duration-200 ${
                  open ? "-translate-y-1.5 -rotate-45" : "translate-y-1.5"
                }`}
              />
            </button>
          </div>
        </div>
      )}
      {(location.pathname === "/" ||
        location.pathname === "/chat" ||
        location.pathname === "/map") && (
        <div
          className={`fixed inset-0 z-40 transform transition duration-300 ${
            open ? "pointer-events-auto" : "pointer-events-none"
          } md:hidden`}
          aria-hidden={!open}
        >
          <div
            className={`absolute inset-0 bg-black/20 transition-opacity ${
              open ? "opacity-100" : "opacity-0"
            }`}
            onClick={() => setOpen(false)}
          />
          <div
            className={`absolute left-0 top-0 h-full w-64 bg-white shadow-2xl transition-transform duration-300 ${
              open ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <div className="flex items-center justify-center px-5 py-4 border-b border-green-50">
              <div className="flex  items-center gap-2 text-lg font-bold text-green-700">
                <img
                  src="/logo.svg"
                  alt="AIGO 로고"
                  className="w-16 h-16 object-cover"
                  style={{ clipPath: "circle(50% at 50% 50%)" }}
                />
                {/* <span className="text-[#e79f85] font-bold">AIGO 챗봇</span> */}
              </div>
            </div>
            <div className="flex flex-col gap-2 px-5 py-4">
              {NAV_ITEMS.map((item) => renderLink(item.path, item.label, true))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
