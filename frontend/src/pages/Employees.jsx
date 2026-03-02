import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus, Search, MoreVertical, Edit2, Trash2, Fingerprint,
  Camera, CheckCircle, XCircle, Clock, Users, RefreshCw
} from 'lucide-react';
import toast from 'react-hot-toast';
import { employeeApi } from '../services/api';
import EmployeeModal from '../components/EmployeeModal';

const STATUS_CONFIG = {
  ACTIVE: {
    label: 'Active',
    icon: CheckCircle,
    className: 'text-emerald-600 bg-emerald-50 border-emerald-100'
  },
  INACTIVE: {
    label: 'Inactive',
    icon: XCircle,
    className: 'text-red-500 bg-red-50 border-red-100'
  },
  ON_LEAVE: {
    label: 'On Leave',
    icon: Clock,
    className: 'text-amber-600 bg-amber-50 border-amber-100'
  },
};

const AVATAR_COLORS = [
  'from-blue-400 to-blue-600',
  'from-violet-400 to-violet-600',
  'from-emerald-400 to-emerald-600',
  'from-rose-400 to-rose-600',
  'from-amber-400 to-amber-600',
  'from-cyan-400 to-cyan-600',
];

function getAvatarColor(name = '') {
  const idx = name.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.INACTIVE;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${config.className}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.label}
    </span>
  );
}

