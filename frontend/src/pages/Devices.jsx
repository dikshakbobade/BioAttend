import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Monitor,
  Camera,
  Fingerprint,
  Plus,
  Trash2,
  Loader2
} from 'lucide-react';
import { deviceApi } from '../services/api';

function Devices() {
  const queryClient = useQueryClient();

  const [showAddModal, setShowAddModal] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const [newDevice, setNewDevice] = useState({
    device_id: '',
    device_name: '',
    device_type: 'FACE_CAMERA',
    location: ''
  });

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const { data: devices = [], isLoading, error } = useQuery({
    queryKey: ['devices'],
    queryFn: async () => {
      const res = await deviceApi.getAll();
      if (Array.isArray(res.data)) return res.data;
      if (Array.isArray(res.data?.items)) return res.data.items;
      return [];
    }
  });

  const registerMutation = useMutation({
    mutationFn: (payload) => deviceApi.register(payload),
    onSuccess: () => {
      queryClient.invalidateQueries(['devices']);
      showMessage('success', 'Device registered successfully');
      setShowAddModal(false);
      setNewDevice({ device_id: '', device_name: '', device_type: 'FACE_CAMERA', location: '' });
    },
    onError: (err) => {
      showMessage('error', err.response?.data?.detail || 'Failed to register device');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => deviceApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['devices']);
      showMessage('success', 'Device deleted');
    }
  });

  const activateMutation = useMutation({
    mutationFn: (id) => deviceApi.activate(id),
    onSuccess: () => queryClient.invalidateQueries(['devices'])
  });

  const deactivateMutation = useMutation({
    mutationFn: (id) => deviceApi.deactivate(id),
    onSuccess: () => queryClient.invalidateQueries(['devices'])
  });

  const handleAddDevice = (e) => {
    e.preventDefault();
    if (!newDevice.device_id.trim() || !newDevice.device_name.trim()) {
      showMessage('error', 'Device ID and Device Name are required');
      return;
    }
    registerMutation.mutate({
      device_id: newDevice.device_id.trim(),
      device_name: newDevice.device_name.trim(),
      device_type: newDevice.device_type,
      location: newDevice.location || null
    });
  };

  const handleDelete = (device) => {
    if (window.confirm(`Delete device "${device.device_id}"?`)) {
      deleteMutation.mutate(device.id || device.device_id);
    }
  };

  const getIcon = (type) => {
    if (type === 'FACE_CAMERA') return <Camera className="w-5 h-5" />;
    if (type === 'FINGERPRINT_SCANNER') return <Fingerprint className="w-5 h-5" />;
    return <Monitor className="w-5 h-5" />;
  };

  const inputClass =
    "w-full border border-gray-200 dark:border-slate-600 px-3 py-2 rounded bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-200 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 outline-none";

  return (
    <div className="space-y-6">
      {/* Toast message */}
      {message.text && (
        <div
          className={`px-4 py-3 rounded text-sm ${message.type === 'success'
              ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300'
              : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'
            }`}
        >
          {message.text}
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Devices</h1>
          <p className="text-gray-500 dark:text-slate-400">Manage biometric devices</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600"
        >
          <Plus className="w-4 h-4" />
          Add Device
        </button>
      </div>

      {error && (
        <div className="bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 px-4 py-3 rounded">
          Failed to load devices
        </div>
      )}

      {/* Device Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-full flex justify-center py-10">
            <Loader2 className="animate-spin w-6 h-6 text-blue-600" />
          </div>
        ) : devices.length === 0 ? (
          <div className="col-span-full text-center text-gray-500 dark:text-slate-400 py-10">
            No devices registered yet.
          </div>
        ) : (
          devices.map((device) => (
            <div
              key={device.id}
              className="border border-gray-200 dark:border-slate-600/60 rounded-lg p-5 bg-white dark:bg-[#334155]"
            >
              <div className="flex justify-between mb-4">
                <div
                  className={`p-3 rounded ${device.is_active
                      ? 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400'
                      : 'bg-gray-100 dark:bg-slate-600/60 text-gray-400 dark:text-slate-500'
                    }`}
                >
                  {getIcon(device.device_type)}
                </div>
                {device.is_active ? (
                  <span className="text-xs bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 px-2 py-1 rounded">
                    Active
                  </span>
                ) : (
                  <span className="text-xs bg-gray-100 dark:bg-slate-600/60 text-gray-600 dark:text-slate-400 px-2 py-1 rounded">
                    Inactive
                  </span>
                )}
              </div>

              <h3 className="font-semibold text-gray-900 dark:text-slate-100">{device.device_name}</h3>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                {device.device_type.replace('_', ' ')}
              </p>
              <p className="text-xs text-gray-400 dark:text-slate-500 mb-4">
                📍 {device.location || 'N/A'}
              </p>

              <div className="flex gap-2">
                {device.is_active ? (
                  <button
                    onClick={() => deactivateMutation.mutate(device.id)}
                    className="flex-1 text-xs bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300 py-1 rounded hover:bg-orange-200 dark:hover:bg-orange-900/60"
                  >
                    Deactivate
                  </button>
                ) : (
                  <button
                    onClick={() => activateMutation.mutate(device.id)}
                    className="flex-1 text-xs bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 py-1 rounded hover:bg-green-200 dark:hover:bg-green-900/60"
                  >
                    Activate
                  </button>
                )}
                <button
                  onClick={() => handleDelete(device)}
                  className="text-xs bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 px-3 py-1 rounded hover:bg-red-200 dark:hover:bg-red-900/60"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add Device Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#334155] rounded-lg p-6 w-full max-w-md border border-gray-100 dark:border-slate-600/60">
            <h2 className="text-lg font-bold mb-4 text-gray-900 dark:text-slate-100">Add Device</h2>

            <form onSubmit={handleAddDevice} className="space-y-4">
              <input
                className={inputClass}
                placeholder="Device ID (FACE-CAM-001)"
                value={newDevice.device_id}
                onChange={(e) => setNewDevice({ ...newDevice, device_id: e.target.value })}
                required
              />
              <input
                className={inputClass}
                placeholder="Device Name"
                value={newDevice.device_name}
                onChange={(e) => setNewDevice({ ...newDevice, device_name: e.target.value })}
                required
              />
              <select
                className={inputClass}
                value={newDevice.device_type}
                onChange={(e) => setNewDevice({ ...newDevice, device_type: e.target.value })}
              >
                <option value="FACE_CAMERA">Face Recognition Camera</option>
                <option value="FINGERPRINT_SCANNER">Fingerprint Scanner</option>
              </select>
              <input
                className={inputClass}
                placeholder="Location"
                value={newDevice.location}
                onChange={(e) => setNewDevice({ ...newDevice, location: e.target.value })}
              />

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 py-2 rounded hover:bg-gray-50 dark:hover:bg-slate-600/40"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 dark:bg-blue-700 text-white py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600"
                >
                  Add Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Devices;
