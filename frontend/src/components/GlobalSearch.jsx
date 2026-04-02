import React, { useState, useEffect, useRef } from 'react';
import { Search, X, User, Briefcase, FileText, Ticket, Package } from 'lucide-react';
import { Input } from './ui/input';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const GlobalSearch = ({ onNavigate }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  const token = localStorage.getItem('token');

  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl+K or Cmd+K to open search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
      // Escape to close
      if (e.key === 'Escape') {
        setIsOpen(false);
        setQuery('');
        setResults([]);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const searchTimer = setTimeout(async () => {
      if (query.length >= 2) {
        setLoading(true);
        try {
          const response = await axios.get(`${API_URL}/api/search/quick?q=${encodeURIComponent(query)}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setResults(response.data);
        } catch (error) {
          console.error('Search error:', error);
          setResults([]);
        }
        setLoading(false);
      } else {
        setResults([]);
      }
    }, 300);

    return () => clearTimeout(searchTimer);
  }, [query, token]);

  const getIcon = (type) => {
    const icons = {
      user: <User className="h-4 w-4" />,
      case: <Briefcase className="h-4 w-4" />,
      sale: <FileText className="h-4 w-4" />,
      ticket: <Ticket className="h-4 w-4" />,
      product: <Package className="h-4 w-4" />
    };
    return icons[type] || <FileText className="h-4 w-4" />;
  };

  const getTypeColor = (type) => {
    const colors = {
      user: 'bg-purple-100 text-purple-600',
      case: 'bg-blue-100 text-blue-600',
      sale: 'bg-green-100 text-green-600',
      ticket: 'bg-orange-100 text-orange-600',
      product: 'bg-indigo-100 text-indigo-600'
    };
    return colors[type] || 'bg-gray-100 text-gray-600';
  };

  const handleSelect = (result) => {
    setIsOpen(false);
    setQuery('');
    setResults([]);
    if (onNavigate) {
      onNavigate(result.url);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      {/* Search Trigger */}
      <button
        onClick={() => {
          setIsOpen(true);
          setTimeout(() => inputRef.current?.focus(), 100);
        }}
        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-500 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
      >
        <Search className="h-4 w-4" />
        <span className="hidden md:inline">Search...</span>
        <kbd className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-white rounded border">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      {/* Search Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/50">
          <div className="w-full max-w-2xl bg-white rounded-xl shadow-2xl overflow-hidden">
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b">
              <Search className="h-5 w-5 text-gray-400" />
              <Input
                ref={inputRef}
                type="text"
                placeholder="Search cases, tickets, users, products..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 border-none shadow-none focus-visible:ring-0 text-lg"
              />
              {query && (
                <button onClick={() => setQuery('')}>
                  <X className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                </button>
              )}
              <button
                onClick={() => {
                  setIsOpen(false);
                  setQuery('');
                  setResults([]);
                }}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                ESC
              </button>
            </div>

            {/* Results */}
            <div className="max-h-96 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
                </div>
              ) : results.length > 0 ? (
                <div className="py-2">
                  {results.map((result, idx) => (
                    <button
                      key={`${result.type}-${result.id}`}
                      onClick={() => handleSelect(result)}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                    >
                      <div className={`p-2 rounded-lg ${getTypeColor(result.type)}`}>
                        {getIcon(result.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">{result.title}</p>
                        <p className="text-sm text-gray-500 truncate">{result.subtitle}</p>
                      </div>
                      <span className="text-xs text-gray-400 capitalize">{result.type}</span>
                    </button>
                  ))}
                </div>
              ) : query.length >= 2 ? (
                <div className="py-8 text-center text-gray-500">
                  <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No results found for "{query}"</p>
                </div>
              ) : (
                <div className="py-8 text-center text-gray-500">
                  <p className="mb-2">Start typing to search</p>
                  <p className="text-sm">Search across cases, tickets, users, and products</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-gray-50 border-t text-xs text-gray-500 flex items-center gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-white rounded border">↓</kbd>
                to navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border">Enter</kbd>
                to select
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GlobalSearch;
