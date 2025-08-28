import React, { useState, useEffect, useCallback } from 'react';
import { PlusIcon, SearchIcon, SettingsIcon, MessageSquareIcon, Clock4Icon, BarChart3Icon, ActivityIcon, LayoutPanelTopIcon } from 'lucide-react';
import { Universe, Asset, UniverseDashboardProps } from '../../types';
import { UniverseSnapshot } from '../../types/temporal';
import { universeAPI } from '../../services/api';
import UniverseTable from './UniverseTable';
import UniverseEditor from './UniverseEditor';
import AssetSearch from './AssetSearch';
import BulkOperations from './BulkOperations';
import UniverseAssetTable from './UniverseAssetTable';
import UniverseTimeline from './UniverseTimeline';
import UniverseEvolution from './UniverseEvolution';
import TimelineView from './TimelineView';
import TurnoverAnalysis from './TurnoverAnalysis';
import TemporalAnalysisPanel from './TemporalAnalysisPanel';

const UniverseDashboard: React.FC<UniverseDashboardProps> = ({ 
  chatMode = false, 
  onToggleChatMode,
  enableTemporalMode = true,
  defaultTemporalMode = false,
  onTemporalModeChange
}) => {
  // State management
  const [universes, setUniverses] = useState<Universe[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUniverse, setSelectedUniverse] = useState<Universe | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isBulkOperationsOpen, setIsBulkOperationsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Enhanced temporal mode state
  const [temporalMode, setTemporalMode] = useState(defaultTemporalMode ?? false);
  const [selectedUniverseForTemporal, setSelectedUniverseForTemporal] = useState<Universe | null>(null);
  const [temporalView, setTemporalView] = useState<'timeline' | 'evolution' | 'analysis' | null>(null);
  const [temporalPanelLayout, setTemporalPanelLayout] = useState<'overlay' | 'sidebar' | 'modal'>('overlay');
  
  // Legacy state for backward compatibility
  const [selectedSnapshot, setSelectedSnapshot] = useState<UniverseSnapshot | null>(null);

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

  // Enhanced universe update handler that refreshes both list and selected universe
  const handleUniverseUpdate = async (updatedUniverseId?: string) => {
    try {
      console.log('🔄 Starting universe update synchronization...');
      
      // Always refresh the universe list first
      await loadUniverses();
      
      // If we have a selected universe, fetch its updated data
      if (selectedUniverse) {
        const targetId = updatedUniverseId || selectedUniverse.id;
        console.log('🔄 Refreshing selected universe data:', targetId);
        
        const result = await universeAPI.get(targetId);
        if (result.success && result.data) {
          // Update selected universe with fresh data from API
          setSelectedUniverse(result.data);
          console.log('✅ Selected universe refreshed with updated data:', {
            id: result.data.id,
            name: result.data.name,
            assetCount: result.data.asset_count || result.data.assets?.length || 0,
            assetsLength: result.data.assets?.length || 0
          });
        } else {
          console.warn('⚠️ Failed to refresh selected universe:', result.message);
          // Clear error after a delay to avoid persistent error state
          setError(`Warning: ${result.message || 'Could not refresh universe details'}`);
          setTimeout(() => setError(null), 3000);
        }
      }
      
      console.log('✅ Universe update synchronization completed');
    } catch (error) {
      console.error('❌ Error during universe update synchronization:', error);
      setError('Failed to refresh universe data. Please try refreshing the page.');
      // Auto-clear error after 5 seconds
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleAssetSelect = (asset: Asset) => {
    // This will be used for adding assets to universes
    console.log('Asset selected:', asset);
  };

  // Enhanced temporal mode handlers
  const handleTemporalModeToggle = useCallback((enabled?: boolean) => {
    const newMode = enabled !== undefined ? enabled : !temporalMode;
    setTemporalMode(newMode);
    
    if (!newMode) {
      // Clean up temporal state when disabled
      setSelectedUniverseForTemporal(null);
      setTemporalView(null);
      setSelectedSnapshot(null);
    }
    
    // Notify parent component
    onTemporalModeChange?.(newMode);
  }, [temporalMode, onTemporalModeChange]);

  const handleTimelineView = useCallback((universe: Universe) => {
    setSelectedUniverseForTemporal(universe);
    setTemporalView('timeline');
    
    // Ensure temporal mode is enabled
    if (!temporalMode) {
      handleTemporalModeToggle(true);
    }
  }, [temporalMode, handleTemporalModeToggle]);

  const handleTemporalAnalysis = useCallback((universe: Universe) => {
    setSelectedUniverseForTemporal(universe);
    setTemporalView('analysis');
    
    // Ensure temporal mode is enabled
    if (!temporalMode) {
      handleTemporalModeToggle(true);
    }
  }, [temporalMode, handleTemporalModeToggle]);

  const handleTemporalViewChange = useCallback((view: 'timeline' | 'evolution' | 'analysis' | null) => {
    setTemporalView(view);
  }, []);

  const handleTemporalPanelClose = useCallback(() => {
    setSelectedUniverseForTemporal(null);
    setTemporalView(null);
  }, []);

  // Legacy handlers for backward compatibility
  const handleSnapshotSelect = (snapshot: UniverseSnapshot) => {
    setSelectedSnapshot(snapshot);
  };

  const handleUniverseTimeline = (universe: Universe) => {
    handleTimelineView(universe);
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
              {/* Enhanced Temporal Mode Toggle */}
              {enableTemporalMode && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleTemporalModeToggle()}
                    className={`inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium transition-all duration-200 ${
                      temporalMode
                        ? 'border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100 shadow-sm'
                        : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                    title={temporalMode ? 'Exit temporal analysis mode' : 'Enable temporal analysis mode'}
                  >
                    <Clock4Icon className={`w-4 h-4 mr-2 ${temporalMode ? 'animate-pulse' : ''}`} />
                    {temporalMode ? 'Exit Temporal Mode' : 'Temporal Analysis'}
                  </button>
                  
                  {/* Panel Layout Toggle - only shown when temporal mode is active */}
                  {temporalMode && selectedUniverseForTemporal && (
                    <button
                      onClick={() => {
                        const layouts: Array<'overlay' | 'sidebar' | 'modal'> = ['overlay', 'sidebar', 'modal'];
                        const currentIndex = layouts.indexOf(temporalPanelLayout);
                        const nextLayout = layouts[(currentIndex + 1) % layouts.length];
                        setTemporalPanelLayout(nextLayout);
                      }}
                      className="inline-flex items-center px-3 py-2 border border-blue-200 bg-blue-50 text-blue-600 rounded-lg text-xs font-medium hover:bg-blue-100 transition-colors"
                      title={`Switch to ${temporalPanelLayout === 'overlay' ? 'sidebar' : temporalPanelLayout === 'sidebar' ? 'modal' : 'overlay'} layout`}
                    >
                      <LayoutPanelTopIcon className="w-3 h-3 mr-1" />
                      {temporalPanelLayout}
                    </button>
                  )}
                </div>
              )}
              
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

        {/* Enhanced Temporal Mode Banner */}
        {temporalMode && (
          <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 text-blue-700 px-6 py-4 rounded-lg shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Clock4Icon className="w-5 h-5 mr-3 animate-pulse" />
                <div>
                  <h3 className="text-sm font-medium text-blue-800">
                    Temporal Analysis Mode Active
                    {selectedUniverseForTemporal && (
                      <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                        {selectedUniverseForTemporal.name}
                      </span>
                    )}
                  </h3>
                  <p className="text-sm mt-1 text-blue-600">
                    {selectedUniverseForTemporal ? (
                      `Exploring ${selectedUniverseForTemporal.name}'s evolution over time with ${
                        temporalView === 'timeline' ? 'timeline view' :
                        temporalView === 'evolution' ? 'evolution charts' :
                        temporalView === 'analysis' ? 'turnover analysis' : 'detailed insights'
                      }.`
                    ) : (
                      'Select a universe to analyze historical snapshots, turnover patterns, and temporal trends.'
                    )}
                  </p>
                </div>
              </div>
              
              {/* Quick Actions */}
              {selectedUniverseForTemporal && (
                <div className="flex items-center space-x-2 ml-4">
                  <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                    {temporalPanelLayout} view
                  </span>
                  <button
                    onClick={handleTemporalPanelClose}
                    className="text-blue-500 hover:text-blue-700 transition-colors text-xs font-medium"
                  >
                    Close Analysis
                  </button>
                </div>
              )}
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

        {/* Main Content Layout with Enhanced Temporal Integration */}
        <div className={`${
          temporalMode && selectedUniverseForTemporal && temporalPanelLayout === 'sidebar'
            ? 'grid grid-cols-1 lg:grid-cols-3 gap-6'
            : ''
        }`}>
          
          {/* Primary Universe Table */}
          <div className={`${
            temporalMode && selectedUniverseForTemporal && temporalPanelLayout === 'sidebar'
              ? 'lg:col-span-2'
              : ''
          }`}>
            <div className="card">
              <div className="card-header">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-medium text-gray-900">
                    {temporalMode && selectedUniverseForTemporal ? (
                      <span className="flex items-center">
                        <span>Universe Analysis</span>
                        <span className="ml-2 text-sm font-normal text-gray-500">
                          ({universes.length} universe{universes.length !== 1 ? 's' : ''} total)
                        </span>
                      </span>
                    ) : (
                      `Your Universes (${universes.length})`
                    )}
                  </h2>
                  
                  {/* Temporal Panel Layout Indicator */}
                  {temporalMode && selectedUniverseForTemporal && (
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      <span>Temporal analysis active</span>
                      <div className={`w-2 h-2 rounded-full ${
                        temporalPanelLayout === 'overlay' ? 'bg-blue-400' :
                        temporalPanelLayout === 'sidebar' ? 'bg-green-400' : 'bg-purple-400'
                      } animate-pulse`}></div>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="card-body">
                <UniverseTable
                  universes={universes}
                  loading={loading}
                  onUniverseSelect={handleUniverseSelect}
                  onUniverseEdit={handleEditUniverse}
                  onUniverseDelete={handleDeleteUniverse}
                  showTemporalMode={enableTemporalMode}
                  temporalModeEnabled={temporalMode}
                  onTemporalModeToggle={handleTemporalModeToggle}
                  onTimelineView={handleTimelineView}
                  onTemporalAnalysis={handleTemporalAnalysis}
                />
              </div>
            </div>
          </div>

          {/* Sidebar Temporal Analysis Panel */}
          {temporalMode && selectedUniverseForTemporal && temporalPanelLayout === 'sidebar' && (
            <div className="lg:col-span-1">
              <TemporalAnalysisPanel
                universe={selectedUniverseForTemporal}
                view={temporalView}
                onViewChange={handleTemporalViewChange}
                onClose={handleTemporalPanelClose}
                className="sticky top-4"
              />
            </div>
          )}
        </div>

        {/* Overlay Temporal Analysis Panel */}
        {temporalMode && selectedUniverseForTemporal && temporalPanelLayout === 'overlay' && (
          <div className="mt-6">
            <TemporalAnalysisPanel
              universe={selectedUniverseForTemporal}
              view={temporalView}
              onViewChange={handleTemporalViewChange}
              onClose={handleTemporalPanelClose}
            />
          </div>
        )}

        {/* Modal Temporal Analysis Panel */}
        {temporalMode && selectedUniverseForTemporal && temporalPanelLayout === 'modal' && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
              <TemporalAnalysisPanel
                universe={selectedUniverseForTemporal}
                view={temporalView}
                onViewChange={handleTemporalViewChange}
                onClose={handleTemporalPanelClose}
                className="max-h-[90vh] overflow-y-auto"
              />
            </div>
          </div>
        )}

        {/* Selected Universe Details */}
        {selectedUniverse && !isEditorOpen && !temporalMode && (
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
                    {selectedUniverse.asset_count || selectedUniverse.assets?.length || 0}
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
                onUniverseUpdate={() => handleUniverseUpdate(selectedUniverse.id)}
              />
            </div>
          </div>
        )}
        
        {/* Selected Snapshot Details (Temporal Mode) */}
        {temporalMode && selectedSnapshot && (
          <div className="mt-8 card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">
                Snapshot Details - {new Date(selectedSnapshot.snapshot_date).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                Universe: {selectedUniverse?.name}
              </p>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-900">
                    {selectedSnapshot.assets.length}
                  </div>
                  <div className="text-sm text-blue-700">Total Assets</div>
                </div>
                
                {selectedSnapshot.turnover_rate && (
                  <div className="bg-red-50 rounded-lg p-4">
                    <div className="text-2xl font-bold text-red-900">
                      {(selectedSnapshot.turnover_rate * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-red-700">Turnover Rate</div>
                  </div>
                )}
                
                {selectedSnapshot.assets_added && selectedSnapshot.assets_added.length > 0 && (
                  <div className="bg-green-50 rounded-lg p-4">
                    <div className="text-2xl font-bold text-green-900">
                      {selectedSnapshot.assets_added.length}
                    </div>
                    <div className="text-sm text-green-700">Assets Added</div>
                  </div>
                )}
                
                {selectedSnapshot.assets_removed && selectedSnapshot.assets_removed.length > 0 && (
                  <div className="bg-orange-50 rounded-lg p-4">
                    <div className="text-2xl font-bold text-orange-900">
                      {selectedSnapshot.assets_removed.length}
                    </div>
                    <div className="text-sm text-orange-700">Assets Removed</div>
                  </div>
                )}
              </div>
              
              {/* Asset changes details */}
              {((selectedSnapshot.assets_added && selectedSnapshot.assets_added.length > 0) || 
                (selectedSnapshot.assets_removed && selectedSnapshot.assets_removed.length > 0)) && (
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                  {selectedSnapshot.assets_added && selectedSnapshot.assets_added.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-green-700 mb-3">Assets Added</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedSnapshot.assets_added.map((asset, index) => (
                          <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {asset}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {selectedSnapshot.assets_removed && selectedSnapshot.assets_removed.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-red-700 mb-3">Assets Removed</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedSnapshot.assets_removed.map((asset, index) => (
                          <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            {asset}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
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