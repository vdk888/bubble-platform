import React, { useMemo } from 'react';
import { UniverseSnapshot } from '../../types/temporal';
import { CalendarIcon, BuildingIcon, TrendingUpIcon, AlertCircleIcon } from 'lucide-react';

interface HorizontalTimelineTableProps {
  snapshots: UniverseSnapshot[];
  onDateClick?: (date: string, snapshot: UniverseSnapshot) => void;
  onAssetClick?: (asset: string, dates: string[]) => void;
  maxDatesToShow?: number;
  className?: string;
}

interface TimelineTableData {
  dates: string[];
  assets: string[];
  assetByDate: Map<string, Set<string>>; // date -> Set of assets
  dateSnapshots: Map<string, UniverseSnapshot>; // date -> snapshot
}

const HorizontalTimelineTable: React.FC<HorizontalTimelineTableProps> = ({
  snapshots,
  onDateClick,
  onAssetClick,
  maxDatesToShow = 10,
  className = ''
}) => {
  // Process snapshots into table format
  const tableData: TimelineTableData = useMemo(() => {
    if (!snapshots || snapshots.length === 0) {
      return {
        dates: [],
        assets: [],
        assetByDate: new Map(),
        dateSnapshots: new Map()
      };
    }

    // Sort snapshots by date (most recent first for display)
    const sortedSnapshots = [...snapshots]
      .sort((a, b) => new Date(b.snapshot_date).getTime() - new Date(a.snapshot_date).getTime())
      .slice(0, maxDatesToShow);

    const dates = sortedSnapshots.map(s => s.snapshot_date);
    const dateSnapshots = new Map(sortedSnapshots.map(s => [s.snapshot_date, s]));
    
    // Build asset presence map
    const assetByDate = new Map<string, Set<string>>();
    const allAssets = new Set<string>();
    
    sortedSnapshots.forEach(snapshot => {
      const assetsInSnapshot = new Set(snapshot.assets.map(asset => asset.symbol));
      assetByDate.set(snapshot.snapshot_date, assetsInSnapshot);
      assetsInSnapshot.forEach(asset => allAssets.add(asset));
    });

    // Sort assets alphabetically for consistent display
    const assets = Array.from(allAssets).sort();

    return {
      dates,
      assets,
      assetByDate,
      dateSnapshots
    };
  }, [snapshots, maxDatesToShow]);

  // Format date for display
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'numeric',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Handle asset click to show which dates it appeared
  const handleAssetClick = (asset: string) => {
    const datesWithAsset = tableData.dates.filter(date => 
      tableData.assetByDate.get(date)?.has(asset)
    );
    onAssetClick?.(asset, datesWithAsset);
  };

  // Get asset status for a specific date
  const getAssetStatus = (asset: string, date: string, prevDate?: string) => {
    const hasAsset = tableData.assetByDate.get(date)?.has(asset) || false;
    const hadAsset = prevDate ? tableData.assetByDate.get(prevDate)?.has(asset) || false : false;
    
    if (!hasAsset) return null;
    
    if (prevDate && !hadAsset) {
      // Asset was added
      return 'added';
    } else if (prevDate && hadAsset) {
      // Asset was maintained
      return 'maintained';
    }
    return 'present';
  };

  if (tableData.dates.length === 0) {
    return (
      <div className={`bg-white border border-gray-200 rounded-lg p-6 ${className}`}>
        <div className="text-center">
          <CalendarIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Timeline Data</h3>
          <p className="text-gray-500">No snapshots available to display in timeline format.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CalendarIcon className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-medium text-gray-900">Portfolio Timeline</h3>
          </div>
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <span className="flex items-center space-x-1">
              <BuildingIcon className="w-4 h-4" />
              <span>{tableData.assets.length} assets</span>
            </span>
            <span className="flex items-center space-x-1">
              <TrendingUpIcon className="w-4 h-4" />
              <span>{tableData.dates.length} snapshots</span>
            </span>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 bg-blue-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 text-xs">
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-gray-600">Asset Present</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-gray-600">Recently Added</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-gray-300 rounded-full"></div>
              <span className="text-gray-600">Not Present</span>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Click column headers to view snapshot details • Click asset symbols to see timeline
          </div>
        </div>
      </div>

      {/* Timeline Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="bg-gray-100">
            <tr>
              {/* Asset column header */}
              <th className="sticky left-0 z-10 px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-100 border-r border-gray-200">
                Assets
              </th>
              
              {/* Date column headers */}
              {tableData.dates.map((date) => (
                <th
                  key={date}
                  className="px-4 py-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-200 transition-colors min-w-[120px]"
                  onClick={() => {
                    const snapshot = tableData.dateSnapshots.get(date);
                    if (snapshot) onDateClick?.(date, snapshot);
                  }}
                  title={`Click to view snapshot details for ${formatDate(date)}`}
                >
                  <div className="space-y-1">
                    <div>{formatDate(date)}</div>
                    <div className="text-xs text-gray-400 font-normal">
                      {tableData.assetByDate.get(date)?.size || 0} assets
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {tableData.assets.map((asset, assetIndex) => (
              <tr key={asset} className="hover:bg-gray-50">
                {/* Asset name column */}
                <td className="sticky left-0 z-10 px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900 bg-white border-r border-gray-200">
                  <button
                    onClick={() => handleAssetClick(asset)}
                    className="text-blue-600 hover:text-blue-800 hover:underline"
                    title={`View ${asset} timeline`}
                  >
                    {asset}
                  </button>
                </td>
                
                {/* Asset presence cells */}
                {tableData.dates.map((date, dateIndex) => {
                  const prevDate = dateIndex > 0 ? tableData.dates[dateIndex - 1] : undefined;
                  const status = getAssetStatus(asset, date, prevDate);
                  const hasAsset = tableData.assetByDate.get(date)?.has(asset) || false;
                  
                  return (
                    <td
                      key={`${asset}-${date}`}
                      className="px-4 py-3 text-center"
                    >
                      <div className="flex items-center justify-center">
                        {hasAsset ? (
                          <div
                            className={`w-4 h-4 rounded-full ${
                              status === 'added' 
                                ? 'bg-blue-500 animate-pulse' 
                                : 'bg-green-500'
                            }`}
                            title={
                              status === 'added' 
                                ? `${asset} was added on ${formatDate(date)}` 
                                : `${asset} present on ${formatDate(date)}`
                            }
                          />
                        ) : (
                          <div 
                            className="w-4 h-4 rounded-full bg-gray-300" 
                            title={`${asset} not present on ${formatDate(date)}`}
                          />
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer Summary */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Showing {Math.min(tableData.dates.length, maxDatesToShow)} most recent snapshots
          </span>
          <div className="flex items-center space-x-4">
            <span>
              Portfolio Range: {tableData.assets.length} total assets
            </span>
            <span>
              Period: {formatDate(tableData.dates[tableData.dates.length - 1])} to {formatDate(tableData.dates[0])}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HorizontalTimelineTable;