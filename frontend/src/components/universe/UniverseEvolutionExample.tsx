import React, { useState } from 'react';
import UniverseEvolution from './UniverseEvolution';
import { DateRange } from '../../types/temporal';

/**
 * Example component showing how to use the UniverseEvolution component
 * with proper props interface and view mode management
 */
const UniverseEvolutionExample: React.FC = () => {
  const [viewMode, setViewMode] = useState<'asset_count' | 'turnover' | 'composition'>('asset_count');
  const [dateRange] = useState<DateRange>({
    start_date: '2023-01-01',
    end_date: '2024-12-31'
  });

  const handleViewModeChange = (mode: string) => {
    setViewMode(mode as 'asset_count' | 'turnover' | 'composition');
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-50 p-4 rounded-lg">
        <h2 className="text-lg font-semibold mb-4">UniverseEvolution Component Usage</h2>
        <p className="text-gray-600 mb-4">
          This example demonstrates the professional chart-based temporal universe analysis component
          with institutional-grade visualization features.
        </p>
        
        <div className="bg-white p-4 rounded border">
          <h3 className="font-medium mb-2">Current Configuration:</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li><strong>Universe ID:</strong> universe-123</li>
            <li><strong>View Mode:</strong> {viewMode}</li>
            <li><strong>Date Range:</strong> {dateRange.start_date} to {dateRange.end_date}</li>
            <li><strong>Height:</strong> 500px</li>
          </ul>
        </div>
      </div>

      <UniverseEvolution
        universeId="universe-123"
        viewMode={viewMode}
        onViewModeChange={handleViewModeChange}
        dateRange={dateRange}
        height={500}
        className="shadow-lg"
      />

      <div className="bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold text-blue-800 mb-2">Key Features Demonstrated:</h3>
        <ul className="text-blue-700 space-y-1 text-sm">
          <li>• Professional fintech color palette</li>
          <li>• Interactive zoom and pan controls</li>
          <li>• PNG export functionality</li>
          <li>• Multiple view modes (Asset Count, Turnover, Composition)</li>
          <li>• Real-time turnover analysis</li>
          <li>• Institutional-grade loading and error states</li>
          <li>• Responsive design with hover tooltips</li>
          <li>• Integration with existing temporal universe hooks</li>
        </ul>
      </div>

      <div className="bg-amber-50 p-4 rounded-lg">
        <h3 className="font-semibold text-amber-800 mb-2">Props Interface:</h3>
        <pre className="text-sm text-amber-700 bg-amber-100 p-3 rounded overflow-x-auto">
{`interface UniverseEvolutionProps {
  universeId: string;                          // Required: Universe ID
  dateRange?: DateRange;                       // Optional: Date range filter
  viewMode: 'asset_count' | 'turnover' | 'composition';  // Required: Chart view mode
  onViewModeChange: (mode: string) => void;   // Required: View mode change handler
  height?: number;                            // Optional: Chart height (default: 400)
  snapshots?: UniverseSnapshot[];             // Optional: External data
  loading?: boolean;                          // Optional: External loading state
  error?: string | null;                      // Optional: External error state
  className?: string;                         // Optional: Additional CSS classes
}`}
        </pre>
      </div>
    </div>
  );
};

export default UniverseEvolutionExample;