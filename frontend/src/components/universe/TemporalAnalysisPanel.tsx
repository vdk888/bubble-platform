import React, { useState, useEffect } from 'react';
import { 
  XIcon, 
  Clock4Icon, 
  BarChart3Icon, 
  ActivityIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CalendarDaysIcon,
  TrendingUpIcon,
  AlertCircleIcon,
  BuildingIcon,
  TableIcon
} from 'lucide-react';
import { Universe } from '../../types';
import { UniverseSnapshot, DateRange, TurnoverAnalysis as TurnoverAnalysisType } from '../../types/temporal';
import { useUniverseTimeline, useTurnoverAnalysis } from '../../hooks/useTemporalUniverse';
import TimelineView from './TimelineView';
import UniverseEvolution from './UniverseEvolution';
import TurnoverAnalysis from './TurnoverAnalysis';
import UniverseTimeline from './UniverseTimeline';
import AssetCompositionView from './AssetCompositionView';
import HorizontalTimelineTable from './HorizontalTimelineTable';
import SimpleTimelineTable from './SimpleTimelineTable';

interface TemporalAnalysisPanelProps {
  universe: Universe;
  view: 'timeline' | 'table' | 'simple-table' | 'evolution' | 'analysis' | 'assets' | null;
  onViewChange: (view: 'timeline' | 'table' | 'simple-table' | 'evolution' | 'analysis' | 'assets' | null) => void;
  onClose: () => void;
  className?: string;
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  disabled?: boolean;
}

const TabButton: React.FC<TabButtonProps> = ({ active, onClick, icon: Icon, children, disabled = false }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`
      inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg border transition-all duration-200
      ${active 
        ? 'bg-blue-600 text-white border-blue-600 shadow-sm' 
        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 hover:border-gray-400'
      }
      ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
    `}
  >
    <Icon className={`w-4 h-4 mr-2 ${active ? 'text-white' : 'text-gray-500'}`} />
    {children}
  </button>
);

