import React, { useState } from 'react';
import { PlusIcon, TrashIcon, CheckIcon, XIcon } from 'lucide-react';
import { Asset, Universe } from '../../types';
import { universeAPI, assetAPI } from '../../services/api';

interface UniverseAssetTableProps {
  universe: Universe;
  onUniverseUpdate: () => void;
}

const UniverseAssetTable: React.FC<UniverseAssetTableProps> = ({
  universe,
  onUniverseUpdate,
}) => {
  // State for inline asset addition
  const [newAssetSymbol, setNewAssetSymbol] = useState('');
  const [addingAsset, setAddingAsset] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [removingAssetId, setRemovingAssetId] = useState<string | null>(null);

  // Handle adding a new asset inline (Sprint 2 Step 2)
  const handleAddAsset = async () => {
    if (!newAssetSymbol.trim()) {
      setError('Please enter a valid asset symbol');
      return;
    }

    setAddingAsset(true);
    setError(null);

    try {
      // First validate the symbol
      const validationResult = await assetAPI.validate([newAssetSymbol.trim().toUpperCase()]);
      
      if (!validationResult.success) {
        setError('Failed to validate asset symbol');
        return;
      }

      // Add the asset to the universe
      const result = await universeAPI.addAssets(universe.id, [newAssetSymbol.trim().toUpperCase()]);
      
      if (result.success) {
        setNewAssetSymbol('');
        onUniverseUpdate(); // Refresh the universe data
      } else {
        setError(result.message || 'Failed to add asset to universe');
      }
    } catch (error) {
      console.error('Failed to add asset:', error);
      setError('Network error while adding asset');
    } finally {
      setAddingAsset(false);
    }
  };

  // Handle removing an asset inline (Sprint 2 Step 2)
  const handleRemoveAsset = async (assetSymbol: string, assetId: string) => {
    if (!window.confirm(`Remove ${assetSymbol} from this universe?`)) {
      return;
    }

    setRemovingAssetId(assetId);
    setError(null);

    try {
      const result = await universeAPI.removeAssets(universe.id, [assetSymbol]);
      
      if (result.success) {
        onUniverseUpdate(); // Refresh the universe data
      } else {
        setError(result.message || 'Failed to remove asset from universe');
      }
    } catch (error) {
      console.error('Failed to remove asset:', error);
      setError('Network error while removing asset');
    } finally {
      setRemovingAssetId(null);
    }
  };

  const assets = universe.assets || [];

  return (
    <div className="mt-6">
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-lg font-medium text-gray-900">
          Assets ({assets.length})
        </h4>
        
        {/* Inline Add Asset Form (Sprint 2 Step 2: "Editable list") */}
        <div className="flex space-x-2">
          <input
            type="text"
            placeholder="Enter symbol (e.g., AAPL)"
            value={newAssetSymbol}
            onChange={(e) => setNewAssetSymbol(e.target.value.toUpperCase())}
            className="input-field text-sm w-40"
            disabled={addingAsset}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleAddAsset();
              }
            }}
          />
          <button
            onClick={handleAddAsset}
            disabled={addingAsset || !newAssetSymbol.trim()}
            className="btn-primary text-sm px-3 py-1 flex items-center"
          >
            {addingAsset ? (
              <>
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1"></div>
                Adding...
              </>
            ) : (
              <>
                <PlusIcon className="h-3 w-3 mr-1" />
                Add Asset
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 bg-error-50 border border-error-200 text-error-700 px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}

      {/* Assets Table with Inline Editing (Sprint 2 Step 2) */}
      {assets.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No assets in this universe yet.</p>
          <p className="text-sm text-gray-400 mt-1">Use the form above to add your first asset.</p>
        </div>
      ) : (
        <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
          <table className="min-w-full divide-y divide-gray-300">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Symbol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sector
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Market Cap
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  P/E Ratio
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {assets.map((asset) => (
                <tr key={asset.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {asset.symbol}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 max-w-xs truncate">
                      {asset.name || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">
                      {asset.sector || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {asset.market_cap
                        ? `$${(asset.market_cap / 1e9).toFixed(1)}B`
                        : 'N/A'
                      }
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {asset.pe_ratio ? asset.pe_ratio.toFixed(1) : 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      asset.is_validated
                        ? 'bg-success-100 text-success-800'
                        : 'bg-warning-100 text-warning-800'
                    }`}>
                      {asset.is_validated ? (
                        <>
                          <CheckIcon className="w-3 h-3 mr-1" />
                          Validated
                        </>
                      ) : (
                        <>
                          <XIcon className="w-3 h-3 mr-1" />
                          Pending
                        </>
                      )}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    {/* Inline Remove Button (Sprint 2 Step 2: "add/remove from universe") */}
                    <button
                      onClick={() => handleRemoveAsset(asset.symbol, asset.id)}
                      disabled={removingAssetId === asset.id}
                      className="text-error-600 hover:text-error-900 disabled:opacity-50"
                      title="Remove from universe"
                    >
                      {removingAssetId === asset.id ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-error-600"></div>
                      ) : (
                        <TrashIcon className="h-4 w-4" />
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default UniverseAssetTable;