import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, subDays, startOfWeek, endOfWeek } from 'date-fns';
import {
  Calendar,
  Clock,
  Camera,
  Fingerprint,
  Download,
  Filter
} from 'lucide-react';
import { attendanceApi } from '../services/api';

function Attendance() {
  const [dateRange, setDateRange] = useState('today');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const getDateRange = () => {
    const today = new Date();
    switch (dateRange) {
      case 'today':
        return { start: today, end: today };
      case 'yesterday':
        const yesterday = subDays(today, 1);
        return { start: yesterday, end: yesterday };
      case 'week':
        return { start: startOfWeek(today), end: endOfWeek(today) };
      case 'month':
        return { start: new Date(today.getFullYear(), today.getMonth(), 1), end: today };
      case 'custom':
        return {
          start: customStart ? new Date(customStart) : today,
          end: customEnd ? new Date(customEnd) : today
        };
      default:
        return { start: today, end: today };
    }
  };

  const { start, end } = getDateRange();

  const { data: attendance, isLoading, error } = useQuery({
    queryKey: ['attendance', 'report', dateRange, customStart, customEnd],
    queryFn: async () => {
      try {
        if (dateRange === 'today') {
          const res = await attendanceApi.getToday();
          return Array.isArray(res.data) ? res.data : (res.data?.logs || res.data?.records || []);
        }
        const res = await attendanceApi.getReport({
          start_date: format(start, 'yyyy-MM-dd'),
          end_date: format(end, 'yyyy-MM-dd')
        });
        return Array.isArray(res.data) ? res.data : (res.data?.records || res.data?.logs || []);
      } catch (err) {
        console.error('Error fetching attendance:', err);
        throw err;
      }
    },
    retry: 1
  });

  const handleExport = () => {
    if (!attendance || attendance.length === 0) return;
    const headers = ['Date', 'Employee Code', 'Name', 'Check In', 'Check Out', 'Method'];
    const rows = attendance.map(record => [
      record.date || '',
      record.employee_code || record.employee?.employee_code || '',
      record.employee_name || record.employee?.full_name || '',
      record.check_in_time || '',
      record.check_out_time || '',
      record.check_in_method || ''
    ]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance-${format(start, 'yyyy-MM-dd')}-to-${format(end, 'yyyy-MM-dd')}.csv`;
    a.click();
  };

  const getMethodIcon = (method) => {
    const m = (method || '').toLowerCase();
    if (m === 'face') return <Camera className="w-4 h-4" />;
    if (m === 'fingerprint') return <Fingerprint className="w-4 h-4" />;
    return null;
  };

  const safeFormatDate = (dateStr) => {
    try {
      if (!dateStr) return '-';
      return format(new Date(dateStr), 'MMM d, yyyy');
    } catch {
      return dateStr;
    }
  };

  const safeFormatTime = (timeStr) => {
    try {
      if (!timeStr) return '--:--';
      const date = timeStr.includes('T')
        ? new Date(timeStr)
        : new Date(`2000-01-01T${timeStr}`);
      return format(date, 'hh:mm a');
    } catch {
      return timeStr || '--:--';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Attendance</h1>
          <p className="text-gray-500 dark:text-slate-400 mt-1">
            {dateRange === 'today'
              ? "Today's attendance records"
              : `${format(start, 'MMM d, yyyy')} - ${format(end, 'MMM d, yyyy')}`
            }
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={!attendance || attendance.length === 0}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-[#334155] border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600/40 disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-[#334155] rounded-xl shadow-sm border border-gray-100 dark:border-slate-600/60 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400 dark:text-slate-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">Date Range:</span>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              { value: 'today', label: 'Today' },
              { value: 'yesterday', label: 'Yesterday' },
              { value: 'week', label: 'This Week' },
              { value: 'month', label: 'This Month' },
              { value: 'custom', label: 'Custom' }
            ].map(option => (
              <button
                key={option.value}
                onClick={() => setDateRange(option.value)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${dateRange === option.value
                    ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
                    : 'bg-gray-100 dark:bg-slate-600/60 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-600'
                  }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {dateRange === 'custom' && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="px-3 py-1.5 border border-gray-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-200"
              />
              <span className="text-gray-400 dark:text-slate-500">to</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="px-3 py-1.5 border border-gray-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-200"
              />
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
          Error loading attendance: {error.message || 'Unknown error'}
        </div>
      )}

      {/* Attendance Table */}
      <div className="bg-white dark:bg-[#334155] rounded-xl shadow-sm border border-gray-100 dark:border-slate-600/60 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700/50 border-b border-gray-100 dark:border-slate-600/60">
              <tr>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Employee</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Date</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Check In</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Check Out</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Method</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Working Hours</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-600/40">
              {isLoading ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500 dark:text-slate-400">Loading...</td>
                </tr>
              ) : !attendance || attendance.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500 dark:text-slate-400">No attendance records found</td>
                </tr>
              ) : (
                attendance.map((record, index) => (
                  <tr key={record.id || index} className="hover:bg-gray-50 dark:hover:bg-slate-600/30">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/40 text-primary-600 dark:text-primary-400 rounded-full flex items-center justify-center font-medium text-sm">
                          {(record.employee_name || record.employee?.full_name || '?')[0]}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-slate-100">
                            {record.employee_name || record.employee?.full_name || 'Unknown'}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-slate-400">
                            {record.employee_code || record.employee?.employee_code || ''}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-gray-600 dark:text-slate-300">
                        <Calendar className="w-4 h-4 text-gray-400 dark:text-slate-500" />
                        {safeFormatDate(record.date)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-green-600 dark:text-green-400 font-medium">
                        <Clock className="w-4 h-4" />
                        {safeFormatTime(record.check_in_time)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className={`flex items-center gap-2 font-medium ${record.check_out_time ? 'text-red-600 dark:text-red-400' : 'text-gray-400 dark:text-slate-500'}`}>
                        <Clock className="w-4 h-4" />
                        {safeFormatTime(record.check_out_time)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className={`p-1.5 rounded ${(record.check_in_method || '').toUpperCase() === 'FACE'
                            ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400'
                            : 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400'
                          }`}>
                          {getMethodIcon(record.check_in_method)}
                        </span>
                        <span className="text-sm text-gray-600 dark:text-slate-300 capitalize">
                          {(record.check_in_method || '-').toLowerCase()}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-700 dark:text-slate-300 font-medium">
                        {record.working_hours || '-'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Summary */}
        {attendance && attendance.length > 0 && (
          <div className="px-6 py-4 border-t border-gray-100 dark:border-slate-600/60 bg-gray-50 dark:bg-slate-700/40">
            <p className="text-sm text-gray-600 dark:text-slate-400">
              Total records: <span className="font-medium text-gray-900 dark:text-slate-200">{attendance.length}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Attendance;