const TemporalAnalysisPanel: React.FC<TemporalAnalysisPanelProps> = ({
  universe,
  view,
  onViewChange,
  onClose,
  className = ''
}) => {
  // State for timeline data
  const [selectedSnapshot, setSelectedSnapshot] = useState<UniverseSnapshot | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>({
    start_date: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 1 year ago
    end_date: new Date().toISOString().split('T')[0] // today
  });

  // Hooks for temporal data
  const { 
    timeline: snapshots, 
    loading: timelineLoading, 
    error: timelineError,
    metadata: timelineMetadata
  } = useUniverseTimeline(universe.id, {
    date_range: dateRange,
    frequency: 'monthly',
    include_turnover_analysis: true
  });

  const {
    analysis: turnoverAnalysis,
    loading: analysisLoading,
    error: analysisError
  } = useTurnoverAnalysis(snapshots, !timelineLoading && snapshots.length > 1);

  // Set default view if none provided
  useEffect(() => {
    if (view === null && snapshots.length > 0) {
      onViewChange('timeline');
    }
  }, [view, snapshots.length, onViewChange]);

  // Handle snapshot selection
  const handleSnapshotSelect = (snapshot: UniverseSnapshot) => {
    setSelectedSnapshot(snapshot);
    setSelectedDate(snapshot.snapshot_date);
  };

  // Handle date selection from timeline
  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    // Find matching snapshot or closest one
    const matchingSnapshot = snapshots.find(s => s.snapshot_date === date) ||
                           snapshots.find(s => new Date(s.snapshot_date) <= new Date(date));
    if (matchingSnapshot) {
      setSelectedSnapshot(matchingSnapshot);
    }
  };

  // Handle asset composition view request
  const handleAssetCompositionView = (snapshot: UniverseSnapshot) => {
    setSelectedSnapshot(snapshot);
    setSelectedDate(snapshot.snapshot_date);
    onViewChange('assets');
  };

  // Calculate panel statistics
  const panelStats = React.useMemo(() => {
    if (!snapshots.length || !timelineMetadata) {
      return {
        totalSnapshots: 0,
        avgTurnover: 0,
        dateSpan: 'No data',
        trendDirection: 'stable' as const
      };
    }

    const totalSnapshots = snapshots.length;
    const avgTurnover = timelineMetadata.avg_turnover_rate || 0;
    const earliestDate = new Date(snapshots[0]?.snapshot_date || Date.now());
    const latestDate = new Date(snapshots[snapshots.length - 1]?.snapshot_date || Date.now());
    const monthSpan = Math.round((latestDate.getTime() - earliestDate.getTime()) / (1000 * 60 * 60 * 24 * 30));
    
    // Calculate trend direction (simplified)
    const recentSnapshots = snapshots.slice(-3);
    const olderSnapshots = snapshots.slice(0, 3);
    const recentAvgTurnover = recentSnapshots.reduce((sum, s) => sum + (s.turnover_rate || 0), 0) / recentSnapshots.length;
    const olderAvgTurnover = olderSnapshots.reduce((sum, s) => sum + (s.turnover_rate || 0), 0) / olderSnapshots.length;
    
    const trendDirection = recentAvgTurnover > olderAvgTurnover * 1.1 ? 'increasing' : 
                          recentAvgTurnover < olderAvgTurnover * 0.9 ? 'decreasing' : 'stable';

    return {
      totalSnapshots,
      avgTurnover: avgTurnover * 100, // Convert to percentage
      dateSpan: `${monthSpan} month${monthSpan !== 1 ? 's' : ''}`,
      trendDirection
    };
  }, [snapshots, timelineMetadata]);

  // Handle view navigation
  const viewOrder = ['timeline', 'table', 'simple-table', 'evolution', 'analysis', 'assets'] as const;
  const currentViewIndex = view ? viewOrder.indexOf(view) : -1;

  const handlePrevView = () => {
    if (currentViewIndex > 0) {
      onViewChange(viewOrder[currentViewIndex - 1]);
    }
  };

  const handleNextView = () => {
    if (currentViewIndex >= 0 && currentViewIndex < viewOrder.length - 1) {
      onViewChange(viewOrder[currentViewIndex + 1]);
    }
  };

  const canGoBack = currentViewIndex > 0;
  const canGoForward = currentViewIndex >= 0 && currentViewIndex < viewOrder.length - 1;

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-200 ${className}`}>
      {/* Panel Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Clock4Icon className="w-6 h-6 text-blue-600" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Temporal Analysis
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                <span className="font-medium">{universe.name}</span>
                {panelStats.totalSnapshots > 0 && (
                  <span className="ml-2 text-xs">
                    • {panelStats.totalSnapshots} snapshots • {panelStats.dateSpan}
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Controls */}
        <div className="flex items-center space-x-3">
          {view && (
            <div className="flex items-center space-x-1 bg-white rounded-lg border border-gray-300 p-1">
              <button
                onClick={handlePrevView}
                disabled={!canGoBack}
                className={`p-1 rounded text-sm ${
                  canGoBack 
                    ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100' 
                    : 'text-gray-300 cursor-not-allowed'
                }`}
                title="Previous view"
              >
                <ChevronLeftIcon className="w-4 h-4" />
              </button>
              <span className="text-xs text-gray-500 px-2 font-medium">
                {currentViewIndex + 1} / {viewOrder.length}
              </span>
              <button
                onClick={handleNextView}
                disabled={!canGoForward}
                className={`p-1 rounded text-sm ${
                  canGoForward 
                    ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100' 
                    : 'text-gray-300 cursor-not-allowed'
                }`}
                title="Next view"
              >
                <ChevronRightIcon className="w-4 h-4" />
              </button>
            </div>
          )}

          <button 
            onClick={onClose} 
            className="text-gray-400 hover:text-gray-600 transition-colors duration-200 p-1 rounded-full hover:bg-gray-100"
            title="Close temporal analysis"
          >
            <XIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Quick Stats Bar */}
      {panelStats.totalSnapshots > 0 && (
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2">
                <CalendarDaysIcon className="w-4 h-4 text-blue-500" />
                <span className="text-gray-600">
                  <span className="font-medium text-gray-900">{panelStats.totalSnapshots}</span> snapshots
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <ActivityIcon className="w-4 h-4 text-orange-500" />
                <span className="text-gray-600">
                  Avg turnover: <span className="font-medium text-gray-900">{panelStats.avgTurnover.toFixed(1)}%</span>
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <TrendingUpIcon className={`w-4 h-4 ${
                  panelStats.trendDirection === 'increasing' ? 'text-red-500' : 
                  panelStats.trendDirection === 'decreasing' ? 'text-green-500' : 'text-gray-500'
                }`} />
                <span className="text-gray-600">
                  Trend: <span className={`font-medium ${
                    panelStats.trendDirection === 'increasing' ? 'text-red-700' : 
                    panelStats.trendDirection === 'decreasing' ? 'text-green-700' : 'text-gray-900'
                  }`}>
                    {panelStats.trendDirection}
                  </span>
                </span>
              </div>
            </div>

            {selectedSnapshot && (
              <div className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                Selected: {new Date(selectedSnapshot.snapshot_date).toLocaleDateString()}
              </div>
            )}
          </div>
        </div>
      )}

      {/* View Tabs */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          <div className="flex space-x-2">
            <TabButton 
              active={view === 'timeline'} 
              onClick={() => onViewChange('timeline')}
              icon={Clock4Icon}
              disabled={timelineLoading}
            >
              Timeline
            </TabButton>
            <TabButton 
              active={view === 'table'} 
              onClick={() => onViewChange('table')}
              icon={TableIcon}
              disabled={timelineLoading}
            >
              Grid Table
            </TabButton>
            <TabButton 
              active={view === 'simple-table'} 
              onClick={() => onViewChange('simple-table')}
              icon={TableIcon}
              disabled={timelineLoading}
            >
              Simple Table
            </TabButton>
            <TabButton 
              active={view === 'evolution'} 
              onClick={() => onViewChange('evolution')}
              icon={BarChart3Icon}
              disabled={timelineLoading}
            >
              Evolution
            </TabButton>
            <TabButton 
              active={view === 'analysis'} 
              onClick={() => onViewChange('analysis')}
              icon={ActivityIcon}
              disabled={timelineLoading || analysisLoading}
            >
              Analysis
            </TabButton>
            <TabButton 
              active={view === 'assets'} 
              onClick={() => onViewChange('assets')}
              icon={BuildingIcon}
              disabled={timelineLoading || !selectedSnapshot}
            >
              Assets
            </TabButton>
          </div>

          {/* Loading indicator */}
          {(timelineLoading || (analysisLoading && view === 'analysis')) && (
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span>
                {timelineLoading ? 'Loading temporal data...' : 'Calculating turnover analysis...'}
              </span>
            </div>
          )}
        </div>
      </div>
      
      {/* Content Area */}
      <div className="p-6">
        {/* Error States */}
        {(timelineError || analysisError) && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start space-x-2">
            <AlertCircleIcon className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-medium">Error loading temporal data</h4>
              <p className="text-sm mt-1">{timelineError || analysisError}</p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!timelineLoading && snapshots.length === 0 && !timelineError && (
          <div className="text-center py-12">
            <Clock4Icon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No temporal data available</h3>
            <p className="text-gray-500 mb-4">
              This universe doesn't have historical snapshots yet. 
              <br />Snapshots are created during universe updates and screening operations.
            </p>
            <div className="text-sm text-gray-400">
              Universe created: {new Date(universe.created_at).toLocaleDateString()}
            </div>
          </div>
        )}

        {/* Content based on selected view */}
        {snapshots.length > 0 && (
          <>
            {view === 'timeline' && (
              <div className="space-y-6">
                {/* Interactive Timeline Chart */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-900 mb-4 flex items-center">
                    <Clock4Icon className="w-4 h-4 mr-2 text-blue-500" />
                    Interactive Timeline
                  </h4>
                  <TimelineView
                    snapshots={snapshots}
                    selectedDate={selectedDate}
                    onDateSelect={handleDateSelect}
                    height={160}
                    showZoomControls={true}
                    highlightChanges={true}
                  />
                </div>

                {/* Timeline Table */}
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <UniverseTimeline
                    universe_id={universe.id}
                    snapshots={snapshots}
                    onSnapshotSelect={handleSnapshotSelect}
                    onAssetCompositionView={handleAssetCompositionView}
                    showTurnoverColumn={true}
                    showActionsColumn={true}
                  />
                </div>
              </div>
            )}

            {view === 'table' && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 flex items-center">
                  <TableIcon className="w-4 h-4 mr-2 text-blue-500" />
                  Portfolio Grid Table
                </h4>
                <div className="text-sm text-gray-600 mb-4">
                  View your portfolio composition across time periods. Each column represents a snapshot date, 
                  and each row shows an asset. Green dots indicate the asset was present in the portfolio.
                </div>
                <HorizontalTimelineTable
                  snapshots={snapshots}
                  onDateClick={(date, snapshot) => {
                    handleSnapshotSelect(snapshot);
                    handleDateSelect(date);
                  }}
                  onAssetClick={(asset, dates) => {
                    console.log(`Asset ${asset} appeared in snapshots:`, dates);
                    // Could show a modal or tooltip with asset timeline details
                  }}
                  maxDatesToShow={10}
                  className="shadow-sm"
                />
              </div>
            )}

            {view === 'simple-table' && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 flex items-center">
                  <TableIcon className="w-4 h-4 mr-2 text-blue-500" />
                  Simple Timeline Table
                </h4>
                <div className="text-sm text-gray-600 mb-4">
                  Clean timeline view with asset symbols arranged by date. Each column shows the portfolio 
                  composition at that point in time, with asset symbols displayed directly in the cells.
                </div>
                <SimpleTimelineTable
                  snapshots={snapshots}
                  onDateClick={(date, snapshot) => {
                    handleSnapshotSelect(snapshot);
                    handleDateSelect(date);
                  }}
                  maxDatesToShow={10}
                  className="shadow-sm"
                />
              </div>
            )}
            
            {view === 'evolution' && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 flex items-center">
                  <BarChart3Icon className="w-4 h-4 mr-2 text-blue-500" />
                  Universe Evolution Charts
                </h4>
                <UniverseEvolution
                  universeId={universe.id}
                  snapshots={snapshots}
                  height={500}
                  viewMode="asset_count"
                  onViewModeChange={() => {}}
                  className="bg-gray-50 rounded-lg"
                />
              </div>
            )}
            
            {view === 'analysis' && turnoverAnalysis && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 flex items-center">
                  <ActivityIcon className="w-4 h-4 mr-2 text-blue-500" />
                  Turnover Analysis & Trends
                </h4>
                <TurnoverAnalysis
                  universe_id={universe.id}
                  snapshots={snapshots}
                  className="bg-gray-50 rounded-lg"
                />
              </div>
            )}
            
            {view === 'assets' && selectedSnapshot && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-gray-900 flex items-center">
                    <BuildingIcon className="w-4 h-4 mr-2 text-blue-500" />
                    Asset Composition Details
                  </h4>
                  <div className="text-xs text-gray-500 bg-blue-50 px-2 py-1 rounded-full">
                    {new Date(selectedSnapshot.snapshot_date).toLocaleDateString()} • {selectedSnapshot.assets.length} assets
                  </div>
                </div>
                <AssetCompositionView
                  universeId={universe.id}
                  snapshot={selectedSnapshot}
                  selectedDate={selectedDate || undefined}
                  showMetadata={true}
                  showActions={true}
                  className="bg-gray-50 rounded-lg"
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TemporalAnalysisPanel;