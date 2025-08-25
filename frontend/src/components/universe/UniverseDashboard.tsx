import React, { useState, useEffect } from 'react';
import { PlusIcon, SearchIcon, SettingsIcon, MessageSquareIcon } from 'lucide-react';
import { Universe, Asset, UniverseDashboardProps } from '../../types';
import { universeAPI } from '../../services/api';
import UniverseTable from './UniverseTable';
import UniverseEditor from './UniverseEditor';
import AssetSearch from './AssetSearch';
import BulkOperations from './BulkOperations';
import UniverseAssetTable from './UniverseAssetTable';

const UniverseDashboard: React.FC<UniverseDashboardProps> = ({ 
  chatMode = false, 
  onToggleChatMode 
}) => {
  // State management
  const [universes, setUniverses] = useState<Universe[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUniverse, setSelectedUniverse] = useState<Universe | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isBulkOperationsOpen, setIsBulkOperationsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load universes on component mount
  useEffect(() => {
    // Small delay to ensure token is set in development
    if (process.env.NODE_ENV === 'development') {
      setTimeout(() => {
        console.log('🔄 UniverseDashboard: Checking token before loading universes...');
        console.log('🔍 Token exists:', !!localStorage.getItem('access_token'));
        loadUniverses();
      }, 500);
    } else {
      loadUniverses();
    }
  }, []);

  const loadUniverses = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🌐 Making API call to load universes...');
      console.log('🔑 Token being used:', localStorage.getItem('access_token')?.substring(0, 50) + '...');
      
      const result = await universeAPI.list();
      
      console.log('📊 API Response:', result);
      
      if (result.success && result.data) {
        setUniverses(result.data);
        console.log('✅ Universes loaded successfully:', result.data.length);
      } else {
        console.error('❌ API returned error:', result.message);
        setError(result.message || 'Failed to load universes');
      }
    } catch (error) {
      console.error('❌ Network/API Error:', error);
      setError('Network error loading universes');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUniverse = () => {
    setSelectedUniverse(null);
    setIsEditorOpen(true);
  };

  const handleEditUniverse = (universe: Universe) => {
    setSelectedUniverse(universe);
    setIsEditorOpen(true);
  };

  const handleDeleteUniverse = async (universe: Universe) => {
    if (!window.confirm(`Are you sure you want to delete "${universe.name}"?`)) {
      return;
    }

    try {
      const result = await universeAPI.delete(universe.id);
      if (result.success) {
        await loadUniverses(); // Refresh the list
      } else {
        setError(result.message || 'Failed to delete universe');
      }
    } catch (error) {
      console.error('Failed to delete universe:', error);
      setError('Network error deleting universe');
    }
  };

  const handleUniverseSelect = (universe: Universe) => {
    setSelectedUniverse(universe);
  };

  const handleEditorClose = async (shouldRefresh = false) => {
    setIsEditorOpen(false);
    setSelectedUniverse(null);
    
    if (shouldRefresh) {
      await loadUniverses();
    }
  };

  const handleAssetSelect = (asset: Asset) => {
    // This will be used for adding assets to universes
    console.log('Asset selected:', asset);
  };

  const handleBulkOperations = () => {
    setIsBulkOperationsOpen(true);
  };

  return (
    <div className="min-h-screen bg-gray-50" data-testid="universe-dashboard">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">
                Investment Universes
              </h1>
              <p className="mt-1 text-sm text-gray-500" data-testid="page-description">
                Manage your asset universes and build investment strategies
              </p>
            </div>
            
            <div className="flex space-x-3">
              {/* AI Chat Toggle */}
              {onToggleChatMode && (
                <button
                  onClick={onToggleChatMode}
                  className={`inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium transition-colors ${
                    chatMode
                      ? 'border-primary-300 bg-primary-50 text-primary-700 hover:bg-primary-100'
                      : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <MessageSquareIcon className="w-4 h-4 mr-2" />
                  {chatMode ? 'Exit Chat Mode' : 'AI Assistant'}
                </button>
              )}

              {/* Bulk Operations */}
              <button
                onClick={handleBulkOperations}
                className="btn-secondary"
              >
                <SettingsIcon className="w-4 h-4 mr-2" />
                Bulk Operations
              </button>

              {/* Asset Search */}
              <button
                onClick={() => setIsSearchOpen(true)}
                className="btn-secondary"
              >
                <SearchIcon className="w-4 h-4 mr-2" />
                Search Assets
              </button>

              {/* Create Universe */}
              <button
                onClick={handleCreateUniverse}
                className="btn-primary"
                data-testid="create-universe-button"
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                Create Universe
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded-lg">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium">Error</h3>
                <div className="mt-2 text-sm">
                  <p>{error}</p>
                </div>
                <div className="mt-4">
                  <button
                    onClick={() => setError(null)}
                    className="text-sm bg-error-100 hover:bg-error-200 text-error-800 px-2 py-1 rounded"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* AI Chat Mode Banner */}
        {chatMode && (
          <div className="mb-6 bg-primary-50 border border-primary-200 text-primary-700 px-4 py-3 rounded-lg">
            <div className="flex items-center">
              <MessageSquareIcon className="w-5 h-5 mr-3" />
              <div>
                <h3 className="text-sm font-medium">AI Assistant Mode Active</h3>
                <p className="text-sm mt-1">
                  You can now ask me to create universes, search for assets, or manage your investment strategies using natural language.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Universe Table */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">
              Your Universes ({universes.length})
            </h2>
          </div>
          <div className="card-body">
            <UniverseTable
              universes={universes}
              loading={loading}
              onUniverseSelect={handleUniverseSelect}
              onUniverseEdit={handleEditUniverse}
              onUniverseDelete={handleDeleteUniverse}
            />
          </div>
        </div>

        {/* Selected Universe Details */}
        {selectedUniverse && !isEditorOpen && (
          <div className="mt-8 card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">
                {selectedUniverse.name}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {selectedUniverse.description || 'No description'}
              </p>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-gray-900">
                    {selectedUniverse.asset_count || 0}
                  </div>
                  <div className="text-sm text-gray-500">Assets</div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-gray-900">
                    {selectedUniverse.turnover_rate 
                      ? `${(selectedUniverse.turnover_rate * 100).toFixed(1)}%`
                      : 'N/A'
                    }
                  </div>
                  <div className="text-sm text-gray-500">Turnover Rate</div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-gray-900">
                    {selectedUniverse.last_screening_date 
                      ? new Date(selectedUniverse.last_screening_date).toLocaleDateString()
                      : 'Never'
                    }
                  </div>
                  <div className="text-sm text-gray-500">Last Updated</div>
                </div>
              </div>

              {/* Asset Table with Inline Editing (Sprint 2 Step 2) */}
              <UniverseAssetTable
                universe={selectedUniverse}
                onUniverseUpdate={loadUniverses}
              />
            </div>
          </div>
        )}
      </div>

      {/* Modals and Slide-outs */}
      {isEditorOpen && (
        <UniverseEditor
          universe={selectedUniverse}
          isOpen={isEditorOpen}
          onClose={handleEditorClose}
        />
      )}

      {isSearchOpen && (
        <AssetSearch
          onAssetSelect={handleAssetSelect}
          onClose={() => setIsSearchOpen(false)}
        />
      )}

      {isBulkOperationsOpen && (
        <BulkOperations
          universes={universes}
          isOpen={isBulkOperationsOpen}
          onClose={() => setIsBulkOperationsOpen(false)}
          onRefresh={loadUniverses}
        />
      )}
    </div>
  );
};

export default UniverseDashboard;