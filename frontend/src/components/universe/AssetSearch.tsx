import React, { useState, useEffect, useRef } from 'react';
import { SearchIcon, XIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import { Asset, AssetSearchProps, ValidationResult } from '../../types';
import { assetAPI } from '../../services/api';

interface AssetSearchModalProps extends AssetSearchProps {
  onClose: () => void;
}

const AssetSearch: React.FC<AssetSearchModalProps> = ({
  onAssetSelect,
  selectedAssets = [],
  onClose,
  placeholder = "Search for assets (e.g., AAPL, Microsoft, Technology)",
  className = "",
}) => {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [validationResults, setValidationResults] = useState<Record<string, ValidationResult>>({});
  const [selectedSector, setSelectedSector] = useState<string>('');
  const [sectors, setSectors] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const searchTimeout = useRef<NodeJS.Timeout>();

  // Load sectors on component mount
  useEffect(() => {
    loadSectors();
  }, []);

  // Debounced search
  useEffect(() => {
    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }

    if (query.trim().length >= 2) {
      searchTimeout.current = setTimeout(() => {
        performSearch(query.trim());
      }, 300);
    } else {
      setSearchResults([]);
      setValidationResults({});
    }

    return () => {
      if (searchTimeout.current) {
        clearTimeout(searchTimeout.current);
      }
    };
  }, [query, selectedSector]);

  const loadSectors = async () => {
    try {
      const result = await assetAPI.getSectors();
      if (result.success && result.data) {
        setSectors(result.data);
      }
    } catch (error) {
      console.error('Failed to load sectors:', error);
    }
  };

  const performSearch = async (searchQuery: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await assetAPI.search(
        searchQuery, 
        selectedSector || undefined,
        20
      );

      if (result.success && result.data) {
        const assets = result.data.assets || [];
        setSearchResults(assets);

        // Validate the found assets
        if (assets.length > 0) {
          const symbols = assets.map(asset => asset.symbol);
          validateAssets(symbols);
        }
      } else {
        setError(result.message || 'Search failed');
        setSearchResults([]);
      }
    } catch (error) {
      console.error('Search failed:', error);
      setError('Network error during search');
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const validateAssets = async (symbols: string[]) => {
    try {
      const result = await assetAPI.validate(symbols);
      if (result.success && result.data) {
        const validationMap: Record<string, ValidationResult> = {};
        result.data.forEach(validation => {
          validationMap[validation.symbol] = validation;
        });
        setValidationResults(validationMap);
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleAssetSelect = (asset: Asset) => {
    onAssetSelect(asset);
    // Optional: close modal after selection
    // onClose();
  };

  const isAssetSelected = (asset: Asset) => {
    return selectedAssets.some(selected => selected.id === asset.id);
  };

  const getValidationIcon = (asset: Asset) => {
    const validation = validationResults[asset.symbol];
    
    if (!validation) {
      return <ClockIcon className="w-4 h-4 text-gray-400" />;
    }

    if (validation.is_valid) {
      return <CheckCircleIcon className="w-4 h-4 text-success-500" />;
    }

    return <XCircleIcon className="w-4 h-4 text-error-500" />;
  };

  const getValidationText = (asset: Asset) => {
    const validation = validationResults[asset.symbol];
    
    if (!validation) {
      return 'Validating...';
    }

    if (validation.is_valid) {
      return validation.cached ? 'Validated (cached)' : 'Validated';
    }

    return validation.message || 'Invalid symbol';
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" onClick={onClose}>
          <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Asset Search
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <XIcon className="w-6 h-6" />
              </button>
            </div>

            {/* Search Input */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <SearchIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="input-field pl-10"
                placeholder={placeholder}
                autoFocus
              />
              {loading && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                </div>
              )}
            </div>

            {/* Sector Filter */}
            <div className="mt-3">
              <select
                value={selectedSector}
                onChange={(e) => setSelectedSector(e.target.value)}
                className="input-field"
              >
                <option value="">All Sectors</option>
                {sectors.map((sector) => (
                  <option key={sector} value={sector}>
                    {sector}
                  </option>
                ))}
              </select>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mt-3 bg-error-50 border border-error-200 text-error-700 px-3 py-2 rounded text-sm">
                {error}
              </div>
            )}
          </div>

          {/* Results */}
          <div className="bg-gray-50 px-4 py-3 sm:px-6 max-h-96 overflow-y-auto">
            {searchResults.length === 0 && query.trim().length >= 2 && !loading && (
              <div className="text-center py-8 text-gray-500">
                <p>No assets found for "{query}"</p>
                <p className="text-sm mt-1">
                  Try searching by symbol (AAPL) or company name (Apple)
                </p>
              </div>
            )}

            {searchResults.length === 0 && query.trim().length < 2 && (
              <div className="text-center py-8 text-gray-500">
                <p>Start typing to search for assets...</p>
                <p className="text-sm mt-1">
                  Search by symbol, company name, or sector
                </p>
              </div>
            )}

            <div className="space-y-2">
              {searchResults.map((asset) => (
                <div
                  key={asset.id}
                  onClick={() => handleAssetSelect(asset)}
                  className={`cursor-pointer p-4 bg-white rounded-lg border transition-colors ${
                    isAssetSelected(asset)
                      ? 'border-primary-300 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center">
                        <div className="font-medium text-gray-900">
                          {asset.symbol}
                        </div>
                        <div className="ml-2 flex items-center">
                          {getValidationIcon(asset)}
                        </div>
                        {isAssetSelected(asset) && (
                          <div className="ml-2">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800">
                              Selected
                            </span>
                          </div>
                        )}
                      </div>
                      <div className="text-sm text-gray-500 truncate">
                        {asset.name}
                      </div>
                      <div className="flex items-center mt-1 space-x-4">
                        {asset.sector && (
                          <span className="text-xs text-gray-400">
                            {asset.sector}
                          </span>
                        )}
                        {asset.industry && (
                          <span className="text-xs text-gray-400">
                            {asset.industry}
                          </span>
                        )}
                        <span className="text-xs text-gray-400">
                          {getValidationText(asset)}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      {asset.market_cap && (
                        <div className="text-sm text-gray-900">
                          ${(asset.market_cap / 1e9).toFixed(1)}B
                        </div>
                      )}
                      {asset.pe_ratio && (
                        <div className="text-xs text-gray-500">
                          P/E: {asset.pe_ratio.toFixed(1)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary w-full sm:w-auto sm:ml-3"
            >
              Close
            </button>
            <div className="flex-1 text-sm text-gray-500 mt-3 sm:mt-0">
              {selectedAssets.length > 0 && (
                <span>{selectedAssets.length} asset(s) selected</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssetSearch;