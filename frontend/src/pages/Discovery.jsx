import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { Search, Sparkles } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';

const Discovery = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [searching, setSearching] = useState(false);

    const performSearch = async (q) => {
        if (!q || q.trim().length < 2) {
            setResults([]);
            return;
        }
        try {
            setSearching(true);
            const response = await api.get('/public/search', { params: { q } });
            setResults(response.data.businesses || []);
        } catch (error) {
            console.error('Search failed', error);
            setResults([]);
        } finally {
            setSearching(false);
        }
    };

    // Debounce the search as the user types
    useEffect(() => {
        const timer = setTimeout(() => {
            if (query && query.trim().length >= 2) {
                performSearch(query.trim());
            } else {
                setResults([]);
            }
        }, 350);
        return () => clearTimeout(timer);
    }, [query]);

    return (
        <div className="min-h-screen bg-background">
            <div className="max-w-5xl mx-auto px-6 py-10">
                <div className="flex items-center justify-between gap-4 mb-8">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-gemini-600 to-gemini-500 rounded-xl flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-foreground">Vyavasa.ai</h1>
                            <p className="text-sm text-muted-foreground">Discover business AI answering pages</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <ThemeToggle />
                        <Link to="/owner/auth" className="btn-ghost">Owner Login</Link>
                    </div>
                </div>

                <div className="card mb-6">
                    <div className="relative">
                        <Search className="w-5 h-5 text-muted-foreground absolute left-4 top-1/2 -translate-y-1/2" />
                        <input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && performSearch(query)}
                            placeholder="Search by name or description (type 2+ characters)"
                            className="input-field pl-12"
                        />
                    </div>
                    <button onClick={() => performSearch(query)} className="btn-primary mt-3">Search</button>
                </div>
                {query.trim().length < 2 ? (
                    <div className="card text-muted-foreground">Start typing (2+ characters) to find a business.</div>
                ) : searching ? (
                    <div className="text-muted-foreground">Searching...</div>
                ) : results.length === 0 ? (
                    <div className="card text-muted-foreground">No results found.</div>
                ) : (
                    <div className="grid gap-3">
                        {results.map((biz) => (
                            <div key={biz.id} className="card hover:border-gemini-300 transition-colors">
                                <h3 className="font-semibold text-foreground">{biz.name}</h3>
                                <p className="text-sm text-muted-foreground mt-1">{biz.intro || 'AI answering page'}</p>
                                <div className="mt-4">
                                    <Link to={`/${biz.slug}`} className="btn-primary inline-flex">Chat Now</Link>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Discovery;
