import React, { useEffect, useState } from 'react';
import api from '../api';

const BusinessProfileSettings = ({ initialProfile = {}, onSaved = null }) => {
    const [tempProfile, setTempProfile] = useState({
        business_name: initialProfile.business_name || '',
        business_description: initialProfile.business_description || initialProfile.intro || '',
        website_url: initialProfile.website_url || '',
    });
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        setTempProfile({
            business_name: initialProfile.business_name || '',
            business_description: initialProfile.business_description || initialProfile.intro || '',
            website_url: initialProfile.website_url || '',
        });
    }, [initialProfile]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        if (name === 'business_description') {
            if (value.length > 350) {
                setTempProfile((p) => ({ ...p, [name]: value.slice(0, 350) }));
                return;
            }
        }
        setTempProfile((p) => ({ ...p, [name]: value }));
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const payload = {
                business_name: tempProfile.business_name,
                business_description: tempProfile.business_description,
                website_url: tempProfile.website_url || null,
            };
            await api.put('/owner/profile', payload);
            if (onSaved) onSaved(resp.data);
            alert('Profile saved');
        } catch (err) {
            console.error('Save failed', err);
            alert('Failed to save profile');
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancel = () => {
        setTempProfile({
            business_name: initialProfile.business_name || '',
            business_description: initialProfile.business_description || initialProfile.intro || '',
            website_url: initialProfile.website_url || '',
        });
    };

    return (
        <div className="glass p-6 rounded-3xl border border-indigo-500/30">
            <h2 className="text-xl font-bold mb-4">Business Profile</h2>
            <div className="space-y-4">
                <input
                    name="business_name"
                    value={tempProfile.business_name}
                    onChange={handleChange}
                    className="input-field"
                    placeholder="Business Name"
                />

                <input
                    name="website_url"
                    value={tempProfile.website_url}
                    onChange={handleChange}
                    className="input-field"
                    placeholder="Website (optional)"
                />

                <textarea
                    name="business_description"
                    value={tempProfile.business_description}
                    onChange={handleChange}
                    className="input-field h-32"
                    placeholder="Business Description (Max 350 chars)"
                />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div>This text appears on the public business page and chat hero.</div>
                    <div>{(tempProfile.business_description || '').length}/350 chars</div>
                </div>

                <div className="flex gap-3 mt-2">
                    <button onClick={handleSave} disabled={isSaving} className="btn-primary">
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button onClick={handleCancel} className="btn-ghost">Cancel</button>
                </div>
            </div>
        </div>
    );
};

export default BusinessProfileSettings;
