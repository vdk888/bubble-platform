import React, { useState, useRef } from 'react';
import { XIcon, UploadIcon, DownloadIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import { Universe, BulkValidationResult } from '../../types';
import { universeAPI, assetAPI } from '../../services/api';

interface BulkOperationsProps {
  universes: Universe[];
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

interface ImportResult {
  success: boolean;
  universe_name: string;
  added_count: number;
  failed_symbols: string[];
  message?: string;
}

const BulkOperations: React.FC<BulkOperationsProps> = ({
  universes,
  isOpen,
  onClose,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<'import' | 'export'>('import');
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResults, setImportResults] = useState<ImportResult[]>([]);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setError('Please select a CSV file');
      return;
    }

    setImporting(true);
    setError(null);
    setImportResults([]);
    setProgress({ current: 0, total: 0 });

    try {
      const text = await file.text();
      const rows = text.split('\n').filter(row => row.trim());
      
      if (rows.length === 0) {
        setError('CSV file is empty');
        return;
      }

      // Parse CSV - supporting both formats:
      // Static: universe_name, symbol1, symbol2, ...
      // Temporal: universe_name, snapshot_date, symbol1, symbol2, ..., change_reason
      const importData: Record<string, { symbols: string[], snapshots?: any[] }> = {};
      const headers = rows[0].split(',').map(h => h.trim());
      
      // Detect if this is temporal format (has "Snapshot Date" column)
      const isTemporalFormat = headers.some(h => h.toLowerCase().includes('snapshot') || h.toLowerCase().includes('date'));
      
      // Skip header row if it looks like headers
      const startRow = headers[0].toLowerCase().includes('universe') ? 1 : 0;
      
      for (let i = startRow; i < rows.length; i++) {
        const columns = rows[i].split(',').map(c => c.trim());
        if (columns.length < 2) continue;
        
        const universeName = columns[0];
        
        if (isTemporalFormat && columns[1]) {
          // Temporal format: Universe Name, Snapshot Date, Symbols..., Change Reason
          const snapshotDate = columns[1];
          const changeReason = columns[columns.length - 1]; // Last column is reason
          const symbols = columns.slice(2, -1).filter(s => s.length > 0 && s !== changeReason);
          
          if (universeName && symbols.length > 0 && snapshotDate) {
            if (!importData[universeName]) {
              importData[universeName] = { symbols: [], snapshots: [] };
            }
            importData[universeName].snapshots!.push({
              date: snapshotDate,
              symbols,
              reason: changeReason
            });
          }
        } else {
          // Static format: Universe Name, Symbol1, Symbol2...
          const symbols = columns.slice(1).filter(s => s.length > 0);
          
          if (universeName && symbols.length > 0) {
            if (!importData[universeName]) {
              importData[universeName] = { symbols: [] };
            }
            // For static format, use the symbols directly
            importData[universeName].symbols = symbols;
          }
        }
      }

      const universeNames = Object.keys(importData);
      if (universeNames.length === 0) {
        setError('No valid data found in CSV file');
        return;
      }

      setProgress({ current: 0, total: universeNames.length });

      // Process each universe
      const results: ImportResult[] = [];
      
      for (let i = 0; i < universeNames.length; i++) {
        const universeName = universeNames[i];
        const universeData = importData[universeName];
        
        setProgress({ current: i + 1, total: universeNames.length });

        try {
          // Find or create universe
          let targetUniverse = universes.find(u => 
            u.name.toLowerCase() === universeName.toLowerCase()
          );

          if (!targetUniverse) {
            const createResult = await universeAPI.create(universeName, `Imported from CSV`);
            if (!createResult.success || !createResult.data) {
              results.push({
                success: false,
                universe_name: universeName,
                added_count: 0,
                failed_symbols: universeData.symbols,
                message: createResult.message || 'Failed to create universe'
              });
              continue;
            }
            targetUniverse = createResult.data;
          }

          if (universeData.snapshots && universeData.snapshots.length > 0) {
            // Process temporal universe with historical snapshots
            let totalAdded = 0;
            let allFailedSymbols: string[] = [];
            
            // Sort snapshots by date to process chronologically
            const sortedSnapshots = universeData.snapshots.sort((a, b) => 
              new Date(a.date).getTime() - new Date(b.date).getTime()
            );
            
            for (const snapshot of sortedSnapshots) {
              try {
                // Add current assets to universe (this will be the latest composition)
                const addResult = await universeAPI.addAssets(targetUniverse.id, snapshot.symbols);
                
                if (addResult.success && addResult.data) {
                  const bulkResult: BulkValidationResult = addResult.data;
                  totalAdded += bulkResult.success_count;
                  
                  // Collect failed symbols from actual backend structure
                  const failed = bulkResult.failed
                    ? bulkResult.failed.map(f => f.symbol)
                    : [];
                  allFailedSymbols.push(...failed);
                  
                  // TODO: Create historical snapshot via API
                  // This would require implementing a temporal snapshot creation endpoint
                  console.log(`Snapshot for ${snapshot.date}: ${snapshot.symbols.join(', ')} (${snapshot.reason})`);
                }
              } catch (snapshotError) {
                console.error(`Failed to process snapshot ${snapshot.date}:`, snapshotError);
                allFailedSymbols.push(...snapshot.symbols);
              }
            }
            
            results.push({
              success: totalAdded > 0,
              universe_name: universeName,
              added_count: totalAdded,
              failed_symbols: Array.from(new Set(allFailedSymbols)), // Remove duplicates
              message: `Processed ${sortedSnapshots.length} historical snapshots`
            });
            
          } else {
            // Process static universe (original logic)
            const addResult = await universeAPI.addAssets(targetUniverse.id, universeData.symbols);
            
            if (addResult.success && addResult.data) {
              const bulkResult: BulkValidationResult = addResult.data;
              results.push({
                success: true,
                universe_name: universeName,
                added_count: bulkResult.success_count,
                failed_symbols: bulkResult.failed
                  ? bulkResult.failed.map(f => f.symbol)
                  : []
              });
            } else {
              results.push({
                success: false,
                universe_name: universeName,
                added_count: 0,
                failed_symbols: universeData.symbols,
                message: addResult.message || 'Failed to add assets'
              });
            }
          }
        } catch (error) {
          console.error(`Failed to import ${universeName}:`, error);
          results.push({
            success: false,
            universe_name: universeName,
            added_count: 0,
            failed_symbols: universeData.symbols,
            message: 'Network error during import'
          });
        }
      }

      setImportResults(results);
      onRefresh(); // Refresh the universes list
      
    } catch (error) {
      console.error('Import failed:', error);
      setError('Failed to read CSV file');
    } finally {
      setImporting(false);
      setProgress({ current: 0, total: 0 });
      // Clear the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleExport = async () => {
    if (universes.length === 0) {
      setError('No universes to export');
      return;
    }

    setExporting(true);
    setError(null);

    try {
      // Create CSV content
      let csvContent = 'Universe Name,Symbols\n';
      
      for (const universe of universes) {
        if (universe.assets && universe.assets.length > 0) {
          const symbols = universe.assets.map(asset => asset.symbol).join(',');
          csvContent += `"${universe.name}","${symbols}"\n`;
        } else {
          csvContent += `"${universe.name}",""\n`;
        }
      }

      // Download CSV file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      
      link.setAttribute('href', url);
      link.setAttribute('download', `bubble_platform_universes_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (error) {
      console.error('Export failed:', error);
      setError('Failed to export universes');
    } finally {
      setExporting(false);
    }
  };

  const downloadTemplate = () => {
    // Historical universe template with temporal snapshots
    const templateContent = `Universe Name,Snapshot Date,Symbol 1,Symbol 2,Symbol 3,Symbol 4,Symbol 5,Change Reason
Tech Leaders Portfolio,2025-03-15,AAPL,MSFT,GOOGL,AMZN,TSLA,Initial composition
Tech Leaders Portfolio,2025-04-15,AAPL,MSFT,GOOGL,AMZN,TSLA,No changes - stable portfolio
Tech Leaders Portfolio,2025-05-15,AAPL,MSFT,GOOGL,META,NVDA,Added META and NVDA for AI exposure
Tech Leaders Portfolio,2025-06-15,AAPL,MSFT,GOOGL,META,NVDA,No changes - monitoring performance
Tech Leaders Portfolio,2025-07-15,AAPL,MSFT,GOOGL,META,NFLX,Replaced NVDA with NFLX for streaming
Dividend Aristocrats,2025-03-01,JNJ,PG,KO,MMM,CAT,Conservative dividend portfolio
Dividend Aristocrats,2025-04-01,JNJ,PG,KO,MMM,HD,Replaced CAT with HD - home improvement growth
Dividend Aristocrats,2025-05-01,JNJ,PG,KO,MMM,HD,No changes - dividend stability focus
Example Static Universe,,,AAPL,MSFT,GOOGL,,,Static universe without temporal data
`;
    
    const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'historical_universe_template.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" onClick={onClose}>
          <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Bulk Operations
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <XIcon className="w-6 h-6" />
              </button>
            </div>
            
            {/* Tab Navigation */}
            <div className="mt-4">
              <nav className="flex space-x-8" aria-label="Tabs">
                <button
                  onClick={() => setActiveTab('import')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'import'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <UploadIcon className="w-4 h-4 mr-2 inline" />
                  Import Universes
                </button>
                <button
                  onClick={() => setActiveTab('export')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'export'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <DownloadIcon className="w-4 h-4 mr-2 inline" />
                  Export Universes
                </button>
              </nav>
            </div>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-6 max-h-[60vh] overflow-y-auto">
            {/* Error Message */}
            {error && (
              <div className="mb-6 bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Import Tab */}
            {activeTab === 'import' && (
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Import from CSV</h4>
                  <p className="text-sm text-gray-600 mb-4">
                    Upload a CSV file to create universes. Supports both formats:<br/>
                    <strong>Static:</strong> Universe Name, Symbol1, Symbol2, Symbol3...<br/>
                    <strong>Temporal:</strong> Universe Name, Snapshot Date, Symbol1, Symbol2..., Change Reason
                  </p>
                  <div className="text-xs text-gray-500 mb-4 p-3 bg-blue-50 rounded-lg">
                    💡 <strong>Temporal Format:</strong> Create historical universe snapshots to track portfolio evolution over time. 
                    Each row represents the universe composition at a specific date, enabling temporal analysis and turnover tracking.
                  </div>
                  
                  <div className="flex space-x-3">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv"
                      onChange={handleImportFile}
                      disabled={importing}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                    />
                    <button
                      onClick={downloadTemplate}
                      className="btn-secondary whitespace-nowrap"
                    >
                      Download Template
                    </button>
                  </div>
                </div>

                {/* Progress */}
                {importing && (
                  <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600 mr-3"></div>
                      <div>
                        <div className="font-medium text-primary-900">
                          Importing universes...
                        </div>
                        <div className="text-sm text-primary-700">
                          Processing {progress.current} of {progress.total}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 bg-primary-200 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%`
                        }}
                      ></div>
                    </div>
                  </div>
                )}

                {/* Import Results */}
                {importResults.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Import Results</h4>
                    <div className="space-y-3">
                      {importResults.map((result, index) => (
                        <div
                          key={index}
                          className={`p-4 rounded-lg border ${
                            result.success
                              ? 'bg-success-50 border-success-200'
                              : 'bg-error-50 border-error-200'
                          }`}
                        >
                          <div className="flex items-start">
                            <div className="mr-3 mt-0.5">
                              {result.success ? (
                                <CheckCircleIcon className="w-4 h-4 text-success-500" />
                              ) : (
                                <XCircleIcon className="w-4 h-4 text-error-500" />
                              )}
                            </div>
                            <div className="flex-1">
                              <div className={`font-medium ${
                                result.success ? 'text-success-900' : 'text-error-900'
                              }`}>
                                {result.universe_name}
                              </div>
                              <div className={`text-sm mt-1 ${
                                result.success ? 'text-success-700' : 'text-error-700'
                              }`}>
                                {result.success ? (
                                  <>
                                    Successfully added {result.added_count} assets
                                    {result.failed_symbols.length > 0 && (
                                      <span>, {result.failed_symbols.length} failed: {result.failed_symbols.join(', ')}</span>
                                    )}
                                  </>
                                ) : (
                                  result.message || 'Import failed'
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Export Tab */}
            {activeTab === 'export' && (
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Export to CSV</h4>
                  <p className="text-sm text-gray-600 mb-4">
                    Export all your universes and their assets to a CSV file. This file can be used as a backup or imported later.
                  </p>
                  
                  <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <div className="text-sm text-gray-600">
                      <div>Total universes: <span className="font-medium">{universes.length}</span></div>
                      <div>Total assets: <span className="font-medium">
                        {universes.reduce((total, u) => total + (u.asset_count || 0), 0)}
                      </span></div>
                    </div>
                  </div>
                  
                  <button
                    onClick={handleExport}
                    disabled={exporting || universes.length === 0}
                    className="btn-primary"
                  >
                    {exporting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Exporting...
                      </>
                    ) : (
                      <>
                        <DownloadIcon className="w-4 h-4 mr-2" />
                        Export CSV
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BulkOperations;