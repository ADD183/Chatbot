import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import { Sparkles, LogOut } from 'lucide-react';
import Avatar from './Avatar';

const GlobalHeader = ({ profile: initialProfile = null, business = null, rightElements = null }) => {
    const { user, logout } = useAuth();
    const [profile, setProfile] = useState(initialProfile || business || null);

    useEffect(() => {
        if (business) {
            setProfile(business);
            return;
        }

        if (!initialProfile) {
            const fetchProfile = async () => {
                try {
                    const resp = await api.get('/api/v1/business/profile');
                    setProfile(resp.data || null);
                } catch (err) {
                    // not fatal for public pages
                    console.warn('GlobalHeader: failed to fetch profile', err);
                }
            };
            fetchProfile();
        }
    }, [initialProfile, business]);

    const logoSrc = profile?.business_logo_url
        ? (profile.business_logo_url.startsWith('http') ? profile.business_logo_url : `${api.defaults.baseURL}${profile.business_logo_url}`)
        : null;

    return (
        <nav className="glass border-b border-border px-6 py-4 sticky top-0 z-40">
            <div className="max-w-7xl mx-auto flex justify-between items-center">
                {/* Left: Vayvsai.ai branding */}
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-gemini-600 to-gemini-500 rounded-xl flex items-center justify-center shadow-lg shadow-gemini-500/20">
                        <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-foreground">Vayvsai.ai</h1>
                        <p className="text-xs text-muted-foreground">Smart business assistant</p>
                    </div>
                </div>

                {/* Right: user info and page controls; business logo is shown in-page hero */}
                <div className="flex items-center space-x-4">
                    {rightElements}

                    {/* Business logo + name on the right */}
                    {(logoSrc || profile?.business_name || profile?.name) && (
                        <div className="flex items-center gap-3">
                            <Avatar src={logoSrc} name={profile?.business_name || profile?.name} size={36} />
                            <div className="hidden sm:block text-sm font-medium text-foreground">{profile?.business_name || profile?.name}</div>
                        </div>
                    )}

                    <div className="h-8 w-px bg-gray-200 mx-2" />

                    <div className="text-right hidden sm:block">
                        <p className="text-sm font-semibold text-foreground">{user?.full_name}</p>
                        <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
                    </div>

                    <button onClick={logout} className="p-2 text-muted-foreground hover:text-red-500 transition-colors">
                        <LogOut className="w-5 h-5" />
                    </button>
                </div>
            </div>
        </nav>
    );
};

export default GlobalHeader;
