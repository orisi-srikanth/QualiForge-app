import React, { useState } from "react";
import { Lock, Mail, ArrowRight, ShieldCheck, AlertCircle, Loader2, UserCheck, Factory } from "lucide-react";
import { api } from "../api";

interface Props {
  onSuccess: (role: "quality_engineer" | "operator" | "admin") => void;
  onNavigateToRegister: () => void;
  onNavigateToLanding: () => void;
  initialRole?: "quality_engineer" | "operator";
}

export const LoginPage: React.FC<Props> = ({
  onSuccess,
  onNavigateToRegister,
  onNavigateToLanding,
  initialRole = "quality_engineer"
}) => {
  const [email, setEmail] = useState(
    initialRole === "operator" ? "operator@precisionaero.com" : "engineer@precisionaero.com"
  );
  const [password, setPassword] = useState("IndustrialQuality2026!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await api.login(email, password);
      const role = (res?.role as "quality_engineer" | "operator" | "admin") || "quality_engineer";
      onSuccess(role);
    } catch (err: any) {
      setError(err?.message || "Failed to authenticate. Please check credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPersona = (selectedEmail: string, role: "quality_engineer" | "operator" | "admin") => {
    setEmail(selectedEmail);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-md border border-slate-200 rounded-2xl">
          {/* Logo integrated directly inside the main card */}
          <button
            onClick={onNavigateToLanding}
            className="w-full flex items-center justify-center group cursor-pointer focus:outline-none mb-4"
            title="Return to QualiForge Home"
          >
            <img
              src="/logo.png"
              alt="QualiForge Logo"
              className="h-16 sm:h-20 w-auto object-contain transition-transform duration-300 group-hover:scale-105 drop-shadow-[0_2px_8px_rgba(37,99,235,0.18)]"
            />
          </button>

          <h2 className="text-center text-2xl font-extrabold text-slate-900 tracking-tight mb-6">
            Sign In to Quality Intelligence
          </h2>
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-rose-800 text-xs">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Authentication Error: </span>
                {error}
              </div>
            </div>
          )}

          {/* Quick Select Persona Bar */}
          <div className="mb-6 pb-6 border-b border-slate-100">
            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
              Select Enterprise Persona
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleSelectPersona("engineer@precisionaero.com", "quality_engineer")}
                className={`px-3 py-2.5 rounded-lg border text-left text-xs transition-all ${
                  email === "engineer@precisionaero.com"
                    ? "border-blue-600 bg-blue-50/60 text-blue-900 font-semibold shadow-2xs"
                    : "border-slate-200 hover:border-slate-300 text-slate-700"
                }`}
              >
                <div className="flex items-center gap-1.5 font-bold">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                  Quality Engineer
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5 truncate">Sarah Chen</div>
              </button>

              <button
                type="button"
                onClick={() => handleSelectPersona("operator@precisionaero.com", "operator")}
                className={`px-3 py-2.5 rounded-lg border text-left text-xs transition-all ${
                  email === "operator@precisionaero.com"
                    ? "border-blue-600 bg-blue-50/60 text-blue-900 font-semibold shadow-2xs"
                    : "border-slate-200 hover:border-slate-300 text-slate-700"
                }`}
              >
                <div className="flex items-center gap-1.5 font-bold">
                  <Factory className="w-3.5 h-3.5 text-slate-600" />
                  Production Team
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5 truncate">Line Operator</div>
              </button>
            </div>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-700">
                Work Email Address
              </label>
              <div className="mt-1.5 relative rounded-md shadow-2xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-9 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-slate-900 placeholder-slate-400 font-mono"
                  placeholder="engineer@precisionaero.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-700">
                Password
              </label>
              <div className="mt-1.5 relative rounded-md shadow-2xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-9 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-slate-900 placeholder-slate-400 font-mono"
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  defaultChecked
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-slate-600">
                  Remember session
                </label>
              </div>

              <span className="text-slate-400 font-medium">Enterprise SSO Ready</span>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-xs text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-all cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Authenticating...
                  </>
                ) : (
                  <>
                    Sign In <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-100 flex items-center justify-between text-xs">
            <button
              onClick={onNavigateToRegister}
              className="text-blue-600 hover:text-blue-800 font-semibold cursor-pointer"
            >
              Request New Account
            </button>
            <button
              onClick={onNavigateToLanding}
              className="text-slate-500 hover:text-slate-700 font-medium cursor-pointer"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
