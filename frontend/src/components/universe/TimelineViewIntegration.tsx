import React, { useState, useCallback } from 'react';
import { UniverseSnapshot } from '../../types/temporal';
import { useUniverseTimeline } from '../../hooks/useTemporalUniverse';
import TimelineView from './TimelineView';
import UniverseTimeline from './UniverseTimeline';
import { CalendarIcon, TableIcon, TrendingUpIcon } from 'lucide-react';

interface TimelineViewIntegrationProps {
  universeId: string;
}

/**
 * TimelineViewIntegration - Demo component showing how to integrate TimelineView
 * with existing temporal universe components.
 * 
 * This component demonstrates:
 * - Using TimelineView alongside the existing UniverseTimeline table component
 * - Shared state management between timeline views
 * - Toggle between horizontal timeline and table views
 * - Real data integration with useUniverseTimeline hook
 * - Consistent date selection across components
 */
const TimelineViewIntegration: React.FC<TimelineViewIntegrationProps> = ({
  universeId
}) => {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'timeline' | 'table' | 'both'>('both');
  
  // Use the existing temporal universe hook
  const { 
    timeline, 
    loading, 
    error, 
    metadata 
  } = useUniverseTimeline(universeId, {
    date_range: {
      start_date: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0]
    },
    frequency: 'monthly',
    show_empty_periods: false,
    include_turnover_analysis: true
  });

  // Handle date selection from timeline
  const handleDateSelect = useCallback((date: string) => {
    setSelectedDate(date);
    console.log('📅 Date selected from timeline:', date);
    
    // Here you could trigger additional actions:
    // - Fetch detailed snapshot data for the selected date
    // - Update other components with the selected snapshot
    // - Navigate to a detailed view
    
    // Example: Find the selected snapshot and log its details
    const selectedSnapshot = timeline.find(s => s.snapshot_date === date);
    if (selectedSnapshot) {
      console.log('📊 Selected snapshot details:', {
        assetCount: selectedSnapshot.assets.length,
        turnoverRate: selectedSnapshot.turnover_rate,
        assetsAdded: selectedSnapshot.assets_added?.length || 0,
        assetsRemoved: selectedSnapshot.assets_removed?.length || 0
      });
    }
  }, [timeline]);

  // Handle snapshot selection from table
  const handleSnapshotSelect = useCallback((snapshot: UniverseSnapshot) => {
    setSelectedDate(snapshot.snapshot_date);
    console.log('📋 Snapshot selected from table:', snapshot.id);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <CalendarIcon className="h-5 w-5 text-red-400" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Timeline Integration Error
            </h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* View Mode Selector */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-medium text-gray-900">
              Universe Timeline Views
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Interactive timeline navigation for universe evolution
            </p>
          </div>
          
          {/* View mode toggle */}
          <div className="flex items-center bg-gray-100 rounded-md p-1">
            <button
              onClick={() => setViewMode('timeline')}
              className={`px-3 py-2 text-sm font-medium rounded transition-colors ${
                viewMode === 'timeline'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
              }`}
            >
              <TrendingUpIcon className="w-4 h-4 mr-1 inline" />
              Timeline
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-2 text-sm font-medium rounded transition-colors ${
                viewMode === 'table'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
              }`}
            >
              <TableIcon className="w-4 h-4 mr-1 inline" />
              Table
            </button>
            <button
              onClick={() => setViewMode('both')}
              className={`px-3 py-2 text-sm font-medium rounded transition-colors ${
                viewMode === 'both'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
              }`}
            >
              Both
            </button>
          </div>
        </div>

        {/* Selected date info */}
        {selectedDate && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-center">
              <CalendarIcon className="w-4 h-4 text-blue-600 mr-2" />
              <span className="text-sm text-blue-800">
                Selected: {new Date(selectedDate).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </span>
              {timeline.find(s => s.snapshot_date === selectedDate) && (
                <span className="ml-4 text-xs text-blue-600">
                  {timeline.find(s => s.snapshot_date === selectedDate)?.assets.length} assets
                  {timeline.find(s => s.snapshot_date === selectedDate)?.turnover_rate && (
                    <span className="ml-2">
                      ({(timeline.find(s => s.snapshot_date === selectedDate)!.turnover_rate! * 100).toFixed(1)}% turnover)
                    </span>
                  )}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Interactive Horizontal Timeline */}
      {(viewMode === 'timeline' || viewMode === 'both') && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-md font-medium text-gray-900">
              Interactive Timeline View
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Click markers to select dates, use zoom controls to change time range, hover for details
            </p>
          </div>
          <div className="p-4">
            <TimelineView
              snapshots={timeline}
              selectedDate={selectedDate}
              onDateSelect={handleDateSelect}
              highlightChanges={true}
              height={160}
              showZoomControls={true}
            />
          </div>
        </div>
      )}

      {/* Traditional Table View */}
      {(viewMode === 'table' || viewMode === 'both') && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-md font-medium text-gray-900">
              Timeline Table View
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Detailed tabular view with sorting and filtering capabilities
            </p>
          </div>
          <UniverseTimeline
            universe_id={universeId}
            snapshots={timeline}
            loading={loading}
            error={error || undefined}
            onSnapshotSelect={handleSnapshotSelect}
            showTurnoverColumn={true}
            showActionsColumn={true}
          />
        </div>
      )}

      {/* Integration Statistics */}
      {metadata && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Timeline Statistics
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {metadata.total_snapshots}
              </div>
              <div className="text-sm text-gray-500">Total Snapshots</div>
            </div>
            
            {metadata.avg_turnover_rate && (
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {(metadata.avg_turnover_rate * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500">Avg Turnover Rate</div>
              </div>
            )}
            
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {Math.floor(
                  (new Date(metadata.period_end).getTime() - new Date(metadata.period_start).getTime()) / 
                  (1000 * 60 * 60 * 24)
                )}
              </div>
              <div className="text-sm text-gray-500">Days Covered</div>
            </div>
          </div>

          {metadata.timeline_statistics && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">
                    Asset Count Range
                  </h4>
                  <p className="text-sm text-gray-600">
                    {metadata.timeline_statistics.min_asset_count} - {metadata.timeline_statistics.max_asset_count} assets
                    (avg: {metadata.timeline_statistics.avg_asset_count})
                  </p>
                </div>
                
                {metadata.timeline_statistics.most_stable_assets.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-2">
                      Most Stable Assets
                    </h4>
                    <p className="text-sm text-gray-600">
                      {metadata.timeline_statistics.most_stable_assets.slice(0, 3).join(', ')}
                      {metadata.timeline_statistics.most_stable_assets.length > 3 && 
                        ` +${metadata.timeline_statistics.most_stable_assets.length - 3} more`
                      }
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Usage Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-md font-medium text-blue-900 mb-3">
          How to Use Timeline Navigation
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-800">
          <div>
            <h4 className="font-medium mb-2">Interactive Timeline:</h4>
            <ul className="list-disc list-inside space-y-1">
              <li>Click markers to select specific dates</li>
              <li>Use zoom controls (1Y, 2Y, 5Y, All) to change time range</li>
              <li>Hover over markers for detailed tooltips</li>
              <li>Use arrow keys for keyboard navigation</li>
              <li>Drag timeline to pan when zoomed in</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">Visual Indicators:</h4>
            <ul className="list-disc list-inside space-y-1">
              <li><span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-1"></span>Green: Low turnover (&lt;10%)</li>
              <li><span className="inline-block w-2 h-2 bg-yellow-400 rounded-full mr-1"></span>Yellow: Moderate turnover (10-25%)</li>
              <li><span className="inline-block w-2 h-2 bg-red-400 rounded-full mr-1"></span>Red: High turnover (&gt;25%)</li>
              <li>Larger markers indicate higher turnover rates</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimelineViewIntegration;