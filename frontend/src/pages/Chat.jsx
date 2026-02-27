import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import {
    Send,
    Sparkles,
    User as UserIcon,
    LogOut,
    Loader2,
    RotateCcw,
} from 'lucide-react';
import Avatar from '../components/Avatar';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { formatToBullets } from '../utils/formatResponse';
import { motion, AnimatePresence } from 'framer-motion';

const Chat = () => {
    const { user, logout } = useAuth();
    const [profile, setProfile] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const suggestedQuestions = [
        "What can you help me with?",
        "Tell me about your capabilities",
        "How does this work?",
        "What information do you have?",
    ];

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        // Focus input on mount
        inputRef.current?.focus();
    }, []);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const resp = await api.get('/api/v1/business/profile');
                setProfile(resp.data || null);
            } catch (err) {
                console.warn('Could not load business profile', err);
            }
        };

        fetchProfile();
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleSend = async (messageText = input) => {
        if (!messageText.trim() || loading) return;

        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: messageText,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);
        setStreaming(true);

            try {
            const sessionId = user?.id ? String(user.id) : 'default';
            const token = localStorage.getItem('access_token');

            const response = await api.post(
                '/chat',
                {
                    message: messageText,
                    session_id: sessionId,
                    tenant_name: user?.client_id ? String(user.client_id) : 'default',
                    tenant_id: user?.client_id || null,
                },
                {
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                }
            );


            const aiMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: response.data.response || response.data.message,
                timestamp: new Date(),
            };

            // Character-level typing (typewriter) streaming
            const fullText = aiMessage.content || '';
            setMessages((prev) => [...prev, { ...aiMessage, content: '' }]);

            for (let i = 0; i < fullText.length; i++) {
                const currentText = fullText.slice(0, i + 1);
                setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                        ...aiMessage,
                        content: currentText,
                    };
                    return newMessages;
                });
                setStreaming(true);
                await new Promise((resolve) => setTimeout(resolve, 16));
            }
            // After streaming completes, post-process to prefer bullet points
            const formatted = formatToBullets(fullText);
            if (formatted !== fullText) {
                setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                        ...aiMessage,
                        content: formatted,
                    };
                    return newMessages;
                });
            }

            setStreaming(false);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                timestamp: new Date(),
                isError: true,
            };
            setMessages((prev) => [...prev, errorMessage]);
            setStreaming(false);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleNewChat = () => {
        setMessages([]);
        inputRef.current?.focus();
    };

    return (
        <div className="h-screen flex flex-col bg-background">
            {/* Header */}
            <header className="glass border-b border-border sticky top-0 z-10">
                <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-gemini-600 to-gemini-500 rounded-xl flex items-center justify-center shadow-lg shadow-gemini-500/30">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-foreground">Vayvsai.ai</h1>
                            <p className="text-xs text-muted-foreground">Smart business assistant</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {messages.length > 0 && (
                            <button
                                onClick={handleNewChat}
                                className="btn-ghost flex items-center gap-2"
                            >
                                <RotateCcw className="w-4 h-4" />
                                New Chat
                            </button>
                        )}
                        <div className="h-6 w-px bg-gray-200" />
                        <div className="flex items-center gap-3">
                            {/* Business logo (owner-uploaded) */}
                            <Avatar src={profile?.business_logo_url ? (profile.business_logo_url.startsWith('http') ? profile.business_logo_url : `${api.defaults.baseURL}${profile.business_logo_url}`) : null} name={profile?.business_name} size={40} />

                            <div className="text-right hidden sm:block">
                                <p className="text-sm font-medium text-foreground">{user?.full_name || 'Guest User'}</p>
                                <p className="text-xs text-muted-foreground capitalize">{user?.role || 'Guest Access'}</p>
                            </div>

                            <button
                                onClick={logout}
                                className="btn-ghost flex items-center gap-2"
                            >
                                <LogOut className="w-4 h-4" />
                                <span className="hidden sm:inline">Logout</span>
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-4xl mx-auto px-6 py-8 relative min-h-[60vh]">

                    {/* Messages List (always rendered beneath the hero) */}
                    <div className="space-y-6">
                        <AnimatePresence>
                            {messages.map((message, index) => (
                                <motion.div
                                    key={message.id}
                                    initial={{ opacity: 0, y: 8, scale: 0.995 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: -6 }}
                                    transition={{ duration: 0.32, type: 'spring', stiffness: 300 }}
                                    className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start' } ${index === messages.length - 1 ? 'bounce-in' : ''}`}
                                >
                                    {message.role === 'assistant' && (
                                        <div className="w-8 h-8 bg-gradient-to-br from-gemini-600 to-gemini-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-gemini-500/30">
                                            <Sparkles className="w-4 h-4 text-white" />
                                        </div>
                                    )}

                                    <motion.div
                                        className={message.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}
                                        initial={{ y: 6 }}
                                        animate={{ y: 0 }}
                                        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                                    >
                                        <div className="whitespace-pre-wrap leading-relaxed">
                                            {message.role === 'assistant' ? (
                                                <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ''}</ReactMarkdown></div>
                                            ) : (
                                                <p>{message.content}</p>
                                            )}

                                            {streaming && index === messages.length - 1 && (
                                                <span className="inline-block w-1 h-5 bg-gemini-600 ml-1 animate-pulse" />
                                            )}
                                        </div>
                                        <p className="text-xs opacity-60 mt-2">
                                            {message.timestamp.toLocaleTimeString([], {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                        </p>
                                    </motion.div>

                                    {message.role === 'user' && (
                                        <div className="w-8 h-8 bg-gradient-to-br from-gray-600 to-gray-500 rounded-xl flex items-center justify-center flex-shrink-0">
                                            <UserIcon className="w-4 h-4 text-white" />
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Welcome Hero Overlay - centered, visible only when no messages */}
                    <AnimatePresence>
                        {messages.length === 0 && (
                            <motion.div
                                key="welcome-hero"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -12 }}
                                transition={{ duration: 0.5 }}
                                className="absolute inset-0 flex items-center justify-center pointer-events-none"
                            >
                                <div className="pointer-events-auto text-center space-y-6 px-6">
                                    <h1 className="text-4xl font-semibold text-gradient">
                                        Hi {user?.full_name ? user.full_name.split(' ')[0] : 'there'}
                                    </h1>

                                    <div className="max-w-xl">
                                        <p className="text-xl text-gray-300">
                                            {profile?.business_description || 'We help businesses with smart AI assistants.'}
                                        </p>
                                        {profile?.welcome_message && (
                                            <p className="text-md text-gray-400 mt-2 italic">
                                                {profile.welcome_message}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex gap-3 justify-center mt-4">
                                        {suggestedQuestions.slice(0, 3).map((q, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleSend(q)}
                                                className="px-4 py-2 border border-gray-700 rounded-full hover:bg-gray-800 text-sm transition"
                                            >
                                                {q}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Input Area */}
            <div className="border-t border-border bg-card">
                <div className="max-w-4xl mx-auto px-6 py-4">
                    <div className="relative">
                        <div className="glass rounded-3xl shadow-lg border-2 border-border focus-within:border-gemini-500 transition-all duration-200">
                            <textarea
                                ref={inputRef}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Ask me anything..."
                                rows={1}
                                disabled={loading}
                                className="w-full px-6 py-4 pr-14 bg-transparent resize-none focus:outline-none placeholder:text-muted-foreground max-h-32"
                                style={{
                                    minHeight: '56px',
                                    maxHeight: '128px',
                                }}
                            />
                            <button
                                onClick={() => handleSend()}
                                disabled={!input.trim() || loading}
                                className="absolute right-3 bottom-3 w-10 h-10 bg-gradient-to-br from-gemini-600 to-gemini-500 rounded-xl flex items-center justify-center shadow-lg shadow-gemini-500/30 hover:shadow-xl hover:shadow-gemini-500/40 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
                            >
                                {loading ? (
                                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                                ) : (
                                    <Send className="w-5 h-5 text-white" />
                                )}
                            </button>
                        </div>
                        <p className="text-xs text-muted-foreground text-center mt-3">
                            AI can make mistakes. Consider checking important information.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Chat;
