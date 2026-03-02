import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      // Login function
      login: async (username, password) => {
        try {
          const formData = new URLSearchParams();
          formData.append('username', username);
          formData.append('password', password);
          formData.append('grant_type', 'password');

          const response = await api.post('/admin/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          });

          const { access_token } = response.data;
          
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          const userResponse = await api.get('/admin/me');
          
          set({
            user: userResponse.data,
            token: access_token,
            isAuthenticated: true
          });

          localStorage.setItem('token', access_token);
          localStorage.setItem('user', JSON.stringify(userResponse.data));

          return { success: true };
        } catch (error) {
          console.error('Login error:', error);
          return {
            success: false, 
            error: error.response?.data?.detail || 'Login failed'
          };
        }
      },

      logout: () => {
        delete api.defaults.headers.common['Authorization'];
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        set({
          user: null,
          token: null,
          isAuthenticated: false
        });
      },

      initAuth: () => {
        const token = get().token;
        if (token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
      },

      setToken: (token) => {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        localStorage.setItem('token', token);
        set({ token, isAuthenticated: true });
      },

      setUser: (user) => {
        localStorage.setItem('user', JSON.stringify(user));
        set({ user });
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);

useAuthStore.getState().initAuth();
