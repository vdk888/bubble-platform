import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { 
  EditIcon, 
  TrashIcon, 
  EyeIcon, 
  Clock4Icon, 
  ToggleLeftIcon, 
  ToggleRightIcon, 
  CalendarDaysIcon,
  ChartBarIcon,
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircleIcon
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Universe, UniverseTableProps } from '../../types';
import { useUniverseTimeline } from '../../hooks/useTemporalUniverse';

const UniverseTable: React.FC<UniverseTableProps> = ({
  universes,
  loading,
  onUniverseSelect,
  onUniverseEdit,
  onUniverseDelete,
  showTemporalMode = false,
  temporalModeEnabled = false,
  onTemporalModeToggle,
  onTimelineView,
  onTemporalAnalysis,
}) => {
  // Temporal data storage for universes when temporal mode is enabled
  const [temporalData, setTemporalData] = useState<Record<string, {
    snapshot_count: number;
    total_snapshots: number;
    avg_turnover: number;
    last_snapshot_date: string;
    loading: boolean;
    error: string | null;
  }>>({});

  // Fetch temporal data for all universes when temporal mode is enabled
  const fetchTemporalData = useCallback(async () => {
    if (!temporalModeEnabled || universes.length === 0) {
      return;
    }

    // Prevent concurrent fetches for already loading universes
    const universesToFetch = universes.filter(u => !temporalData[u.id]?.loading);
    if (universesToFetch.length === 0) {
      return;
    }

    console.log('🔄 UniverseTable: Fetching temporal data for universes', {
      universeCount: universes.length,
      temporalModeEnabled
    });

    // Fetch temporal data for each universe that isn't already loading
    const temporalPromises = universesToFetch.map(async (universe) => {
      try {
        setTemporalData(prev => ({
          ...prev,
          [universe.id]: { ...prev[universe.id], loading: true, error: null }
        }));

        // Import the API function dynamically to avoid circular imports
        const { temporalUniverseAPI } = await import('../../services/api');
        const response = await temporalUniverseAPI.getTimeline(universe.id, {
          date_range: {
            start_date: new Date(Date.now() - 6 * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 6 months ago
            end_date: new Date().toISOString().split('T')[0] // today
          },
          frequency: 'monthly',
          show_empty_periods: false,
          include_turnover_analysis: true
        });

        if (response.success && response.metadata) {
          const metadata = response.metadata;
          const snapshots = response.data || [];
          
          // Calculate average turnover from snapshots
          const turnoverRates = snapshots
            .filter(s => s.turnover_rate !== null && s.turnover_rate !== undefined)
            .map(s => s.turnover_rate as number);
          const avgTurnover = turnoverRates.length > 0 
            ? turnoverRates.reduce((sum, rate) => sum + rate, 0) / turnoverRates.length
            : universe.turnover_rate || 0;

          const lastSnapshotDate = snapshots.length > 0 
            ? snapshots[snapshots.length - 1].snapshot_date 
            : universe.updated_at;

          setTemporalData(prev => ({
            ...prev,
            [universe.id]: {
              snapshot_count: snapshots.length,
              total_snapshots: metadata.total_snapshots,
              avg_turnover: avgTurnover,
              last_snapshot_date: lastSnapshotDate,
              loading: false,
              error: null
            }
          }));

          console.log('✅ UniverseTable: Temporal data loaded for universe', {
            universeId: universe.id,
            universeName: universe.name,
            snapshotCount: snapshots.length,
            totalSnapshots: metadata.total_snapshots
          });
        } else {
          throw new Error(response.message || 'Failed to fetch temporal data');
        }
      } catch (error: any) {
        console.error('❌ UniverseTable: Failed to fetch temporal data for universe', {
          universeId: universe.id,
          universeName: universe.name,
          error: error.message
        });
        
        setTemporalData(prev => ({
          ...prev,
          [universe.id]: {
            snapshot_count: 0,
            total_snapshots: 0,
            avg_turnover: universe.turnover_rate || 0,
            last_snapshot_date: universe.updated_at,
            loading: false,
            error: error.message
          }
        }));
      }
    });

    await Promise.all(temporalPromises);
  }, [temporalModeEnabled, universes.map(u => u.id).join(',')]); // Use stable universe ID string

  // Helper function for formatting dates
  const formatDate = useCallback((dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }, []);

  // Get temporal metadata for a specific universe
  const getTemporalMetadata = useCallback((universe: Universe) => {
    const data = temporalData[universe.id];
    if (!data) {
      return {
        snapshot_count: 0,
        avg_turnover: universe.turnover_rate || 0,
        last_snapshot_date: universe.updated_at,
        loading: temporalModeEnabled, // Only show loading if temporal mode is enabled
        error: null,
        tooltip: temporalModeEnabled ? 'Loading temporal data...' : 'Temporal mode disabled'
      };
    }

    return {
      snapshot_count: data.total_snapshots, // Use total_snapshots from API metadata
      avg_turnover: data.avg_turnover,
      last_snapshot_date: data.last_snapshot_date,
      loading: data.loading,
      error: data.error,
      tooltip: data.error 
        ? `Error loading temporal data: ${data.error}`
        : `${data.total_snapshots} temporal snapshots tracked since ${formatDate(universe.created_at)}`
    };
  }, [temporalData, temporalModeEnabled, formatDate]);

  // Fetch temporal data when temporal mode is enabled or universes change
  useEffect(() => {
    if (temporalModeEnabled) {
      fetchTemporalData();
    } else {
      // Clear temporal data when temporal mode is disabled
      setTemporalData({});
    }
  }, [fetchTemporalData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <span className="ml-3 text-gray-600">Loading universes...</span>
      </div>
    );
  }

  if (universes.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto h-12 w-12 text-gray-400">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
        </div>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No universes</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by creating your first investment universe.
        </p>
      </div>
    );
  }

  const getStatusBadge = (universe: Universe) => {
    if (!universe.is_active) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
          Inactive
        </span>
      );
    }

    const assetCount = universe.asset_count || 0;
    if (assetCount === 0) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-100 text-warning-800">
          Empty
        </span>
      );
    }

    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-100 text-success-800">
        Active
      </span>
    );
  };

  // Enhanced turnover badge component with better styling
  const TurnoverBadge: React.FC<{ rate: number | null | undefined; className?: string }> = ({ rate, className = '' }) => {
    if (!rate) return null;
    
    const percentage = rate * 100;
    let badgeColor = '';
    let label = '';
    let icon: React.ReactNode = null;
    
    if (percentage > 20) {
      badgeColor = 'bg-red-100 text-red-800 border-red-200';
      label = `${percentage.toFixed(1)}% High`;
      icon = <AlertTriangleIcon className="h-3 w-3" />;
    } else if (percentage > 10) {
      badgeColor = 'bg-yellow-100 text-yellow-800 border-yellow-200';
      label = `${percentage.toFixed(1)}% Med`;
      icon = <ActivityIcon className="h-3 w-3" />;
    } else {
      badgeColor = 'bg-green-100 text-green-800 border-green-200';
      label = `${percentage.toFixed(1)}% Low`;
      icon = <CheckCircleIcon className="h-3 w-3" />;
    }
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full border ${badgeColor} ${className}`}>
        {icon}
        {label}
      </span>
    );
  };


  return (
    <div className="overflow-hidden">
      {/* Enhanced Temporal mode toggle */}
      {showTemporalMode && onTemporalModeToggle && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-3 border-b border-blue-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => onTemporalModeToggle(!temporalModeEnabled)}
                className="flex items-center space-x-2 text-sm font-medium transition-colors duration-200"
                aria-label={temporalModeEnabled ? 'Disable temporal mode' : 'Enable temporal mode'}
              >
                {temporalModeEnabled ? (
                  <ToggleRightIcon className="w-5 h-5 text-blue-600" />
                ) : (
                  <ToggleLeftIcon className="w-5 h-5 text-gray-400 hover:text-blue-600" />
                )}
                <span className={temporalModeEnabled ? 'text-blue-700' : 'text-gray-700 hover:text-blue-700'}>
                  Temporal Mode
                </span>
              </button>
              <div className="text-xs font-medium">
                {temporalModeEnabled ? (
                  <span className="text-blue-600">📊 Viewing historical snapshots and turnover trends</span>
                ) : (
                  <span className="text-gray-500">📋 Viewing current universe state</span>
                )}
              </div>
            </div>
            
            {temporalModeEnabled && (
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-1 text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                  <CalendarDaysIcon className="w-3 h-3" />
                  <span>Timeline Active</span>
                </div>
                <div className="text-xs text-gray-600">
                  {universes.length} universe{universes.length !== 1 ? 's' : ''} with temporal data
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Assets
              </th>
              {temporalModeEnabled && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <div className="flex items-center space-x-1">
                    <CalendarDaysIcon className="w-3 h-3" />
                    <span>Snapshots</span>
                  </div>
                </th>
              )}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center space-x-1">
                  <ActivityIcon className="w-3 h-3" />
                  <span>{temporalModeEnabled ? 'Avg Turnover' : 'Turnover'}</span>
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {temporalModeEnabled ? 'First Snapshot' : 'Created'}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Updated
              </th>
              <th className="relative px-6 py-3">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {universes.map((universe) => {
              const temporalMetadata = getTemporalMetadata(universe);
              
              return (
              <tr 
                key={universe.id}
                className="hover:bg-gray-50 cursor-pointer transition-colors duration-150"
                onClick={() => onUniverseSelect(universe)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {universe.name}
                    </div>
                    {universe.description && (
                      <div className="text-sm text-gray-500 truncate max-w-xs">
                        {universe.description}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {universe.asset_count || 0}
                  </div>
                </td>
                {temporalModeEnabled && temporalMetadata && (
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      <CalendarDaysIcon className="h-4 w-4 text-blue-500" />
                      {temporalMetadata.loading ? (
                        <div className="flex items-center space-x-1">
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                          <span className="text-xs text-gray-500">Loading...</span>
                        </div>
                      ) : temporalMetadata.error ? (
                        <span className="text-sm font-medium text-red-600" title={temporalMetadata.error}>
                          Error
                        </span>
                      ) : (
                        <>
                          <span className="text-sm font-medium text-gray-900">
                            {temporalMetadata.snapshot_count}
                          </span>
                          <div 
                            className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"
                            title={temporalMetadata.tooltip}
                          ></div>
                        </>
                      )}
                    </div>
                  </td>
                )}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    {temporalModeEnabled ? (
                      // In temporal mode, show enhanced turnover with badge
                      <TurnoverBadge 
                        rate={temporalMetadata?.avg_turnover || universe.turnover_rate}
                        className="min-w-max"
                      />
                    ) : (
                      // Standard mode shows simple percentage
                      <span className="text-sm text-gray-900">
                        {universe.turnover_rate 
                          ? `${(universe.turnover_rate * 100).toFixed(1)}%`
                          : 'N/A'
                        }
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(universe)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {temporalModeEnabled ? (
                    <div className="flex items-center space-x-1">
                      <CalendarDaysIcon className="w-3 h-3 text-blue-400" />
                      <span className="font-medium">{formatDate(universe.created_at)}</span>
                    </div>
                  ) : (
                    formatDate(universe.created_at)
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {temporalModeEnabled && temporalMetadata ? (
                    temporalMetadata.loading ? (
                      <div className="flex items-center space-x-1">
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                        <span className="text-xs text-gray-500">Loading...</span>
                      </div>
                    ) : temporalMetadata.error ? (
                      <span className="text-xs text-red-600">Error loading data</span>
                    ) : (
                      <div className="flex flex-col">
                        <span className="font-medium">
                          {temporalMetadata.last_snapshot_date 
                            ? formatDistanceToNow(new Date(temporalMetadata.last_snapshot_date)) + ' ago'
                            : 'Unknown'
                          }
                        </span>
                        <span className="text-xs text-gray-400">
                          {temporalMetadata.last_snapshot_date 
                            ? formatDate(temporalMetadata.last_snapshot_date)
                            : 'No date available'
                          }
                        </span>
                      </div>
                    )
                  ) : (
                    formatDate(universe.updated_at)
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex items-center justify-end space-x-2">
                    {/* Standard actions */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onUniverseSelect(universe);
                      }}
                      className="text-primary-600 hover:text-primary-900 transition-colors duration-150"
                      title="View Universe"
                    >
                      <EyeIcon className="h-4 w-4" />
                    </button>
                    
                    {/* Temporal actions - only shown when temporal mode is enabled */}
                    {temporalModeEnabled && (
                      <>
                        {onTimelineView && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onTimelineView(universe);
                            }}
                            className="text-blue-600 hover:text-blue-900 transition-colors duration-150"
                            title="View Timeline"
                            aria-label="View Timeline"
                          >
                            <ChartBarIcon className="h-4 w-4" />
                          </button>
                        )}
                        {onTemporalAnalysis && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onTemporalAnalysis(universe);
                            }}
                            className="text-purple-600 hover:text-purple-900 transition-colors duration-150"
                            title="Temporal Analysis"
                            aria-label="Temporal Analysis"
                          >
                            <ActivityIcon className="h-4 w-4" />
                          </button>
                        )}
                      </>
                    )}
                    
                    {/* Standard edit/delete actions */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onUniverseEdit(universe);
                      }}
                      className="text-primary-600 hover:text-primary-900 transition-colors duration-150"
                      title="Edit Universe"
                    >
                      <EditIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onUniverseDelete(universe);
                      }}
                      className="text-error-600 hover:text-error-900 transition-colors duration-150"
                      title="Delete Universe"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UniverseTable;