import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import api from "../services/api";

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalEmployees: 0,
    presentToday: 0,
    absentToday: 0,
    activeDevices: 0,
  });
  const [todayAttendance, setTodayAttendance] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const empRes = await api.get("/employees");
      const totalEmployees = empRes.data.total || (empRes.data.items ? empRes.data.items.length : 0);

      const attRes = await api.get("/attendance/today");
      const attData = attRes.data;
      const attendance = attData.logs || [];

      let activeDevices = 0;
      try {
        const devRes = await api.get("/devices");
        const devices = Array.isArray(devRes.data) ? devRes.data : devRes.data.devices || [];
        activeDevices = devices.filter(d => d.is_active).length;
      } catch (e) {
        console.log("Could not fetch devices");
      }

      setTodayAttendance(attendance);
      setStats({
        totalEmployees: attData.total_employees || totalEmployees,
        presentToday: attData.checked_in || attendance.length,
        absentToday: attData.absent || Math.max(0, totalEmployees - attendance.length),
        activeDevices: activeDevices,
      });
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-slate-400">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-slate-100">Dashboard</h1>

      {/* ── Stat Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40">
          <h3 className="text-gray-500 dark:text-slate-400 text-sm font-medium">Total Employees</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-slate-100 mt-1">{stats.totalEmployees}</p>
        </div>
        <div className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40">
          <h3 className="text-gray-500 dark:text-slate-400 text-sm font-medium">Present Today</h3>
          <p className="text-3xl font-bold text-green-600 dark:text-green-400 mt-1">{stats.presentToday}</p>
        </div>
        <div className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40">
          <h3 className="text-gray-500 dark:text-slate-400 text-sm font-medium">Absent Today</h3>
          <p className="text-3xl font-bold text-red-600 dark:text-red-400 mt-1">{stats.absentToday}</p>
        </div>
        <div className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40">
          <h3 className="text-gray-500 dark:text-slate-400 text-sm font-medium">Active Devices</h3>
          <p className="text-3xl font-bold text-blue-600 dark:text-blue-400 mt-1">{stats.activeDevices}</p>
        </div>
      </div>

      {/* ── Quick Actions ───────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Link
          to="/employees"
          className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40 hover:shadow-md dark:hover:shadow-slate-900/60 transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-slate-100">Manage Employees</h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">Add or edit employee records</p>
        </Link>
        <Link
          to="/attendance"
          className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40 hover:shadow-md dark:hover:shadow-slate-900/60 transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-slate-100">View Attendance</h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">Check attendance records</p>
        </Link>
        <Link
          to="/devices"
          className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40 hover:shadow-md dark:hover:shadow-slate-900/60 transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-slate-100">Manage Devices</h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">Configure biometric devices</p>
        </Link>
      </div>

      {/* ── Today's Attendance Table ────────────────────────── */}
      <div className="bg-white dark:bg-[#334155] rounded-lg shadow dark:shadow-slate-900/40">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-600/60">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">Today's Attendance</h2>
        </div>
        <div className="p-6">
          {todayAttendance.length === 0 ? (
            <p className="text-gray-500 dark:text-slate-400 text-center py-4">No attendance records for today</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-slate-600/60">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-500 dark:text-slate-400">Employee</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-500 dark:text-slate-400">Check In</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-500 dark:text-slate-400">Check Out</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-500 dark:text-slate-400">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {todayAttendance.slice(0, 10).map((record, index) => (
                    <tr key={record.id || index} className="border-b border-gray-100 dark:border-slate-600/40 last:border-0 hover:bg-gray-50 dark:hover:bg-slate-600/30">
                      <td className="py-3 px-4">
                        <div className="font-medium text-gray-900 dark:text-slate-100">{record.employee_name || record.employee?.full_name || "N/A"}</div>
                        <div className="text-sm text-gray-500 dark:text-slate-400">{record.employee_code || record.employee?.employee_code || ""}</div>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-700 dark:text-slate-300">
                        {record.check_in_time ? format(new Date(record.check_in_time), "hh:mm a") : "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-700 dark:text-slate-300">
                        {record.check_out_time ? format(new Date(record.check_out_time), "hh:mm a") : "-"}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 text-xs rounded-full ${record.check_out_time
                            ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
                            : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300"
                          }`}>
                          {record.check_out_time ? "Complete" : "Working"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}