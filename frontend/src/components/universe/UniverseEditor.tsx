import React, { useState, useEffect } from 'react';
import { XIcon, PlusIcon, MinusIcon, SaveIcon, CheckCircleIcon, XCircleIcon } from 'lucide-react';
import { Universe, Asset, ValidationResult } from '../../types';
import { universeAPI, assetAPI } from '../../services/api';

interface UniverseEditorProps {
  universe?: Universe | null;
  isOpen: boolean;
  onClose: (shouldRefresh?: boolean) => void;
}

const UniverseEditor: React.FC<UniverseEditorProps> = ({
  universe,
  isOpen,
  onClose,
}) => {
  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [newSymbols, setNewSymbols] = useState('');
  
  // UI state
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResults, setValidationResults] = useState<Record<string, ValidationResult>>({});
  const [error, setError] = useState<string | null>(null);
  
  const isEditing = !!universe;

  // Initialize form data
  useEffect(() => {
    if (isOpen) {
      if (universe) {
        setName(universe.name);
        setDescription(universe.description || '');
        setAssets(universe.assets || []);
      } else {
        // Reset for new universe
        setName('');
        setDescription('');
        setAssets([]);
      }
      setNewSymbols('');
      setError(null);
      setValidationResults({});
    }
  }, [universe, isOpen]);

  const handleAddSymbols = async () => {
    if (!newSymbols.trim()) return;

    const symbols = newSymbols
      .split(/[,\s\n]+/)
      .map(s => s.trim().toUpperCase())
      .filter(s => s.length > 0);

    if (symbols.length === 0) return;

    // Check for duplicates
    const existingSymbols = new Set(assets.map(a => a.symbol));
    const newUniqueSymbols = symbols.filter(s => !existingSymbols.has(s));

    if (newUniqueSymbols.length === 0) {
      setError('All symbols are already in this universe');
      return;
    }

    // Validate the new symbols
    setValidating(true);
    setError(null);

    try {
      const result = await assetAPI.validate(newUniqueSymbols);
      if (result.success && result.data) {
        const validationMap: Record<string, ValidationResult> = {};
        result.data.forEach(validation => {
          validationMap[validation.symbol] = validation;
        });
        setValidationResults(prev => ({ ...prev, ...validationMap }));

        // Create temporary Asset objects for valid symbols
        const newAssets: Asset[] = result.data
          .filter(v => v.is_valid)
          .map(validation => ({
            id: `temp_${validation.symbol}`, // Temporary ID
            symbol: validation.symbol,
            name: validation.asset_info?.name || validation.symbol,
            sector: validation.asset_info?.sector,
            industry: validation.asset_info?.industry,
            market_cap: validation.asset_info?.market_cap,
            pe_ratio: validation.asset_info?.pe_ratio,
            dividend_yield: validation.asset_info?.dividend_yield,
            is_validated: true,
            asset_metadata: validation.asset_info?.asset_metadata || {},
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }));

        setAssets(prev => [...prev, ...newAssets]);
        setNewSymbols('');

        // Show validation results for invalid symbols
        const invalidSymbols = result.data.filter(v => !v.is_valid);
        if (invalidSymbols.length > 0) {
          setError(`Invalid symbols: ${invalidSymbols.map(v => v.symbol).join(', ')}`);
        }
      } else {
        setError(result.message || 'Validation failed');
      }
    } catch (error) {
      console.error('Validation failed:', error);
      setError('Network error during validation');
    } finally {
      setValidating(false);
    }
  };

  const handleRemoveAsset = (assetToRemove: Asset) => {
    setAssets(prev => prev.filter(asset => asset.id !== assetToRemove.id));
    // Remove from validation results
    setValidationResults(prev => {
      const updated = { ...prev };
      delete updated[assetToRemove.symbol];
      return updated;
    });
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Universe name is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      let savedUniverse: Universe;

      if (isEditing && universe) {
        // Update existing universe
        const updateResult = await universeAPI.update(universe.id, {
          name: name.trim(),
          description: description.trim() || undefined,
        });

        if (!updateResult.success || !updateResult.data) {
          throw new Error(updateResult.message || 'Failed to update universe');
        }

        savedUniverse = updateResult.data;

        // Add new assets if any
        const newAssetSymbols = assets
          .filter(asset => asset.id.startsWith('temp_'))
          .map(asset => asset.symbol);

        if (newAssetSymbols.length > 0) {
          const addAssetsResult = await universeAPI.addAssets(universe.id, newAssetSymbols);
          if (!addAssetsResult.success) {
            console.warn('Some assets may not have been added:', addAssetsResult.message);
          }
        }
      } else {
        // Create new universe
        const createResult = await universeAPI.create(name.trim(), description.trim() || undefined);

        if (!createResult.success || !createResult.data) {
          throw new Error(createResult.message || 'Failed to create universe');
        }

        savedUniverse = createResult.data;

        // Add assets if any
        const assetSymbols = assets.map(asset => asset.symbol);
        if (assetSymbols.length > 0) {
          const addAssetsResult = await universeAPI.addAssets(savedUniverse.id, assetSymbols);
          if (!addAssetsResult.success) {
            console.warn('Some assets may not have been added:', addAssetsResult.message);
          }
        }
      }

      // Close and refresh
      onClose(true);
    } catch (error) {
      console.error('Save failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to save universe');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" onClick={() => onClose(false)}>
          <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                {isEditing ? `Edit ${universe?.name}` : 'Create Universe'}
              </h3>
              <button
                onClick={() => onClose(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XIcon className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-6 max-h-[70vh] overflow-y-auto">
            {/* Basic Info */}
            <div className="grid grid-cols-1 gap-4 mb-6">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Universe Name *
                </label>
                <input
                  type="text"
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-field"
                  placeholder="e.g., Tech Growth Stocks, Dividend Aristocrats"
                  required
                />
              </div>
              
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="input-field"
                  placeholder="Describe the investment theme or criteria for this universe"
                />
              </div>
            </div>

            {/* Add Assets */}
            <div className="mb-6">
              <label htmlFor="symbols" className="block text-sm font-medium text-gray-700 mb-1">
                Add Assets
              </label>
              <div className="flex space-x-2">
                <textarea
                  id="symbols"
                  value={newSymbols}
                  onChange={(e) => setNewSymbols(e.target.value)}
                  rows={2}
                  className="input-field flex-1"
                  placeholder="Enter symbols separated by commas or new lines (e.g., AAPL, MSFT, GOOGL)"
                />
                <button
                  onClick={handleAddSymbols}
                  disabled={validating || !newSymbols.trim()}
                  className="btn-primary h-fit flex-shrink-0"
                >
                  {validating ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  ) : (
                    <PlusIcon className="w-4 h-4 mr-2" />
                  )}
                  Add
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-6 bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Assets List */}
            <div className="mb-6">
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                Assets ({assets.length})
              </h4>
              
              {assets.length === 0 ? (
                <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
                  <p>No assets added yet</p>
                  <p className="text-sm mt-1">Add some symbols above to get started</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {assets.map((asset) => {
                    const validation = validationResults[asset.symbol];
                    return (
                      <div
                        key={asset.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center flex-1 min-w-0">
                          <div className="flex items-center mr-3">
                            {asset.is_validated ? (
                              <CheckCircleIcon className="w-4 h-4 text-success-500" />
                            ) : validation?.is_valid === false ? (
                              <XCircleIcon className="w-4 h-4 text-error-500" />
                            ) : (
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center">
                              <span className="font-medium text-gray-900 mr-2">
                                {asset.symbol}
                              </span>
                              {asset.sector && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-800">
                                  {asset.sector}
                                </span>
                              )}
                            </div>
                            <div className="text-sm text-gray-500 truncate">
                              {asset.name}
                            </div>
                          </div>
                          <div className="text-right">
                            {asset.market_cap && (
                              <div className="text-sm text-gray-600">
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
                        <button
                          onClick={() => handleRemoveAsset(asset)}
                          className="ml-3 text-error-600 hover:text-error-800"
                        >
                          <MinusIcon className="w-4 h-4" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => onClose(false)}
              className="btn-secondary"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !name.trim()}
              className="btn-primary"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                <>
                  <SaveIcon className="w-4 h-4 mr-2" />
                  {isEditing ? 'Update' : 'Create'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UniverseEditor;