import React, { useState } from "react";
import { ShieldCheck, Mail, Lock, User, Briefcase, Factory, ArrowRight, CheckCircle2, AlertCircle } from "lucide-react";

interface Props {
  onNavigateToLogin: () => void;
  onNavigateToLanding: () => void;
}

export const RegisterPage: React.FC<Props> = ({ onNavigateToLogin, onNavigateToLanding }) => {
  const [submitted, setSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    fullName: "",
    workEmail: "",
    employeeId: "",
    department: "Quality Assurance",
    jobTitle: "Quality Engineer",
    requestedRole: "quality_engineer",
    facility: "Plant 01 - CNC Machining Center",
    password: "",
    confirmPassword: ""
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-xl px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-md border border-slate-200 rounded-2xl">
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

          <h2 className="text-center text-2xl font-extrabold text-slate-900 tracking-tight mb-2">
            Request Enterprise Platform Access
          </h2>
          <p className="text-center text-xs text-slate-500 font-medium max-w-md mx-auto mb-6">
            All user accounts require authorization by the Plant Quality Directorate.
          </p>
          {submitted ? (
            <div className="text-center py-6">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Access Request Submitted</h3>
              <p className="mt-3 text-sm text-slate-600 leading-relaxed max-w-md mx-auto">
                Your credentials for <span className="font-semibold text-slate-900">{formData.workEmail}</span> have been registered.
                An invitation email will be issued once approved by the Quality Administrator for <span className="font-semibold text-slate-900">{formData.facility}</span>.
              </p>

              <div className="mt-6 p-4 rounded-xl bg-slate-50 border border-slate-200 text-left text-xs space-y-1.5 text-slate-600">
                <div><span className="font-semibold text-slate-800">Employee ID:</span> {formData.employeeId || "EMP-7492"}</div>
                <div><span className="font-semibold text-slate-800">Assigned Department:</span> {formData.department}</div>
                <div><span className="font-semibold text-slate-800">Requested Role:</span> {formData.requestedRole === "quality_engineer" ? "Quality Engineer (Privileged)" : "Production Team (Operator/Supervisor)"}</div>
              </div>

              <div className="mt-8">
                <button
                  onClick={onNavigateToLogin}
                  className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-xs transition-all"
                >
                  Return to Sign In
                </button>
              </div>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Full Name</label>
                  <div className="mt-1 relative rounded-md shadow-2xs">
                    <input
                      name="fullName"
                      required
                      value={formData.fullName}
                      onChange={handleChange}
                      placeholder="e.g. Sarah Chen"
                      className="block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Work Email Address</label>
                  <div className="mt-1 relative rounded-md shadow-2xs">
                    <input
                      name="workEmail"
                      type="email"
                      required
                      value={formData.workEmail}
                      onChange={handleChange}
                      placeholder="name@company.com"
                      className="block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Employee ID</label>
                  <input
                    name="employeeId"
                    required
                    value={formData.employeeId}
                    onChange={handleChange}
                    placeholder="EMP-9021"
                    className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Department</label>
                  <select
                    name="department"
                    value={formData.department}
                    onChange={handleChange}
                    className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                  >
                    <option value="Quality Assurance">Quality Assurance (QA)</option>
                    <option value="Quality Control">Quality Control (QC)</option>
                    <option value="Precision Machining">Precision Machining</option>
                    <option value="Plant Maintenance">Plant Maintenance</option>
                    <option value="Operations Management">Operations Management</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Job Title</label>
                  <select
                    name="jobTitle"
                    value={formData.jobTitle}
                    onChange={handleChange}
                    className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                  >
                    <option value="Quality Engineer">Quality Engineer</option>
                    <option value="Quality Inspector">Quality Inspector</option>
                    <option value="Line Supervisor">Line Supervisor</option>
                    <option value="Machine Operator">Machine Operator</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Requested Role Group</label>
                  <select
                    name="requestedRole"
                    value={formData.requestedRole}
                    onChange={handleChange}
                    className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                  >
                    <option value="quality_engineer">Quality Engineer (Privileged Sign-off)</option>
                    <option value="operator">Production Team (Intake & Uploads)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Facility / Machining Cell</label>
                <input
                  name="facility"
                  required
                  value={formData.facility}
                  onChange={handleChange}
                  placeholder="Plant 01 - CNC Machining Line 4"
                  className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Password</label>
                  <input
                    name="password"
                    type="password"
                    required
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••••••"
                    className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Confirm Password</label>
                  <input
                    name="confirmPassword"
                    type="password"
                    required
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    placeholder="••••••••••••"
                    className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Governance Notice: </span>
                  Role selection indicates intent only. Quality Engineer approval and root cause confirmation rights are granted by the administrator post-verification.
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-xs transition-all cursor-pointer"
                >
                  Submit Access Request
                </button>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={onNavigateToLogin}
                  className="text-blue-600 hover:text-blue-800 font-semibold cursor-pointer"
                >
                  Already have an account? Sign In
                </button>
                <button
                  type="button"
                  onClick={onNavigateToLanding}
                  className="text-slate-500 hover:text-slate-700 font-medium cursor-pointer"
                >
                  Home
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
