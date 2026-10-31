"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, Shield, LogOut, ChevronDown, Clock, Zap, CheckCircle2 } from "lucide-react";
import { User, UserQuota } from "@/types";
import AuthModal from "./AuthModal";

export default function UserQuotaBadge() {
  const [user, setUser] = useState<User | null>(null);
  const [quota, setQuota] = useState<UserQuota | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  async function fetchUserStatus() {
    try {
      const res = await fetch("/api/auth/me");
      const data = await res.json();
      if (data.authenticated) {
        setUser(data.user);
        setQuota(data.quota);
      } else {
        setUser(null);
        setQuota(data.quota);
      }
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    fetchUserStatus();
    // Refresh quota every 30s
    const timer = setInterval(fetchUserStatus, 30000);
    return () => clearInterval(timer);
  }, []);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    setUser(null);
    setQuota(null);
    setDropdownOpen(false);
    fetchUserStatus();
  }

  if (!user) {
    return (
      <>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setModalOpen(true)}
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors px-2 py-1"
          >
            Log in
          </button>
          <button
            onClick={() => setModalOpen(true)}
            className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-95 text-white text-xs font-semibold transition-all shadow-sm flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            30-Day Trial
          </button>
        </div>
        <AuthModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          onSuccess={(u, q) => {
            setUser(u);
            setQuota(q);
          }}
        />
      </>
    );
  }

  const isPremiumActive = quota?.is_trial_active && quota?.current_engine === "premium";

  return (
    <div className="relative">
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 transition-all text-xs shadow-sm"
      >
        <span
          className={`w-2 h-2 rounded-full ${
            isPremiumActive ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
          }`}
        />
        <div className="flex flex-col text-left">
          <span className="font-semibold text-gray-900 leading-tight flex items-center gap-1">
            {isPremiumActive ? (
              <>
                <Zap className="w-3 h-3 text-indigo-600" />
                Premium Trial
              </>
            ) : (
              "Free Tier"
            )}
          </span>
          <span className="text-[10px] text-gray-500 leading-tight">
            {isPremiumActive
              ? `${quota?.premium_daily_chars_left.toLocaleString()} chars left today`
              : "Edge TTS Active"}
          </span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-gray-400 ml-0.5" />
      </button>

      {dropdownOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-2xl shadow-xl border border-gray-100 p-4 z-50 text-xs text-gray-700 animate-in fade-in duration-150">
          <div className="border-b border-gray-100 pb-3 mb-3">
            <div className="text-[11px] text-gray-400">Signed in as</div>
            <div className="font-semibold text-gray-900 truncate">{user.email}</div>
          </div>

          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-gray-600">
                <Clock className="w-3.5 h-3.5 text-indigo-500" />
                Trial Days Remaining
              </span>
              <span className="font-bold text-gray-900">
                {quota?.days_left ?? 0} days
              </span>
            </div>

            <div className="bg-slate-50 p-2.5 rounded-xl space-y-1.5 border border-slate-100">
              <div className="flex justify-between font-medium">
                <span className="text-gray-500">Today's Premium Quota</span>
                <span className="text-indigo-600 font-semibold">
                  {quota?.premium_daily_chars_left ?? 0} / 1,000
                </span>
              </div>
              <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-indigo-600 h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(
                      100,
                      ((quota?.premium_daily_chars_left ?? 0) / 1000) * 100
                    )}%`,
                  }}
                />
              </div>

              <div className="flex justify-between font-medium pt-1">
                <span className="text-gray-500">Total Trial Quota</span>
                <span className="text-purple-600 font-semibold">
                  {quota?.premium_total_chars_left ?? 0} / 10,000
                </span>
              </div>
              <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-purple-600 h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(
                      100,
                      ((quota?.premium_total_chars_left ?? 0) / 10000) * 100
                    )}%`,
                  }}
                />
              </div>
            </div>

            <div className="text-[11px] text-gray-500 leading-snug pt-1">
              ✨ Once daily or trial quota ends, generations smoothly switch to free high-quality voices automatically.
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full mt-3 pt-2.5 border-t border-gray-100 flex items-center justify-center gap-1.5 text-red-600 font-medium hover:text-red-700 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
