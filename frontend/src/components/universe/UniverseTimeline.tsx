import React, { useState, useCallback, useMemo } from 'react';
import { 
  CalendarIcon, 
  TrendingUpIcon, 
  TrendingDownIcon, 
  MinusIcon,
  EyeIcon,
  RefreshCwIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  FilterIcon,
  DownloadIcon,
  BuildingIcon
} from 'lucide-react';
import {
  UniverseSnapshot,
  UniverseTimelineProps,
  TimelineColumn,
  DateRange
} from '../../types/temporal';
import { useUniverseTimeline, useDateRangePresets } from '../../hooks/useTemporalUniverse';

/**
 * UniverseTimeline Component
 * 
 * Displays temporal universe evolution in a professional table format.
 * Features:
 * - Sortable columns (Date, Asset Count, Turnover, Added, Removed)
 * - Date range picker with presets
 * - Frequency selection (daily/weekly/monthly/quarterly)  
 * - Click handlers for snapshot details
 * - Loading states and error handling
 * - Export functionality
 */
const UniverseTimeline: React.FC<UniverseTimelineProps> = ({
  universe_id,
  snapshots: externalSnapshots,
  loading: externalLoading = false,
  error: externalError = null,
  onSnapshotSelect,
  onAssetCompositionView,
  onDateRangeChange,
  onFrequencyChange,
  showTurnoverColumn = true,
  showActionsColumn = true
}) => {
  // Local state for filtering and sorting
  const [sortColumn, setSortColumn] = useState<keyof UniverseSnapshot>('snapshot_date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [selectedDateRange, setSelectedDateRange] = useState<DateRange>(() => {
    const now = new Date();
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(now.getMonth() - 6);
    return {
      start_date: sixMonthsAgo.toISOString().split('T')[0],
      end_date: now.toISOString().split('T')[0]
    };
  });
  const [selectedFrequency, setSelectedFrequency] = useState<string>('monthly');
  const [showFilters, setShowFilters] = useState(false);

  // Get date range presets
  const dateRangePresets = useDateRangePresets();

  // Use internal hook if external snapshots not provided
  const {
    timeline: internalTimeline,
    loading: internalLoading,
    error: internalError,
    metadata,
    refetch
  } = useUniverseTimeline(
    universe_id,
    externalSnapshots ? undefined : {
      date_range: selectedDateRange,
      frequency: selectedFrequency as any,
      show_empty_periods: false,
      include_turnover_analysis: true
    }
  );

  // Use external data if provided, otherwise use internal hook data
  const snapshots = externalSnapshots || internalTimeline;
  const loading = externalLoading || internalLoading;
  const error = externalError || internalError;

  // Define table columns
  const columns: TimelineColumn[] = useMemo(() => {
    const baseColumns: TimelineColumn[] = [
      {
        key: 'snapshot_date',
        header: 'Date',
        sortable: true,
        width: '120px',
        formatter: (value: string) => formatDate(value)
      },
      {
        key: 'assets',
        header: 'Asset Count',
        sortable: true,
        width: '100px',
        formatter: (assets: any[]) => assets?.length || 0
      }
    ];

    if (showTurnoverColumn) {
      baseColumns.push({
        key: 'turnover_rate',
        header: 'Turnover',
        sortable: true,
        width: '100px',
        formatter: (value: number | null) => 
          value !== null ? `${(value * 100).toFixed(1)}%` : 'N/A'
      });
    }

    baseColumns.push(
      {
        key: 'assets_added',
        header: 'Added',
        sortable: false,
        width: '80px',
        formatter: (value: string[] | null) => 
          value ? value.length.toString() : '0'
      },
      {
        key: 'assets_removed',
        header: 'Removed',
        sortable: false,
        width: '80px',
        formatter: (value: string[] | null) => 
          value ? value.length.toString() : '0'
      }
    );

    if (showActionsColumn) {
      baseColumns.push({
        key: 'actions',
        header: 'Actions',
        sortable: false,
        width: '100px',
        formatter: (_, snapshot) => (
          <div className="flex items-center space-x-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSnapshotSelect?.(snapshot);
              }}
              className="text-blue-600 hover:text-blue-800 p-1 rounded"
              title="View Snapshot Details"
            >
              <EyeIcon className="w-4 h-4" />
            </button>
            {onAssetCompositionView && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAssetCompositionView(snapshot);
                }}
                className="text-green-600 hover:text-green-800 p-1 rounded"
                title="View Asset Composition"
              >
                <BuildingIcon className="w-4 h-4" />
              </button>
            )}
          </div>
        )
      });
    }

    return baseColumns;
  }, [showTurnoverColumn, showActionsColumn, onSnapshotSelect, onAssetCompositionView]);

  // Sorting logic
  const sortedSnapshots = useMemo(() => {
    if (!snapshots || snapshots.length === 0) return [];

    const sorted = [...snapshots].sort((a, b) => {
      let aValue: any = a[sortColumn];
      let bValue: any = b[sortColumn];

      // Handle special cases
      if (sortColumn === 'assets') {
        aValue = a.assets?.length || 0;
        bValue = b.assets?.length || 0;
      } else if (sortColumn === 'turnover_rate') {
        aValue = a.turnover_rate || 0;
        bValue = b.turnover_rate || 0;
      } else if (sortColumn === 'snapshot_date') {
        aValue = new Date(a.snapshot_date).getTime();
        bValue = new Date(b.snapshot_date).getTime();
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [snapshots, sortColumn, sortDirection]);

  // Date formatting utility
  const formatDate = useCallback((dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }, []);

  // Handle column sorting
  const handleSort = useCallback((column: keyof UniverseSnapshot) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  }, [sortColumn]);

  // Handle date range change
  const handleDateRangeChange = useCallback((range: DateRange) => {
    setSelectedDateRange(range);
    onDateRangeChange?.(range);
  }, [onDateRangeChange]);

  // Handle frequency change
  const handleFrequencyChange = useCallback((frequency: string) => {
    setSelectedFrequency(frequency);
    onFrequencyChange?.(frequency);
  }, [onFrequencyChange]);

  // Get turnover trend indicator
  const getTurnoverTrend = useCallback((turnoverRate: number | null) => {
    if (turnoverRate === null || turnoverRate === undefined) return null;
    
    // Assuming >5% is high, <1% is low
    if (turnoverRate > 0.05) {
      return (
        <div title="High Turnover">
          <TrendingUpIcon className="w-4 h-4 text-red-500" />
        </div>
      );
    } else if (turnoverRate < 0.01) {
      return (
        <div title="Low Turnover">
          <TrendingDownIcon className="w-4 h-4 text-green-500" />
        </div>
      );
    } else {
      return (
        <div title="Moderate Turnover">
          <MinusIcon className="w-4 h-4 text-yellow-500" />
        </div>
      );
    }
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading timeline...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Timeline Error</h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{error}</p>
            </div>
            <div className="mt-4">
              <button
                onClick={() => refetch?.()}
                className="bg-red-100 px-3 py-2 text-sm leading-4 font-medium rounded-md text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="text-center py-12">
        <CalendarIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No Timeline Data</h3>
        <p className="mt-1 text-sm text-gray-500">
          No historical snapshots found for the selected date range.
        </p>
        <div className="mt-6">
          <button
            onClick={() => setShowFilters(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <FilterIcon className="w-4 h-4 mr-2" />
            Adjust Filters
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg">
      {/* Header with filters */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Universe Timeline</h3>
            {metadata && (
              <p className="mt-1 text-sm text-gray-500">
                {metadata.total_snapshots} snapshots from {formatDate(metadata.period_start)} to {formatDate(metadata.period_end)}
                {metadata.avg_turnover_rate && (
                  <span className="ml-2">
                    • Avg Turnover: {(metadata.avg_turnover_rate * 100).toFixed(1)}%
                  </span>
                )}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <FilterIcon className="w-4 h-4 mr-1" />
              Filters
            </button>
            <button
              onClick={() => refetch?.()}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <RefreshCwIcon className="w-4 h-4 mr-1" />
              Refresh
            </button>
          </div>
        </div>

        {/* Collapsible filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Date range presets */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Date Range
                </label>
                <select
                  value=""
                  onChange={(e) => {
                    if (e.target.value) {
                      handleDateRangeChange(dateRangePresets[e.target.value]);
                    }
                  }}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="">Select preset...</option>
                  <option value="last30Days">Last 30 Days</option>
                  <option value="last3Months">Last 3 Months</option>
                  <option value="last6Months">Last 6 Months</option>
                  <option value="lastYear">Last Year</option>
                  <option value="last2Years">Last 2 Years</option>
                  <option value="ytd">Year to Date</option>
                </select>
              </div>

              {/* Frequency selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Frequency
                </label>
                <select
                  value={selectedFrequency}
                  onChange={(e) => handleFrequencyChange(e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                </select>
              </div>

              {/* Export option */}
              <div className="flex items-end">
                <button
                  onClick={() => {
                    // TODO: Implement CSV export
                    console.log('Export timeline to CSV');
                  }}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <DownloadIcon className="w-4 h-4 mr-1" />
                  Export CSV
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Timeline table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                    column.sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                  }`}
                  style={{ width: column.width }}
                  onClick={() => column.sortable && handleSort(column.key as keyof UniverseSnapshot)}
                >
                  <div className="flex items-center space-x-1">
                    <span>{column.header}</span>
                    {column.sortable && sortColumn === column.key && (
                      sortDirection === 'asc' 
                        ? <ChevronUpIcon className="w-4 h-4" />
                        : <ChevronDownIcon className="w-4 h-4" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedSnapshots.map((snapshot) => (
              <tr
                key={snapshot.id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => onSnapshotSelect?.(snapshot)}
              >
                {columns.map((column) => (
                  <td
                    key={`${snapshot.id}-${column.key}`}
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                  >
                    <div className="flex items-center space-x-2">
                      {column.formatter ? 
                        column.formatter((snapshot as any)[column.key], snapshot) : 
                        (snapshot as any)[column.key]
                      }
                      {column.key === 'turnover_rate' && getTurnoverTrend(snapshot.turnover_rate ?? null)}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary footer */}
      {metadata && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              Showing {sortedSnapshots.length} of {metadata.total_snapshots} snapshots
            </span>
            {metadata.timeline_statistics && (
              <div className="flex items-center space-x-4">
                <span>
                  Assets: {metadata.timeline_statistics.min_asset_count}-{metadata.timeline_statistics.max_asset_count} 
                  (avg: {metadata.timeline_statistics.avg_asset_count})
                </span>
                {metadata.timeline_statistics.most_stable_assets.length > 0 && (
                  <span>
                    Most stable: {metadata.timeline_statistics.most_stable_assets.slice(0, 3).join(', ')}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default UniverseTimeline;