"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Mic, Radio, Users, Sliders, Shield, BookOpen, Menu, X } from "lucide-react";
import { useState } from "react";
import UserQuotaBadge from "./UserQuotaBadge";

const NAV_ITEMS = [
  { name: "Voices", href: "/voices", icon: Radio },
  { name: "Studio", href: "/studio", icon: Mic },
  { name: "Conversation Studio", href: "/conversation", icon: Users },
  { name: "Compare", href: "/compare", icon: Sliders },
  { name: "Admin", href: "/admin", icon: Shield },
  { name: "Terms of Use", href: "/terms", icon: BookOpen },
];

export default function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2 shrink-0 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-md shadow-purple-500/30">
              <Mic className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-gray-900 text-base tracking-tight group-hover:text-gray-700 transition-colors">
              AwaazAI
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-gray-100 text-gray-900"
                      : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
                  }`}
                >
                  {item.name}
                </Link>
              );
            })}
          </div>

          {/* CTA & User Trial Quota */}
          <div className="hidden md:flex items-center gap-3">
            <UserQuotaBadge />
          </div>

          {/* Mobile hamburger */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-4 pt-2 pb-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-gray-100 text-gray-900"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <item.icon className="w-4 h-4 text-gray-400" />
                {item.name}
              </Link>
            );
          })}
          <div className="pt-2 flex flex-col gap-2">
            <Link
              href="/studio"
              className="w-full text-center px-4 py-2.5 rounded-xl bg-gray-900 text-white text-sm font-semibold"
            >
              Get started
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