function Employees() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [menuOpen, setMenuOpen] = useState(null);

  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const limit = 10;

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ['employees', page, search],
    queryFn: async () => {
      const res = await employeeApi.getAll({ skip: (page - 1) * limit, limit, search: search || undefined });
      return res.data;
    },
  });

  const employees = data?.items || data?.employees || (Array.isArray(data) ? data : []);
  const totalCount = data?.total || employees.length;
  const totalPages = Math.ceil(totalCount / limit);

  const deleteMutation = useMutation({
    mutationFn: (id) => employeeApi.delete(id),
    onSuccess: () => { queryClient.invalidateQueries(['employees']); toast.success('Employee deleted'); },
    onError: () => toast.error('Failed to delete employee'),
  });

  const handleDelete = (employee) => {
    if (window.confirm(`Delete ${employee.full_name}? This cannot be undone.`)) {
      deleteMutation.mutate(employee.id);
    }
    setMenuOpen(null);
  };

  const handleEdit = (employee) => {
    setEditingEmployee(employee);
    setModalOpen(true);
    setMenuOpen(null);
  };

  const openAdd = () => {
    setEditingEmployee(null);
    setModalOpen(true);
  };

  // close menu when clicking outside
  const handleTableClick = () => { if (menuOpen) setMenuOpen(null); };

  return (
    <div className="space-y-5" onClick={handleTableClick}>

      {/* ── Page Header ─────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <Users className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Employees</h1>
            <p className="text-sm text-gray-500">
              {isLoading ? 'Loading...' : `${totalCount} total`}
              {isFetching && !isLoading && (
                <RefreshCw className="inline w-3 h-3 ml-1.5 animate-spin text-blue-500" />
              )}
            </p>
          </div>
        </div>

        <button
          onClick={openAdd}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition-all duration-150"
        >
          <Plus className="w-4 h-4" />
          Add Employee
        </button>
      </div>

      {/* ── Search ──────────────────────────────────── */}
      <div className="relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search by name, email, or employee code…"
          className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-all"
        />
      </div>

      {/* ── Error ───────────────────────────────────── */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          Failed to load employees: {error.message}
        </div>
      )}

      {/* ── Table ───────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/80">
              <th className="px-6 py-3.5 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Employee</th>
              <th className="px-6 py-3.5 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Department</th>
              <th className="px-6 py-3.5 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Biometrics</th>
              <th className="px-6 py-3.5 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3.5 text-right text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-50">
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-gray-100 animate-pulse" />
                      <div className="space-y-2">
                        <div className="w-32 h-3 bg-gray-100 rounded animate-pulse" />
                        <div className="w-20 h-2.5 bg-gray-100 rounded animate-pulse" />
                      </div>
                    </div>
                  </td>
                  {[...Array(4)].map((_, j) => (
                    <td key={j} className="px-6 py-4">
                      <div className="w-24 h-3 bg-gray-100 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : employees.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-6 py-16 text-center">
                  <Users className="w-10 h-10 mx-auto text-gray-200 mb-3" />
                  <p className="text-sm text-gray-400 font-medium">No employees found</p>
                  <p className="text-xs text-gray-300 mt-1">Try a different search or add a new employee</p>
                </td>
              </tr>
            ) : (
              employees.map((employee) => {
                const avatarColor = getAvatarColor(employee.full_name);
                return (
                  <tr
                    key={employee.id}
                    className="hover:bg-blue-50/40 transition-colors group"
                  >
                    {/* Employee */}
                    <td className="px-6 py-4">
                      <Link to={`/employees/${employee.id}`} className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${avatarColor} flex items-center justify-center text-white text-sm font-bold shadow-sm flex-shrink-0`}>
                          {(employee.full_name || '?').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-800 group-hover:text-blue-600 transition-colors">
                            {employee.full_name}
                          </p>
                          <p className="text-xs text-gray-400 mt-0.5 font-mono">
                            {employee.employee_code}
                          </p>
                        </div>
                      </Link>
                    </td>

                    {/* Department */}
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-gray-700">{employee.department || '—'}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{employee.designation || '—'}</p>
                    </td>

                    {/* Biometrics */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => navigate(`/employees/${employee.id}/face-enroll`)}
                          disabled={employee.has_face_template}
                          title={employee.has_face_template ? 'Face enrolled ✓' : 'Enroll face'}
                          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                            employee.has_face_template
                              ? 'bg-emerald-50 text-emerald-600 border-emerald-100 cursor-default'
                              : 'bg-white text-gray-500 border-gray-200 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200'
                          }`}
                        >
                          <Camera className="w-3.5 h-3.5" />
                          {employee.has_face_template ? 'Enrolled' : 'Face'}
                        </button>

                        <button
                          disabled
                          title="Fingerprint not yet available"
                          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border bg-gray-50 text-gray-300 border-gray-100 cursor-not-allowed"
                        >
                          <Fingerprint className="w-3.5 h-3.5" />
                          Print
                        </button>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <StatusBadge status={employee.status} />
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 text-right">
                      <div className="relative inline-block" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => setMenuOpen(menuOpen === employee.id ? null : employee.id)}
                          className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>

                        {menuOpen === employee.id && (
                          <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-gray-100 rounded-xl shadow-xl z-50 py-1 overflow-hidden">
                            <button
                              onClick={() => handleEdit(employee)}
                              className="w-full px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2.5 transition-colors"
                            >
                              <Edit2 className="w-3.5 h-3.5 text-blue-500" />
                              Edit Details
                            </button>
                            <div className="mx-3 border-t border-gray-100" />
                            <button
                              onClick={() => handleDelete(employee)}
                              className="w-full px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 flex items-center gap-2.5 transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ──────────────────────────────── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between py-2">
          <p className="text-xs text-gray-400">
            Showing {((page - 1) * limit) + 1}–{Math.min(page * limit, totalCount)} of {totalCount}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3.5 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              ← Prev
            </button>
            {[...Array(Math.min(totalPages, 5))].map((_, i) => {
              const p = i + 1;
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-9 h-9 text-sm font-semibold rounded-lg transition-colors ${
                    page === p
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                      : 'border border-gray-200 text-gray-600 bg-white hover:bg-gray-50'
                  }`}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3.5 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* ── Modal ───────────────────────────────────── */}
      <EmployeeModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditingEmployee(null);
          queryClient.invalidateQueries(['employees']);
        }}
        employee={editingEmployee}
      />
    </div>
  );
}

export default Employees;
