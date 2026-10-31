"use client";

import { useState } from "react";

const REDIRECT_URL = "https://youtube.com/shorts/f1CN-axX-KQ?si=WerLTl8myMbLRFgH";

export default function AdminFakeLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // No real authentication – simply redirect after "login"
    window.location.replace(REDIRECT_URL);
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white/80 backdrop-blur-sm rounded-xl shadow-md p-6 space-y-5">
        <h2 className="text-2xl font-semibold text-center text-gray-800">Admin Login</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-md transition-colors"
          >
            Sign in
          </button>
        </form>
        <p className="text-xs text-center text-gray-500">
          This is a placeholder login. After submitting you will be redirected.
        </p>
      </div>
    </div>
  );
}

