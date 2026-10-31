import Link from "next/link";
import { BookOpen, ArrowLeft } from "lucide-react";

export default function TermsPage() {
  return (
    <div className="relative overflow-hidden min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
      {/* Background Gradient Mesh */}
      <div className="gradient-mesh absolute inset-0 -z-10" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full bg-gradient-to-br from-indigo-400/20 via-purple-400/15 to-pink-400/10 blur-[100px] -z-10 pointer-events-none" />

      <div className="max-w-xl w-full p-8 md:p-10 rounded-3xl bg-white/70 backdrop-blur-xl border border-white/80 shadow-xl shadow-purple-500/5 space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/10 via-purple-500/10 to-pink-500/10 border border-purple-200/50 flex items-center justify-center mx-auto text-purple-600 shadow-sm">
          <BookOpen className="w-8 h-8" />
        </div>

        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-50 border border-purple-200/60 text-purple-700 text-xs font-semibold uppercase tracking-wider">
            Legal & Ethics
          </div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            Terms of <span className="gradient-text">Use</span>
          </h1>
          <p className="text-sm text-gray-500 leading-relaxed">
            Ethical voice generation policy, licensing terms, and platform compliance guidelines.
          </p>
        </div>

        <div className="text-xs text-gray-600 space-y-3 bg-white/60 border border-gray-100 rounded-2xl p-5 leading-relaxed">
          <p>
            <strong>1. Consented Voices Only:</strong> All voices hosted on AwaazAI are trained exclusively with verified contractual consent from voice actors.
          </p>
          <p>
            <strong>2. Prohibited Use:</strong> Impersonation, unauthorized synthetic deepfakes, harassment, fraud, and unlawful robocalls are strictly prohibited.
          </p>
          <p>
            <strong>3. Synthetic Audio Watermarking:</strong> Generated files embed automated AI disclosure headers and metadata in compliance with Indian synthetic media regulations.
          </p>
        </div>

        <div className="pt-2 text-center">
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold shadow-md transition-all active:scale-95"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
