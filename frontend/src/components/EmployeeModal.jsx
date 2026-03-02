import React, { useState, useEffect } from 'react';
import { User, Mail, Hash, Building2, Briefcase, ShieldCheck, X, Loader2, UserPlus, UserCog } from 'lucide-react';
import api from "../services/api";

const DEPARTMENTS = ['Engineering', 'HR', 'Finance', 'Marketing', 'Operations', 'Sales', 'Design'];
const DESIGNATIONS = ['Manager', 'Senior Engineer', 'Engineer', 'Analyst', 'Designer', 'Intern'];

function FieldWrapper({ icon: Icon, label, required, children }) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500">
        <Icon className="w-3.5 h-3.5" />
        {label}
        {required && <span className="text-blue-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

const baseInput =
  "w-full px-3.5 py-2.5 rounded-lg text-sm font-medium " +
  "bg-gray-50 " +
  "border border-gray-200 " +
  "text-gray-900 " +
  "placeholder:text-gray-400 " +
  "focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 " +
  "transition-all duration-150";

const disabledInput = baseInput + " opacity-60 cursor-not-allowed bg-gray-100";

function EmployeeModal({ open, onClose, employee }) {
  const [formData, setFormData] = useState({
    employee_code: '',
    full_name: '',
    email: '',
    department: '',
    designation: '',
    status: 'ACTIVE'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isEditing = !!employee;

  useEffect(() => {
    if (employee) {
      setFormData({
        employee_code: employee.employee_code || '',
        full_name: employee.full_name || '',
        email: employee.email || '',
        department: employee.department || '',
        designation: employee.designation || '',
        status: employee.status || 'ACTIVE',
      });
    } else {
      setFormData({ employee_code: '', full_name: '', email: '', department: '', designation: '', status: 'ACTIVE' });
    }
    setError('');
  }, [employee, open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!formData.employee_code || !formData.full_name || !formData.email || !formData.department) {
      setError('Please fill in all required fields.');
      return;
    }
    setLoading(true);
    try {
      if (isEditing) {
        await api.put(`/employees/${employee.id}`, formData);
      } else {
        await api.post('/employees', formData);
      }
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Operation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  if (!open) return null;

  const initials = formData.full_name
    ? formData.full_name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : isEditing ? 'ED' : 'NE';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg animate-in fade-in slide-in-from-bottom-4 duration-200">
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">

          {/* Header */}
          <div className="relative px-6 pt-6 pb-5 bg-gradient-to-br from-blue-600 to-blue-700">
            {/* Decorative circles */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-8 w-16 h-16 bg-white/5 rounded-full translate-y-1/2" />

            <div className="relative flex items-center justify-between">
              <div className="flex items-center gap-4">
                {/* Avatar preview */}
                <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm border border-white/30 flex items-center justify-center text-white font-bold text-lg shadow-inner">
                  {initials || (isEditing ? <UserCog className="w-6 h-6" /> : <UserPlus className="w-6 h-6" />)}
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">
                    {isEditing ? 'Edit Employee' : 'Add New Employee'}
                  </h2>
                  <p className="text-blue-200 text-xs mt-0.5">
                    {isEditing ? `Updating ${employee.employee_code}` : 'Fill in the details below'}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/80 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2.5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
                <div className="w-4 h-4 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-white text-[10px] font-bold">!</span>
                </div>
                {error}
              </div>
            )}

            {/* Employee Code */}
            <FieldWrapper icon={Hash} label="Employee Code" required>
              <input
                type="text"
                name="employee_code"
                value={formData.employee_code}
                onChange={handleChange}
                className={isEditing ? disabledInput : baseInput}
                placeholder="e.g. EMP001"
                disabled={isEditing}
              />
            </FieldWrapper>

            {/* Full Name */}
            <FieldWrapper icon={User} label="Full Name" required>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className={baseInput}
                placeholder="e.g. John Doe"
              />
            </FieldWrapper>

            {/* Email */}
            <FieldWrapper icon={Mail} label="Email Address" required>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className={baseInput}
                placeholder="e.g. john@company.com"
              />
            </FieldWrapper>

            {/* Department + Designation (2 cols) */}
            <div className="grid grid-cols-2 gap-4">
              <FieldWrapper icon={Building2} label="Department" required>
                <input
                  type="text"
                  name="department"
                  value={formData.department}
                  onChange={handleChange}
                  list="dept-list"
                  className={baseInput}
                  placeholder="e.g. Engineering"
                />
                <datalist id="dept-list">
                  {DEPARTMENTS.map((d) => <option key={d} value={d} />)}
                </datalist>
              </FieldWrapper>

              <FieldWrapper icon={Briefcase} label="Designation">
                <input
                  type="text"
                  name="designation"
                  value={formData.designation}
                  onChange={handleChange}
                  list="desig-list"
                  className={baseInput}
                  placeholder="e.g. Engineer"
                />
                <datalist id="desig-list">
                  {DESIGNATIONS.map((d) => <option key={d} value={d} />)}
                </datalist>
              </FieldWrapper>
            </div>

            {/* Status */}
            <FieldWrapper icon={ShieldCheck} label="Status">
              <div className="flex gap-2">
                {[
                  { value: 'ACTIVE', label: 'Active', color: 'green' },
                  { value: 'INACTIVE', label: 'Inactive', color: 'red' },
                  { value: 'ON_LEAVE', label: 'On Leave', color: 'amber' },
                ].map(({ value, label, color }) => {
                  const active = formData.status === value;
                  const colorMap = {
                    green: active
                      ? 'bg-green-600 text-white border-green-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-green-400',
                    red: active
                      ? 'bg-red-600 text-white border-red-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-red-400',
                    amber: active
                      ? 'bg-amber-500 text-white border-amber-500'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-amber-400',
                  };
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setFormData((p) => ({ ...p, status: value }))}
                      className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition-all duration-150 ${colorMap[color]}`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </FieldWrapper>

            {/* Divider */}
            <div className="border-t border-gray-100" />

            {/* Actions */}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold border border-gray-200 text-gray-600 bg-white hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/25 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-150 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : isEditing ? (
                  <>
                    <UserCog className="w-4 h-4" />
                    Update Employee
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    Create Employee
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default EmployeeModal;
