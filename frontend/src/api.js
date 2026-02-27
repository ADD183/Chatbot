import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000',
});

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    // 🔥 Do NOT attach token to auth routes
    if (
      token &&
            !config.url.includes("/auth/login") &&
            !config.url.includes("/auth/register") &&
            !config.url.includes("/auth/refresh") &&
            !config.url.includes("/auth/otp/") &&
            !config.url.includes("/public/")
    ) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // If error is 401 and we haven't retried yet
        if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !originalRequest.url.includes("/auth/login") &&
            !originalRequest.url.includes("/auth/otp/") &&
            !originalRequest.url.includes("/public/")
            ) {
            originalRequest._retry = true;

            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                    const response = await axios.post('http://localhost:8000/auth/refresh', {
                        refresh_token: refreshToken,
                    });

                    const { access_token } = response.data;
                    const { refresh_token } = response.data;
                    if (refresh_token) {
                        localStorage.setItem('refresh_token', refresh_token);
                    }
                    localStorage.setItem('access_token', access_token);

                    // Retry the original request with new token
                    originalRequest.headers.Authorization = `Bearer ${access_token}`;
                    return api(originalRequest);
                }
            } catch (refreshError) {
                // Refresh failed, clear tokens and redirect to login
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('user');
                window.location.href = '/auth';
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

export default api;
