import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../api';
import { Send, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { formatToBullets } from '../utils/formatResponse';
import GlobalHeader from '../components/GlobalHeader';
import Avatar from '../components/Avatar';
import { motion, AnimatePresence } from 'framer-motion';

const BusinessChat = () => {
    const { businessSlug } = useParams();
    const [business, setBusiness] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const messagesEndRef = useRef(null);
    const sessionKey = `session_${businessSlug}`;

    const suggestedQuestions = [
        "What can you help me with?",
        "Tell me about your capabilities",
        "How does this work?",
        "What information do you have?",
    ];

    const getSessionId = () => {
        const existing = sessionStorage.getItem(sessionKey);
        if (existing) return existing;
        const created = crypto.randomUUID();
        sessionStorage.setItem(sessionKey, created);
        return created;
    };

    useEffect(() => {
        const loadBusiness = async () => {
            try {
                const response = await api.get(`/public/business/${businessSlug}`);
                const b = response.data || {};
                // Normalize server response to canonical front-end fields
                const normalized = {
                    business_name: b.business_name || b.name || '',
                    business_description: b.business_description || b.welcome_message || b.intro || '',
                    business_logo_url: b.business_logo_url || b.logo_url || null,
                    ...b
                };
                // Keep a `name` alias for older components that read `business.name`
                normalized.name = normalized.business_name || normalized.name || '';
                setBusiness(normalized);
            } catch (error) {
                console.error('Business load failed', error);
                setBusiness(null);
            }
        };

        setMessages([]);
        loadBusiness();
    }, [businessSlug]);

    const computeLogoSrc = (b) => {
        if (!b) return null;
        const p = b.business_logo_url || null;
        if (!p) return null;
        return p.startsWith('http') ? p : `${api.defaults.baseURL}${p}`;
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Compute a safely truncated business description (limit 500 chars)
    // Accept multiple possible field names returned by different API versions
    const businessFullDesc = business ? (business.business_description || '') : '';
    const businessDesc = businessFullDesc && businessFullDesc.length > 350 ? businessFullDesc.slice(0, 347) + '...' : businessFullDesc;

    const handleSend = async () => {
        if (!input.trim() || loading || !business) return;

        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: input,
        };

        setMessages((prev) => [...prev, userMessage]);
        const outgoing = input;
        setInput('');
        setLoading(true);
        setStreaming(true);

        try {
            const response = await api.post(`/public/business/${businessSlug}/chat`, {
                message: outgoing,
                session_id: getSessionId(),
            });

            const fullText = response.data.response || '';
            // append assistant placeholder
            setMessages((prev) => [...prev, { id: Date.now() + 1, role: 'assistant', content: '' }]);

            for (let i = 0; i < fullText.length; i++) {
                const currentText = fullText.slice(0, i + 1);
                setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = { id: newMessages[newMessages.length - 1].id, role: 'assistant', content: currentText };
                    return newMessages;
                });
                await new Promise((resolve) => setTimeout(resolve, 18));
            }
            // Post-process to prefer bullet points when helpful
            const formatted = formatToBullets(fullText);
            if (formatted !== fullText) {
                setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = { id: newMessages[newMessages.length - 1].id, role: 'assistant', content: formatted };
                    return newMessages;
                });
            }
            setStreaming(false);
        } catch (error) {
            console.error('Chat failed', error);
            setMessages((prev) => [
                ...prev,
                {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: 'Sorry, I could not process that question right now.',
                    isError: true,
                },
            ]);
            setStreaming(false);
        } finally {
            setLoading(false);
        }
    };

    if (!business) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center text-muted-foreground">
                Business page not found.
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col bg-background">
            <GlobalHeader business={{ business_name: business.business_name || business.name, business_logo_url: business.business_logo_url || business.logo_url, welcome_message: business.business_description || business.welcome_message || business.intro }} rightElements={<><Link to="/" className="btn-ghost">Discovery</Link></>} />

            <div className="flex-1 overflow-y-auto">
                <div className="max-w-4xl mx-auto px-6 py-8 relative min-h-screen">

                    {/* Messages list always present */}
                    <div className="space-y-4">
                        {messages.map((message, index) => (
                            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} ${index === messages.length - 1 ? 'bounce-in' : ''}`}>
                                <div className={message.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                                    {message.role === 'assistant' ? (
                                        <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ''}</ReactMarkdown></div>
                                    ) : (
                                        <p>{message.content}</p>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Centered Welcome Hero overlay when no messages */}
                    <AnimatePresence>
                        {messages.length === 0 && (
                            <motion.div
                                key="business-hero"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -12 }}
                                transition={{ duration: 0.45 }}
                                className="absolute inset-0 flex items-center justify-center pointer-events-none z-50"
                            >
                                <div className="pointer-events-auto text-center space-y-6 px-6">
                                        <div className="mx-auto mb-4">
                                            <Avatar
                                                src={computeLogoSrc(business)}
                                                name={business.name}
                                                size={120}
                                                className="mx-auto"
                                            />
                                        </div>
                                        <h1 className="text-3xl font-bold text-gradient">
                                            {business.business_name || business.name || 'Welcome'}
                                        </h1>

                                        {/* Show business description when present, otherwise a short neutral prompt. */}
                                        <p className="text-lg text-muted-foreground max-w-xl mx-auto">{businessDesc || 'Ask a question to get started.'}</p>

                                    <div className="flex gap-3 justify-center mt-4">
                                        {suggestedQuestions.slice(0, 3).map((q, i) => (
                                            <button
                                                key={i}
                                                onClick={() => { setInput(q); handleSend(); }}
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

            <div className="border-t border-border bg-card">
                <div className="max-w-4xl mx-auto px-6 py-4 flex gap-3">
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Type your question about this business"
                        className="input-field"
                        disabled={loading}
                    />
                    <button onClick={handleSend} className="btn-primary" disabled={loading || !input.trim()}>
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default BusinessChat;
