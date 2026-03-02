import { useState } from "react";
import { format } from "date-fns";
import { Download } from "lucide-react";
import api from "../services/api";

export default function Reports() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [report, setReport] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generateReport = async () => {
    if (!startDate || !endDate) {
      alert("Please select both dates");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/attendance/report", {
        params: { start_date: startDate, end_date: endDate }
      });
      const records = res.data?.records || res.data?.logs || [];
      setReport(records);
    } catch (err) {
      console.error(err);
      setError("Failed to generate report. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const safeFormatTime = (timeStr) => {
    try {
      if (!timeStr) return "-";
      const d = timeStr.includes("T")
        ? new Date(timeStr)
        : new Date(`2000-01-01T${timeStr}`);
      return format(d, "hh:mm a");
    } catch {
      return timeStr || "-";
    }
  };

  const safeFormatDate = (dateStr) => {
    try {
      if (!dateStr) return "-";
      return format(new Date(dateStr), "MMM d, yyyy");
    } catch {
      return dateStr;
    }
  };

  const handleExportCSV = () => {
    if (report.length === 0) return;
    const headers = ["Employee", "Employee Code", "Date", "Check In", "Check Out", "Working Hours", "Method"];
    const rows = report.map((item) => [
      item.employee_name || "Unknown",
      item.employee_code || "",
      item.date || "",
      item.check_in_time || "",
      item.check_out_time || "",
      item.working_hours || "",
      (item.check_in_method || "").toLowerCase(),
    ]);
    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attendance-report-${startDate}-to-${endDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-slate-100">Attendance Reports</h1>

      {/* Filter Panel */}
      <div className="bg-white dark:bg-[#334155] p-6 rounded-lg shadow dark:shadow-slate-900/40 mb-6 border border-gray-100 dark:border-slate-600/60">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-slate-300">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="border border-gray-200 dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-200"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-slate-300">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="border border-gray-200 dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-200"
            />
          </div>
          <button
            onClick={generateReport}
            disabled={loading}
            className="bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate Report"}
          </button>
          {report.length > 0 && (
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-2 bg-green-600 dark:bg-green-700 text-white px-4 py-2 rounded hover:bg-green-700 dark:hover:bg-green-600"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Report Table */}
      {report.length > 0 && (
        <div className="bg-white dark:bg-[#334155] rounded-lg shadow dark:shadow-slate-900/40 overflow-hidden border border-gray-100 dark:border-slate-600/60">
          <div className="px-6 py-3 bg-gray-50 dark:bg-slate-700/50 border-b border-gray-200 dark:border-slate-600/60">
            <p className="text-sm text-gray-600 dark:text-slate-400">
              Total records: <span className="font-semibold text-gray-900 dark:text-slate-200">{report.length}</span>
              {" | "}
              {safeFormatDate(startDate)} — {safeFormatDate(endDate)}
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50 dark:bg-slate-700/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Employee</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Check In</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Check Out</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Hours</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Method</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-600/40">
                {report.map((item, idx) => (
                  <tr key={item.id || idx} className="hover:bg-gray-50 dark:hover:bg-slate-600/30">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900 dark:text-slate-100">
                        {item.employee_name || "Unknown"}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-slate-400">
                        {item.employee_code || ""}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-300">
                      {safeFormatDate(item.date)}
                    </td>
                    <td className="px-6 py-4 text-sm text-green-600 dark:text-green-400 font-medium">
                      {safeFormatTime(item.check_in_time)}
                    </td>
                    <td className="px-6 py-4 text-sm text-red-600 dark:text-red-400 font-medium">
                      {safeFormatTime(item.check_out_time)}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-800 dark:text-slate-200">
                      {item.working_hours ? `${item.working_hours} hrs` : "-"}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-300 capitalize">
                      {(item.check_in_method || "-").toLowerCase()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && report.length === 0 && startDate && endDate && !error && (
        <div className="bg-white dark:bg-[#334155] rounded-lg shadow dark:shadow-slate-900/40 p-8 text-center text-gray-500 dark:text-slate-400 border border-gray-100 dark:border-slate-600/60">
          No records found for the selected date range.
        </div>
      )}
    </div>
  );
}