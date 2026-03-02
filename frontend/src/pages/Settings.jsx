import { useState } from "react";
import { useAuthStore } from "../store/authStore";
import api from "../services/api";

export default function Settings() {
  const { user } = useAuthStore();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await api.post("/admin/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMessage("Password changed successfully");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setMessage(err.response?.data?.detail || "Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    "w-full border border-gray-200 dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-200 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 outline-none";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-slate-100">Settings</h1>

      {/* Change Password Card */}
      <div className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40 max-w-md border border-gray-100 dark:border-slate-600/60">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-slate-100">Change Password</h2>

        {message && (
          <div
            className={`p-3 rounded mb-4 text-sm ${message.includes("success")
                ? "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300"
                : "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300"
              }`}
          >
            {message}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-slate-300">
              Current Password
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className={inputClass}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-slate-300">
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className={inputClass}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-slate-300">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={inputClass}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 dark:bg-blue-700 text-white py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 font-medium"
          >
            {loading ? "Changing..." : "Change Password"}
          </button>
        </form>
      </div>

      {/* Account Info Card */}
      <div className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40 max-w-md mt-6 border border-gray-100 dark:border-slate-600/60">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-slate-100">Account Info</h2>
        <div className="space-y-2 text-sm text-gray-700 dark:text-slate-300">
          <p><strong className="text-gray-900 dark:text-slate-100">Username:</strong> {user?.username}</p>
          <p><strong className="text-gray-900 dark:text-slate-100">Email:</strong> {user?.email}</p>
          <p><strong className="text-gray-900 dark:text-slate-100">Role:</strong> {user?.role}</p>
        </div>
      </div>
    </div>
  );
}