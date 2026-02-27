/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // -----------------------------
    // Check login on app start
    // -----------------------------
    useEffect(() => {
        const storedUser = localStorage.getItem('user');
        const token = localStorage.getItem('access_token');

        if (storedUser && token) {
            try {
                setUser(JSON.parse(storedUser));
            } catch (err) {
                console.error('User parse error:', err);
                localStorage.removeItem('user');
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
            }
        }

        setLoading(false);
    }, []);

    const requestOtp = async (email) => {
        try {
            const response = await api.post('/auth/otp/request', {
                email,
            });
            return { success: true, otp: response.data.debug_otp || '' };
        } catch (error) {
            console.error('OTP request error:', error);
            let errorMessage = 'Failed to request OTP';
            if (error.response?.data?.detail) {
                errorMessage = Array.isArray(error.response.data.detail)
                    ? error.response.data.detail[0].msg
                    : error.response.data.detail;
            }
            return { success: false, error: errorMessage };
        }
    };

    const register = async ({ username, email, password, full_name, role = 'business' }) => {
        try {
            const response = await api.post('/auth/register', {
                username,
                email,
                password,
                full_name,
                role,
            });

            const { access_token, refresh_token, user: userData } = response.data;

            localStorage.setItem('access_token', access_token);
            if (refresh_token) {
                localStorage.setItem('refresh_token', refresh_token);
            }

            localStorage.setItem('user', JSON.stringify(userData));
            setUser(userData);

            return { success: true, user: userData };
        } catch (error) {
            console.error('Register error:', error);
            let errorMessage = 'Registration failed';
            if (error.response?.data?.detail) {
                errorMessage = Array.isArray(error.response.data.detail)
                    ? error.response.data.detail[0].msg
                    : error.response.data.detail;
            }
            return { success: false, error: errorMessage };
        }
    };

    const verifyOtp = async (email, code, fullName = null) => {
        try {
            const response = await api.post('/auth/otp/verify', {
                email,
                code,
                full_name: fullName,
            });

            const { access_token, refresh_token, user: userData } = response.data;

            localStorage.setItem('access_token', access_token);
            if (refresh_token) {
                localStorage.setItem('refresh_token', refresh_token);
            }

            localStorage.setItem('user', JSON.stringify(userData));
            setUser(userData);

            return { success: true, user: userData };

        } catch (error) {
            console.error('OTP verify error:', error);
            let errorMessage = 'OTP verification failed';
            if (error.response?.data?.detail) {
                errorMessage = Array.isArray(error.response.data.detail)
                    ? error.response.data.detail[0].msg
                    : error.response.data.detail;
            }
            return { success: false, error: errorMessage };
        }
    };

    // -----------------------------
    // LOGOUT
    // -----------------------------
    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        setUser(null);
    };

    const value = {
        user,
        requestOtp,
        verifyOtp,
        register,
        logout,
        loading,
        isAuthenticated: !!user,
        isBusiness: user?.role === 'business',
        isUser: false,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
