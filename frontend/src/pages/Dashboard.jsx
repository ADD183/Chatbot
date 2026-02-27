import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import {
    Upload,
    FileText,
    CheckCircle2,
    Clock,
    XCircle,
    MessageSquare,
    LogOut,
    Sparkles,
    Loader2,
    File,
    Trash2,
    BarChart3,
    Globe,
    ChevronDown,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ThemeToggle from '../components/ThemeToggle';
import GlobalHeader from '../components/GlobalHeader';
import BusinessProfileSettings from '../components/BusinessProfileSettings';

const Dashboard = () => {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const fileInputRef = useRef(null);

    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [dragActive, setDragActive] = useState(false);
    const [profileLoading, setProfileLoading] = useState(false);
    const [businessProfile, setBusinessProfile] = useState({ business_name: '', intro: '', business_description: '', website_url: '' });
    const [analytics, setAnalytics] = useState({ total_questions: 0, recent_qa: [] });
    const [historyOpen, setHistoryOpen] = useState(false);

    useEffect(() => {
        fetchFiles();
        fetchProfile();
        fetchAnalytics();
    }, []);

    const fetchProfile = async () => {
        try {
            const response = await api.get('/owner/profile');
            // Prefer business_description, then intro, then welcome_message
            const introValue = response.data.business_description || response.data.intro || response.data.welcome_message || '';
            setBusinessProfile({
                business_name: response.data.name || '',
                intro: introValue,
                business_description: response.data.business_description || introValue,
                website_url: response.data.website_url || '',
                logo_url: response.data.logo_url || response.data.business_logo_url || null,
            });
        } catch (error) {
            console.error('Error fetching owner profile:', error);
        }
    };

    const fetchAnalytics = async () => {
        try {
            const response = await api.get('/owner/analytics', { params: { limit: 25 } });
            setAnalytics(response.data || { total_questions: 0, recent_qa: [] });
        } catch (error) {
            console.error('Error fetching analytics:', error);
        }
    };

    const fetchFiles = async () => {
        try {
            setLoading(true);
            const response = await api.get('/documents/');
            setFiles(response.data.documents || []);
        } catch (error) {
            console.error('Error fetching files:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleFileSelect = async (e) => {
        const selectedFiles = Array.from(e.target.files);
        if (selectedFiles.length === 0) return;

        setUploading(true);
        setUploadProgress(0);

        for (const file of selectedFiles) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                await api.post('/documents/upload', formData, {
                    onUploadProgress: (progressEvent) => {
                        const progress = Math.round(
                            (progressEvent.loaded * 100) / progressEvent.total
                        );
                        setUploadProgress(progress);
                    },
                });
                await fetchFiles();
                await fetchAnalytics();
            } catch (error) {
                console.error('Error uploading file:', error);
                alert(`Failed to upload ${file.name}`);
            }
        }

        setUploading(false);
        setUploadProgress(0);
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Are you sure you want to delete this document?')) return;
        try {
            await api.delete(`/documents/${id}`);
            setFiles(files.filter((f) => f.id !== id));
        } catch (error) {
            console.error('Error deleting file:', error);
        }
    };

    const saveProfile = async () => {
        try {
            setProfileLoading(true);
            await api.put('/owner/profile', {
                business_name: businessProfile.business_name,
                business_description: businessProfile.business_description || businessProfile.intro,
                website_url: businessProfile.website_url || null,
            });
            await fetchProfile();
            await fetchFiles();
        } catch (error) {
            console.error('Error saving profile:', error);
            alert('Failed to save profile');
        } finally {
            setProfileLoading(false);
        }
    };

    const refreshUrlKb = async () => {
        if (!businessProfile.website_url) {
            alert('Please enter website URL first');
            return;
        }
        try {
            setProfileLoading(true);
            await api.post('/documents/refresh-url', null, {
                params: { website_url: businessProfile.website_url },
            });
            await fetchFiles();
        } catch (error) {
            console.error('Error refreshing website KB:', error);
            alert('Website refresh failed');
        } finally {
            setProfileLoading(false);
        }
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case 'completed':
                return (
                    <span className="badge-success">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Ready
                    </span>
                );
            case 'processing':
                return (
                    <span className="badge-warning animate-pulse">
                        <Clock className="w-3 h-3 mr-1" /> Processing
                    </span>
                );
            case 'failed':
                return (
                    <span className="badge-error">
                        <XCircle className="w-3 h-3 mr-1" /> Failed
                    </span>
                );
            default:
                return <span className="badge-info">{status}</span>;
        }
    };

    return (
        <div className="min-h-screen bg-background flex flex-col">
            {/* Navigation Header */}
            <GlobalHeader
                profile={{ business_name: businessProfile.business_name, business_logo_url: businessProfile.logo_url }}
                rightElements={(
                    <>
                        <button
                            onClick={() => {
                                const slug = (businessProfile.business_name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                                navigate(slug ? `/${slug}` : '/');
                            }}
                            className="flex items-center space-x-2 px-4 py-2 bg-gemini-50 text-gemini-600 rounded-xl hover:bg-gemini-100 transition-colors font-medium"
                        >
                            <MessageSquare className="w-4 h-4" />
                            <span>Open Public Page</span>
                        </button>
                    </>
                )}
            />

            <main className="flex-1 max-w-7xl mx-auto w-full p-6 md:p-8 space-y-8">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card shadow-sm border-border"
                >
                    <BusinessProfileSettings
                        initialProfile={businessProfile}
                        onSaved={async () => { await fetchProfile(); await fetchFiles(); }}
                    />
                    <div className="mt-4">
                        <div className="flex items-start gap-4">
                            <div>
                                <div className="w-24 h-24 bg-card rounded-xl overflow-hidden border border-border flex items-center justify-center">
                                    {businessProfile.logo_url ? (
                                        <img src={businessProfile.logo_url.startsWith('http') ? businessProfile.logo_url : `${api.defaults.baseURL}${businessProfile.logo_url}`} alt="Logo" className="w-full h-full object-cover" />
                                    ) : (
                                        <div className="text-muted-foreground">No logo</div>
                                    )}
                                </div>
                            </div>
                            <div className="flex-1">
                                <input type="file" accept="image/*" onChange={async (e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;
                                    const formData = new FormData();
                                    // backend expects field name 'file'
                                    formData.append('file', file);
                                    try {
                                        setProfileLoading(true);
                                        const resp = await api.post('/api/v1/business/upload-logo', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
                                        const url = resp.data?.logo_url || resp.data?.url || resp.data?.business_logo_url || resp.data?.path || resp.data;
                                        if (url) {
                                            setBusinessProfile((prev) => ({ ...prev, logo_url: url }));
                                        }
                                    } catch (err) {
                                        console.error('Logo upload failed', err);
                                        alert('Logo upload failed');
                                    } finally {
                                        setProfileLoading(false);
                                    }
                                }} />
                                <p className="text-sm text-muted-foreground mt-2">Upload a PNG/JPEG logo (recommended 300x300)</p>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Upload Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card shadow-sm border-border"
                >
                    <div className="flex items-center space-x-3 mb-6">
                        <div className="p-2 bg-blue-50 rounded-lg">
                            <Upload className="w-5 h-5 text-blue-600" />
                        </div>
                        <h2 className="text-xl font-bold text-foreground">Upload Knowledge Base</h2>
                    </div>

                    <div
                        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                        onDragLeave={() => setDragActive(false)}
                        onDrop={(e) => { e.preventDefault(); setDragActive(false); handleFileSelect({ target: { files: e.dataTransfer.files } }); }}
                        className={`relative border-2 border-dashed rounded-2xl p-12 transition-all duration-300 text-center ${dragActive ? 'border-gemini-500 bg-card' : 'border-border hover:border-gemini-400 hover:bg-card'
                            }`}
                    >
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileSelect}
                            className="hidden"
                            multiple
                            accept=".pdf,.txt,.docx"
                            title="Upload PDF, TXT, or DOCX files for your knowledge base"
                        />
                        <div className="max-w-xs mx-auto">
                            <div className="w-16 h-16 bg-card rounded-2xl shadow-sm border border-border flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                                <FileText className="w-8 h-8 text-muted-foreground" />
                            </div>
                            <h3 className="text-lg font-semibold text-foreground mb-1">Drop files here</h3>
                            <p className="text-sm text-muted-foreground mb-6">Support for PDF, TXT and DOCX (Max 10MB)</p>
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploading}
                                className="btn-primary w-full flex items-center justify-center space-x-2"
                            >
                                {uploading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span>Uploading {uploadProgress}%</span>
                                    </>
                                ) : (
                                    <>
                                        <Upload className="w-4 h-4" />
                                        <span>Select Files</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="card shadow-sm border-border"
                >
                    <div className="flex items-center space-x-3 mb-4">
                        <div className="p-2 bg-purple-50 rounded-lg">
                            <BarChart3 className="w-5 h-5 text-purple-600" />
                        </div>
                        <h2 className="text-xl font-bold text-foreground">Insights</h2>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">Total questions asked: <span className="font-semibold">{analytics.total_questions}</span></p>
                    <button
                        type="button"
                        onClick={() => setHistoryOpen((prev) => !prev)}
                        className="btn-ghost w-full flex items-center justify-between"
                    >
                        <span className="font-medium">Chat History</span>
                        <ChevronDown className={`w-4 h-4 transition-transform ${historyOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {historyOpen && (
                        <div className="space-y-3 mt-3">
                            {analytics.recent_qa?.length ? analytics.recent_qa.map((item) => (
                                <div key={item.id} className="p-3 rounded-xl border border-border bg-card">
                                    <div className="text-xs text-muted-foreground mb-1">{new Date(item.created_at).toLocaleString()} · Session {item.session_id}</div>
                                    <div className="text-sm font-medium text-foreground">Q: {item.question}</div>
                                    <div className="text-sm text-muted-foreground mt-1">A: {item.answer}</div>
                                </div>
                            )) : <p className="text-sm text-muted-foreground">No questions yet.</p>}
                        </div>
                    )}
                </motion.div>

                {/* Files List */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="card"
                >
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center space-x-3">
                            <div className="p-2 bg-purple-50 rounded-lg">
                                <File className="w-5 h-5 text-purple-600" />
                            </div>
                            <h2 className="text-xl font-bold text-foreground">Your Documents</h2>
                        </div>
                        <span className="text-sm text-muted-foreground font-medium">{files.length} Files</span>
                    </div>

                    {loading ? (
                        <div className="py-20 text-center">
                            <Loader2 className="w-8 h-8 animate-spin text-gemini-500 mx-auto" />
                        </div>
                        ) : files.length === 0 ? (
                        <div className="py-20 text-center bg-card rounded-2xl border border-dashed border-border">
                            <p className="text-muted-foreground">No documents uploaded yet</p>
                        </div>
                    ) : (
                        <div className="grid gap-4">
                                    <AnimatePresence>
                                {files.map((file) => (
                                    <motion.div
                                        key={file.id}
                                        layout
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        className="group flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:shadow-md transition-all"
                                    >
                                        <div className="flex items-center space-x-4">
                                            <div className="w-10 h-10 bg-card rounded-lg flex items-center justify-center text-muted-foreground group-hover:text-gemini-500 group-hover:bg-gemini-50 transition-colors">
                                                <FileText className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-semibold text-foreground">{file.filename}</h4>
                                                <div className="flex items-center space-x-3 mt-1 text-xs text-muted-foreground">
                                                    <span>{new Date(file.created_at).toLocaleDateString()}</span>
                                                    <span>•</span>
                                                    {file.size && (
                                                        <span>{(file.size / 1024).toFixed(2)} KB</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            {getStatusBadge(file.status)}
                                            <div className="flex items-center space-x-1 ml-4 border-l pl-4 border-border">
                                                <button
                                                    onClick={() => {
                                                        const slug = (businessProfile.business_name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                                                        navigate(slug ? `/${slug}` : '/');
                                                    }}
                                                    className="p-2 text-gemini-600 hover:bg-gemini-50 rounded-lg transition-colors"
                                                    title="Chat with this file"
                                                >
                                                    <MessageSquare className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(file.id)}
                                                    className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}
                </motion.div>
            </main>
        </div>
    );
};

export default Dashboard;