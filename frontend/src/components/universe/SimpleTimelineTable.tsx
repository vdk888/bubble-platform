import React, { useMemo } from 'react';
import { UniverseSnapshot } from '../../types/temporal';
import { CalendarIcon } from 'lucide-react';

interface SimpleTimelineTableProps {
  snapshots: UniverseSnapshot[];
  onDateClick?: (date: string, snapshot: UniverseSnapshot) => void;
  maxDatesToShow?: number;
  className?: string;
}

interface SimpleTableData {
  dates: string[];
  dateSnapshots: Map<string, UniverseSnapshot>;
  assetsByDate: Map<string, string[]>; // date -> array of asset symbols
  maxAssetsPerDate: number;
}

const SimpleTimelineTable: React.FC<SimpleTimelineTableProps> = ({
  snapshots,
  onDateClick,
  maxDatesToShow = 10,
  className = ''
}) => {
  // Process snapshots into simple table format
  const tableData: SimpleTableData = useMemo(() => {
    if (!snapshots || snapshots.length === 0) {
      return {
        dates: [],
        dateSnapshots: new Map(),
        assetsByDate: new Map(),
        maxAssetsPerDate: 0
      };
    }

    // Sort snapshots by date (most recent first for display)
    const sortedSnapshots = [...snapshots]
      .sort((a, b) => new Date(a.snapshot_date).getTime() - new Date(b.snapshot_date).getTime())
      .slice(0, maxDatesToShow);

    const dates = sortedSnapshots.map(s => s.snapshot_date);
    const dateSnapshots = new Map(sortedSnapshots.map(s => [s.snapshot_date, s]));
    
    // Build assets by date map
    const assetsByDate = new Map<string, string[]>();
    let maxAssetsPerDate = 0;
    
    sortedSnapshots.forEach(snapshot => {
      const assetsInSnapshot = snapshot.assets
        .map(asset => asset.symbol)
        .sort(); // Sort alphabetically
      assetsByDate.set(snapshot.snapshot_date, assetsInSnapshot);
      maxAssetsPerDate = Math.max(maxAssetsPerDate, assetsInSnapshot.length);
    });

    return {
      dates,
      dateSnapshots,
      assetsByDate,
      maxAssetsPerDate
    };
  }, [snapshots, maxDatesToShow]);

  // Format date for display
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
    });
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
          <div className="text-sm text-gray-600">
            {tableData.dates.length} snapshots • Up to {tableData.maxAssetsPerDate} assets per period
          </div>
        </div>
      </div>

      {/* Simple Timeline Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full">
          {/* Column Headers - Dates */}
          <thead className="bg-gray-50">
            <tr>
              {tableData.dates.map((date) => (
                <th
                  key={date}
                  className="px-4 py-3 text-center text-sm font-medium text-gray-900 border-r border-gray-200 last:border-r-0 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    const snapshot = tableData.dateSnapshots.get(date);
                    if (snapshot) onDateClick?.(date, snapshot);
                  }}
                  title={`View snapshot details for ${formatDate(date)}`}
                >
                  <div className="space-y-1">
                    <div className="font-semibold">{formatDate(date)}</div>
                    <div className="text-xs text-gray-500 font-normal">
                      {tableData.assetsByDate.get(date)?.length || 0} assets
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Asset Rows */}
          <tbody className="bg-white">
            {/* Create rows for maximum assets to ensure proper alignment */}
            {Array.from({ length: tableData.maxAssetsPerDate }, (_, rowIndex) => (
              <tr key={rowIndex} className="border-t border-gray-200">
                {tableData.dates.map((date) => {
                  const assetsForDate = tableData.assetsByDate.get(date) || [];
                  const asset = assetsForDate[rowIndex]; // Get asset at this row index

                  return (
                    <td
                      key={`${date}-${rowIndex}`}
                      className="px-4 py-3 text-center text-sm border-r border-gray-200 last:border-r-0"
                    >
                      {asset ? (
                        <span className="inline-block font-mono font-medium text-gray-900 bg-gray-50 px-2 py-1 rounded">
                          {asset}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
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
            Timeline showing {tableData.dates.length} snapshots
          </span>
          <div className="flex items-center space-x-4">
            <span>
              Period: {formatDate(tableData.dates[0])} to {formatDate(tableData.dates[tableData.dates.length - 1])}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleTimelineTable;