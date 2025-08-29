import React, { useState, useMemo, useCallback } from 'react';
import {
  TrendingUpIcon,
  TrendingDownIcon,
  BuildingIcon,
  DollarSignIcon,
  CalendarIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  InfoIcon,
  ExternalLinkIcon,
  FilterIcon,
  DownloadIcon
} from 'lucide-react';
import { AssetComposition, UniverseSnapshot } from '../../types/temporal';
import { useCompositionAtDate } from '../../hooks/useTemporalUniverse';

interface AssetCompositionViewProps {
  universeId: string;
  snapshot?: UniverseSnapshot;
  selectedDate?: string;
  onAssetSelect?: (asset: AssetComposition) => void;
  onDateChange?: (date: string) => void;
  showMetadata?: boolean;
  showActions?: boolean;
  className?: string;
}

interface SortConfig {
  key: keyof AssetComposition;
  direction: 'asc' | 'desc';
}

const AssetCompositionView: React.FC<AssetCompositionViewProps> = ({
  universeId,
  snapshot,
  selectedDate,
  onAssetSelect,
  onDateChange,
  showMetadata = true,
  showActions = true,
  className = ''
}) => {
  // State management
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'symbol', direction: 'asc' });
  const [searchTerm, setSearchTerm] = useState('');
  const [sectorFilter, setSectorFilter] = useState<string>('all');
  const [showFilters, setShowFilters] = useState(false);

  // Hook for fetching composition at specific date
  const { getComposition, loading, error, lastResponse } = useCompositionAtDate(universeId);

  // Get assets from snapshot or use composition hook
  const assets: AssetComposition[] = useMemo(() => {
    if (snapshot?.assets) {
      return snapshot.assets;
    }
    return [];
  }, [snapshot]);

  // Get unique sectors for filtering
  const sectors = useMemo(() => {
    const uniqueSectors = new Set(
      assets.map(asset => asset.sector || 'Unknown').filter(Boolean)
    );
    return Array.from(uniqueSectors).sort();
  }, [assets]);

  // Filtered and sorted assets
  const filteredAssets = useMemo(() => {
    let filtered = assets;

    // Apply search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(asset =>
        asset.symbol.toLowerCase().includes(search) ||
        asset.name.toLowerCase().includes(search) ||
        (asset.sector?.toLowerCase().includes(search) || false)
      );
    }

    // Apply sector filter
    if (sectorFilter !== 'all') {
      filtered = filtered.filter(asset => asset.sector === sectorFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];

      // Handle different data types
      if (sortConfig.key === 'market_cap') {
        const aNum = (aValue as number) || 0;
        const bNum = (bValue as number) || 0;
        return sortConfig.direction === 'asc' ? aNum - bNum : bNum - aNum;
      }

      // String comparison for other fields
      const aStr = String(aValue || '').toLowerCase();
      const bStr = String(bValue || '').toLowerCase();

      if (aStr < bStr) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aStr > bStr) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [assets, searchTerm, sectorFilter, sortConfig]);

  // Handle column sorting
  const handleSort = useCallback((key: keyof AssetComposition) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  }, []);

  // Handle asset row click
  const handleAssetClick = useCallback((asset: AssetComposition) => {
    onAssetSelect?.(asset);
  }, [onAssetSelect]);

  // Format market cap for display
  const formatMarketCap = useCallback((marketCap?: number) => {
    if (!marketCap) return 'N/A';
    
    if (marketCap >= 1e12) return `$${(marketCap / 1e12).toFixed(1)}T`;
    if (marketCap >= 1e9) return `$${(marketCap / 1e9).toFixed(1)}B`;
    if (marketCap >= 1e6) return `$${(marketCap / 1e6).toFixed(1)}M`;
    return `$${marketCap.toLocaleString()}`;
  }, []);

  // Format date for display
  const formatDate = useCallback((dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }, []);

  // Get sector color for visual differentiation
  const getSectorColor = useCallback((sector?: string) => {
    if (!sector) return 'bg-gray-100 text-gray-700';
    
    const sectorColors: Record<string, string> = {
      'Technology': 'bg-blue-100 text-blue-800',
      'Healthcare': 'bg-green-100 text-green-800',
      'Financials': 'bg-yellow-100 text-yellow-800',
      'Consumer Discretionary': 'bg-purple-100 text-purple-800',
      'Consumer Staples': 'bg-pink-100 text-pink-800',
      'Energy': 'bg-red-100 text-red-800',
      'Industrials': 'bg-indigo-100 text-indigo-800',
      'Materials': 'bg-orange-100 text-orange-800',
      'Real Estate': 'bg-teal-100 text-teal-800',
      'Telecommunications': 'bg-cyan-100 text-cyan-800',
      'Utilities': 'bg-gray-100 text-gray-800'
    };
    
    return sectorColors[sector] || 'bg-gray-100 text-gray-700';
  }, []);

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (filteredAssets.length === 0) return null;

    const totalMarketCap = filteredAssets.reduce((sum, asset) => 
      sum + (asset.market_cap || 0), 0
    );
    
    const avgMarketCap = totalMarketCap / filteredAssets.length;
    const sectorCounts = filteredAssets.reduce((counts, asset) => {
      const sector = asset.sector || 'Unknown';
      counts[sector] = (counts[sector] || 0) + 1;
      return counts;
    }, {} as Record<string, number>);

    const topSector = Object.entries(sectorCounts)
      .sort(([, a], [, b]) => b - a)[0];

    return {
      totalAssets: filteredAssets.length,
      totalMarketCap,
      avgMarketCap,
      topSector: topSector ? { sector: topSector[0], count: topSector[1] } : null
    };
  }, [filteredAssets]);

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading asset composition...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center text-red-600">
          <InfoIcon className="w-5 h-5 mr-2" />
          <span>Error loading asset composition: {error}</span>
        </div>
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="text-center py-8">
          <BuildingIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Assets Found</h3>
          <p className="text-gray-500">
            {selectedDate ? `No assets were found for ${formatDate(selectedDate)}` : 'No assets in this universe snapshot'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <BuildingIcon className="w-5 h-5 mr-2 text-blue-600" />
              Asset Composition
            </h3>
            {snapshot && (
              <p className="text-sm text-gray-600 mt-1 flex items-center">
                <CalendarIcon className="w-4 h-4 mr-1" />
                {formatDate(snapshot.snapshot_date)}
                {snapshot.turnover_rate !== null && snapshot.turnover_rate !== undefined && (
                  <span className="ml-3 text-xs bg-gray-100 px-2 py-1 rounded-full">
                    Turnover: {((snapshot.turnover_rate || 0) * 100).toFixed(1)}%
                  </span>
                )}
              </p>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <FilterIcon className="w-4 h-4 mr-2" />
              Filters
            </button>
            {showActions && (
              <button
                onClick={() => {
                  // TODO: Implement CSV export
                  console.log('Export composition to CSV');
                }}
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                <DownloadIcon className="w-4 h-4 mr-2" />
                Export
              </button>
            )}
          </div>
        </div>

        {/* Summary Statistics */}
        {showMetadata && summaryStats && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="flex items-center">
                <BuildingIcon className="w-5 h-5 text-blue-600 mr-2" />
                <div>
                  <p className="text-sm font-medium text-blue-900">Total Assets</p>
                  <p className="text-lg font-bold text-blue-600">{summaryStats.totalAssets}</p>
                </div>
              </div>
            </div>
            <div className="bg-green-50 rounded-lg p-3">
              <div className="flex items-center">
                <DollarSignIcon className="w-5 h-5 text-green-600 mr-2" />
                <div>
                  <p className="text-sm font-medium text-green-900">Total Market Cap</p>
                  <p className="text-lg font-bold text-green-600">{formatMarketCap(summaryStats.totalMarketCap)}</p>
                </div>
              </div>
            </div>
            <div className="bg-purple-50 rounded-lg p-3">
              <div className="flex items-center">
                <TrendingUpIcon className="w-5 h-5 text-purple-600 mr-2" />
                <div>
                  <p className="text-sm font-medium text-purple-900">Avg Market Cap</p>
                  <p className="text-lg font-bold text-purple-600">{formatMarketCap(summaryStats.avgMarketCap)}</p>
                </div>
              </div>
            </div>
            {summaryStats.topSector && (
              <div className="bg-orange-50 rounded-lg p-3">
                <div className="flex items-center">
                  <BuildingIcon className="w-5 h-5 text-orange-600 mr-2" />
                  <div>
                    <p className="text-sm font-medium text-orange-900">Top Sector</p>
                    <p className="text-sm font-bold text-orange-600">
                      {summaryStats.topSector.sector} ({summaryStats.topSector.count})
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Search Assets
                </label>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search by symbol, name, or sector..."
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Filter by Sector
                </label>
                <select
                  value={sectorFilter}
                  onChange={(e) => setSectorFilter(e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="all">All Sectors</option>
                  {sectors.map(sector => (
                    <option key={sector} value={sector}>
                      {sector}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="flex items-end">
                <button
                  onClick={() => {
                    setSearchTerm('');
                    setSectorFilter('all');
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Clear Filters
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Asset Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {[
                { key: 'symbol' as keyof AssetComposition, label: 'Symbol', width: '100px' },
                { key: 'name' as keyof AssetComposition, label: 'Name', width: '200px' },
                { key: 'sector' as keyof AssetComposition, label: 'Sector', width: '150px' },
                { key: 'market_cap' as keyof AssetComposition, label: 'Market Cap', width: '120px' },
                { key: 'weight' as keyof AssetComposition, label: 'Weight', width: '100px' }
              ].map(column => (
                <th
                  key={column.key}
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  style={{ width: column.width }}
                  onClick={() => handleSort(column.key)}
                >
                  <div className="flex items-center space-x-1">
                    <span>{column.label}</span>
                    {sortConfig.key === column.key && (
                      sortConfig.direction === 'asc' 
                        ? <ArrowUpIcon className="w-4 h-4" />
                        : <ArrowDownIcon className="w-4 h-4" />
                    )}
                  </div>
                </th>
              ))}
              {showActions && (
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredAssets.map((asset, index) => (
              <tr
                key={`${asset.symbol}-${index}`}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => handleAssetClick(asset)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm font-medium text-gray-900">
                      {asset.symbol}
                    </div>
                  </div>
                </td>
                
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900">{asset.name}</div>
                  {asset.reason_added && (
                    <div className="text-xs text-gray-500 mt-1">{asset.reason_added}</div>
                  )}
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  {asset.sector ? (
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSectorColor(asset.sector)}`}>
                      {asset.sector}
                    </span>
                  ) : (
                    <span className="text-sm text-gray-400">Unknown</span>
                  )}
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatMarketCap(asset.market_cap)}
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {asset.weight ? `${(asset.weight * 100).toFixed(2)}%` : 'N/A'}
                </td>
                
                {showActions && (
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // TODO: Implement view asset details
                        console.log('View asset details:', asset.symbol);
                      }}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ExternalLinkIcon className="w-4 h-4" />
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Showing {filteredAssets.length} of {assets.length} assets
            {searchTerm || sectorFilter !== 'all' ? ' (filtered)' : ''}
          </span>
          {lastResponse && (
            <div className="flex items-center space-x-4">
              {lastResponse.data.context?.is_exact_match ? (
                <span className="text-green-600 font-medium">Exact snapshot match</span>
              ) : (
                <span className="text-yellow-600">
                  Nearest snapshot: {formatDate(lastResponse.data.snapshot_date)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AssetCompositionView;