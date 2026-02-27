import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Sparkles, Mail, User, ArrowRight, Loader2, KeyRound } from 'lucide-react';
import { motion } from 'framer-motion';
import ThemeToggle from '../components/ThemeToggle';

const Auth = () => {
    const navigate = useNavigate();
    const { requestOtp, verifyOtp, isAuthenticated } = useAuth();
    const { register } = useAuth();

    // Do not auto-navigate on `isAuthenticated` because the signup flow
    // shows an intermediate logo upload step after registration. Navigation
    // is handled explicitly after successful OTP verify or after the logo
    // upload step completes.

    const [step, setStep] = useState('request');
    const [mode, setMode] = useState('login'); // 'login' or 'signup'
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    // debugOtp is intentionally not exposed in production UI
    const [debugOtp, setDebugOtp] = useState('');

    const [formData, setFormData] = useState({
        email: '',
        fullName: '',
        code: '',
        businessName: '',
        businessDescription: '',
        website: '',
        password: ''
    });

    const handleChange = (e) => {
        // Enforce character-limit for business description (350 characters)
        if (e.target.name === 'businessDescription') {
            const raw = e.target.value || '';
            if (raw.length > 350) {
                const truncated = raw.slice(0, 350);
                setFormData({ ...formData, businessDescription: truncated });
                return;
            }
            setFormData({ ...formData, businessDescription: raw });
            return;
        }
        setFormData({ ...formData, [e.target.name]: e.target.value });
        setError('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
    
        try {
            if (mode === 'login') {
                if (step === 'request') {
                    const result = await requestOtp(formData.email);
                    if (result.success) {
                        // Do not expose OTP in UI in production
                        setStep('verify');
                    } else {
                        setError(result.error);
                    }
                } else {
                    const result = await verifyOtp(formData.email, formData.code, formData.fullName);
                    if (result.success) {
                        navigate('/owner/dashboard');
                    } else {
                        setError(result.error);
                    }
                }
            } else {
                // signup flow
                // required business fields: business_name, email, password, full name, business description
                const payload = {
                    username: formData.email,
                    email: formData.email,
                    password: formData.password,
                    full_name: formData.fullName,
                    role: 'business'
                };
                const res = await register(payload);
                if (!res.success) {
                    setError(res.error);
                } else {
                    // after registration, save profile fields via /owner/profile
                        try {
                            const profilePayload = {
                                business_name: formData.businessName,
                                // Map the owner-provided businessDescription into the client `intro` field
                                intro: formData.businessDescription || formData.website || '',
                                website_url: formData.website || '',
                                business_description: formData.businessDescription,
                                // also set welcome_message from the description
                                welcome_message: formData.businessDescription || ''
                            };
                            // Use API client to call PUT /owner/profile (authenticated)
                            const api = (await import('../api')).default;
                            await api.put('/owner/profile', profilePayload);

                            // Fetch the saved profile to verify values are persisted
                            try {
                                await api.get('/owner/profile');
                            } catch (fetchErr) {
                                console.warn('Failed to fetch owner profile after save', fetchErr);
                            }
                        } catch (pe) {
                            console.error('Profile save failed', pe);
                        }

                    // Move to logo upload step
                    setStep('logo');
                }
            }
        } catch (err) {
            setError('An unexpected error occurred. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // Logo upload handler
    const handleLogoUpload = async (e) => {
        e.preventDefault();
        const file = e.target.logo?.files?.[0];
        if (!file) {
            setError('Please select a logo file');
            return;
        }
        setLoading(true);
        setError('');
        try {
            const api = (await import('../api')).default;
            const fd = new FormData();
            fd.append('file', file);
            const resp = await api.post('/api/v1/business/upload-logo', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
            // update local user/client profile
            const userStr = localStorage.getItem('user');
            if (userStr) {
                const u = JSON.parse(userStr);
                u.client_id = u.client_id; // keep
                localStorage.setItem('user', JSON.stringify(u));
            }
            // navigate to dashboard
            navigate('/owner/dashboard');
        } catch (err) {
            console.error('Logo upload error', err);
            setError('Logo upload failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gemini-50 via-white to-purple-50 flex items-center justify-center p-4">
            {/* Background decorative elements */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-20 left-10 w-72 h-72 bg-gemini-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
                <div className="absolute top-40 right-10 w-72 h-72 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse" style={{ animationDelay: '1s' }}></div>
                <div className="absolute -bottom-8 left-1/2 w-72 h-72 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse" style={{ animationDelay: '2s' }}></div>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="relative w-full max-w-md"
            >
                {/* Logo and Header */}
                <div className="text-center mb-8">
                    <div className="flex justify-end mb-3">
                        <ThemeToggle />
                    </div>
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                        className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-gemini-600 to-gemini-500 rounded-2xl mb-4 shadow-lg shadow-gemini-500/30"
                    >
                        <Sparkles className="w-8 h-8 text-white" />
                    </motion.div>
                    <h1 className="text-3xl font-bold text-foreground mb-2">
                        Owner Access
                    </h1>
                    <p className="text-muted-foreground">
                        OTP-based onboarding and login for business owners
                    </p>
                    <button
                        type="button"
                        onClick={() => navigate('/')}
                        className="mt-4 text-sm text-gemini-600 hover:text-gemini-700 font-medium"
                    >
                        Continue as End User
                    </button>
                </div>

                {/* Auth Card */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="glass rounded-3xl shadow-2xl p-8"
                >
                    {/* Mode toggle */}
                    <div className="flex gap-3 mb-6">
                        <button
                            className={`flex-1 py-2 rounded-xl font-medium ${mode === 'login' ? 'bg-gemini-600 text-white' : 'bg-transparent text-muted-foreground border border-border'}`}
                            onClick={() => { setMode('login'); setStep('request'); setError(''); }}
                        >
                            Login (OTP)
                        </button>
                        <button
                            className={`flex-1 py-2 rounded-xl font-medium ${mode === 'signup' ? 'bg-gemini-600 text-white' : 'bg-transparent text-muted-foreground border border-border'}`}
                            onClick={() => { setMode('signup'); setStep('request'); setError(''); }}
                        >
                            Sign Up (Owner)
                        </button>
                    </div>
                    {/* Error Message */}
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="mb-4 p-4 bg-red-50 border border-red-200 rounded-2xl"
                        >
                            <p className="text-sm text-red-600">{error}</p>
                        </motion.div>
                    )}

                    {/* Debug OTP display for local dev */}
                    {/* Debug OTP intentionally hidden in production build */}

                    {/* Form */}
                    {step !== 'logo' && (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {mode === 'signup' && (
                                <>
                                    <div>
                                        <label className="block text-sm font-medium text-muted-foreground mb-2">Business Name</label>
                                        <input type="text" name="businessName" value={formData.businessName || ''} onChange={handleChange} required className="input-field" />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-muted-foreground mb-2">Business Description</label>
                                        <textarea name="businessDescription" value={formData.businessDescription || ''} onChange={handleChange} required className="input-field h-24" />
                                        <div className="text-xs text-muted-foreground mt-1">{(formData.businessDescription || '').length}/350 chars</div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-muted-foreground mb-2">Website (optional)</label>
                                        <input type="url" name="website" value={formData.website || ''} onChange={handleChange} placeholder="https://example.com" className="input-field" />
                                    </div>
                                </>
                            )}

                            {/* Common fields */}
                            <div>
                                <label className="block text-sm font-medium text-muted-foreground mb-2">Full Name</label>
                                <div className="relative">
                                    <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                                    <input type="text" name="fullName" value={formData.fullName} onChange={handleChange} placeholder="Enter your full name" className="input-field pl-12" />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-muted-foreground mb-2">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                                    <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="Enter your business email (e.g., owner@company.com)" required className="input-field pl-12" />
                                </div>
                            </div>

                            {mode === 'signup' && (
                                <div>
                                    <label className="block text-sm font-medium text-muted-foreground mb-2">Password</label>
                                    <input type="password" name="password" value={formData.password || ''} onChange={handleChange} required className="input-field" />
                                </div>
                            )}

                            {mode === 'login' && step === 'verify' && (
                                <div>
                                    <label className="block text-sm font-medium text-muted-foreground mb-2">OTP Code</label>
                                    <div className="relative">
                                        <KeyRound className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                                        <input type="text" name="code" value={formData.code} onChange={handleChange} placeholder="Enter the 6-digit OTP sent to your email" required className="input-field pl-12" />
                                    </div>
                                </div>
                            )}

                            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 mt-6">
                                {loading ? (<><Loader2 className="w-5 h-5 animate-spin" /><span>{mode === 'signup' ? 'Creating account...' : (step === 'request' ? 'Sending OTP...' : 'Verifying OTP...')}</span></>) : (<><span>{mode === 'signup' ? 'Create Account' : (step === 'request' ? 'Send OTP' : 'Verify OTP')}</span><ArrowRight className="w-5 h-5" /></>)}
                            </button>
                        </form>
                    )}

                    {/* Logo upload step after signup */}
                    {step === 'logo' && mode === 'signup' && (
                        <div className="space-y-4">
                            <p className="text-sm text-muted-foreground">Your account was created. Upload a logo to personalize your business profile.</p>
                            <form onSubmit={handleLogoUpload} className="space-y-4">
                                <input type="file" name="logo" accept="image/*" />
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Upload Logo</button>
                                    <button type="button" onClick={() => navigate('/owner/dashboard')} className="btn-secondary">Skip</button>
                                </div>
                            </form>
                        </div>
                    )}
                    
                    <div className="mt-6 text-center space-y-4">
                        {mode === 'login' && (
                            <button type="button" onClick={() => { setStep(step === 'request' ? 'verify' : 'request'); setError(''); }} className="text-sm text-muted-foreground hover:text-gemini-600 transition-colors">{step === 'request' ? 'Already have OTP? Verify now' : 'Request a new OTP'}</button>
                        )}
                    </div>
                </motion.div>

                {/* Footer */}
                <p className="text-center text-sm text-muted-foreground mt-8">
                    By continuing, you agree to our Terms of Service and Privacy Policy
                </p>
            </motion.div>
        </div>
    );
};

export default Auth;
