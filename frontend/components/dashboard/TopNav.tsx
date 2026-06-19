"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Search, Menu, LogOut, User as UserIcon } from "lucide-react";
import { NotificationBell } from "@/components/notifications/NotificationCenter";

interface TopNavProps {
  user: { name: string; email: string; role: string } | null;
  onLogout: () => void;
  onToggleSidebar: () => void;
}

export function TopNav({ user, onLogout, onToggleSidebar }: TopNavProps) {
  const [showProfile, setShowProfile] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, right: 16 });
  const profileButtonRef = useRef<HTMLButtonElement>(null);

  const updateMenuPosition = useCallback(() => {
    const el = profileButtonRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setMenuPos({
      top: rect.bottom + 8,
      right: Math.max(8, window.innerWidth - rect.right),
    });
  }, []);

  useEffect(() => {
    if (!showProfile) return;
    updateMenuPosition();
    const onResize = () => updateMenuPosition();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
    };
  }, [showProfile, updateMenuPosition]);

  useEffect(() => {
    if (!showProfile) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowProfile(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [showProfile]);

  const handleLogout = useCallback(() => {
    setShowProfile(false);
    onLogout();
  }, [onLogout]);

  const profileMenu =
    showProfile && typeof document !== "undefined"
      ? createPortal(
          <>
            <div
              className="fixed inset-0 z-[200]"
              aria-hidden
              onClick={() => setShowProfile(false)}
            />
            <div
              role="menu"
              className="fixed z-[201] w-56 bg-white rounded-xl shadow-lg border border-gray-200 py-2"
              style={{ top: menuPos.top, right: menuPos.right }}
            >
              <div className="px-4 py-2 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <button
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          </>,
          document.body,
        )
      : null;

  return (
    <header className="relative z-50 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 lg:px-6 flex-shrink-0">
      <div className="flex items-center gap-4">
        <button onClick={onToggleSidebar} className="lg:hidden p-2 hover:bg-gray-100 rounded-lg">
          <Menu className="w-5 h-5 text-gray-600" />
        </button>
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search contracts, clauses..."
            className="input pl-10 w-64 lg:w-80"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <NotificationBell />

        <div className="relative">
          <button
            ref={profileButtonRef}
            type="button"
            aria-expanded={showProfile}
            aria-haspopup="menu"
            onClick={() => {
              if (!showProfile) updateMenuPosition();
              setShowProfile((open) => !open);
            }}
            className="flex items-center gap-2 p-1.5 hover:bg-gray-100 rounded-lg"
          >
            <div className="w-8 h-8 bg-navy-900 rounded-full flex items-center justify-center">
              <UserIcon className="w-4 h-4 text-gold-400" />
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-gray-900">{user?.name || "User"}</p>
              <p className="text-xs text-gray-500 capitalize">
                {user?.role ? (
                  user.role === "viewer" ? "Read-only" :
                  user.role === "tenant_admin" ? "Admin" :
                  user.role === "legal_reviewer" ? "Legal" :
                  user.role.replace(/_/g, " ")
                ) : "Viewer"}
              </p>
            </div>
          </button>
        </div>
      </div>

      {profileMenu}
    </header>
  );
}
