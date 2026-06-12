import axios from 'axios';
import toast from 'react-hot-toast';

const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL,
  withCredentials: true,
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // If the refresh endpoint itself fails, don't loop
      if (originalRequest.url === '/auth/refresh' || originalRequest.url === '/auth/login') {
        return Promise.reject(error);
      }

      try {
        // Attempt to refresh the token
        await apiClient.post('/auth/refresh');
        
        // Retry original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, usually means user needs to log in again
        toast.error('Session expired. Please log in again.');
        return Promise.reject(refreshError);
      }
    }

    // Show generic error toasts for non-401s if they are 500s or network errors
    if (!error.response) {
      toast.error('Network error. Please check your connection.');
    } else if (error.response.status >= 500) {
      toast.error('A server error occurred. Please try again later.');
    }

    return Promise.reject(error);
  }
);
