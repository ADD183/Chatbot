import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Discovery from './pages/Discovery';
import BusinessChat from './pages/BusinessChat';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, isBusiness, loading } = useAuth();

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gemini-50 to-purple-50">
                <div className="text-center">
                    <div className="text-4xl mb-4 animate-bounce">✨</div>
                    <p className="text-muted-foreground">Loading Assistant...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/owner/auth" replace />;
    }

    if (!isBusiness) return <Navigate to="/owner/auth" replace />;

    return children;
};

function AppRoutes() {
    return (
        <Routes>
            <Route path="/owner/auth" element={<Auth />} />

            <Route
                path="/owner/dashboard"
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />

            <Route path="/" element={<Discovery />} />
            <Route path="/:businessSlug" element={<BusinessChat />} />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}

function App() {
    return (
        <BrowserRouter
            future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
            }}
        >
            <ThemeProvider>
                <AuthProvider>
                    <AppRoutes />
                </AuthProvider>
            </ThemeProvider>
        </BrowserRouter>
    );
}

export default App;