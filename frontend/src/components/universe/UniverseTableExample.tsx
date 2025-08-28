import React, { useState } from 'react';
import UniverseTable from './UniverseTable';
import { Universe } from '../../types';

/**
 * Example usage of the enhanced UniverseTable component
 * Demonstrates both standard and temporal mode usage patterns
 */

const sampleUniverses: Universe[] = [
  {
    id: '1',
    name: 'Tech Leaders',
    description: 'Top technology companies with strong fundamentals',
    owner_id: 'user-1',
    asset_count: 15,
    turnover_rate: 0.12,
    is_active: true,
    created_at: '2024-01-15T00:00:00Z',
    updated_at: '2025-01-28T10:30:00Z'
  },
  {
    id: '2', 
    name: 'Healthcare Innovation',
    description: 'Pharmaceutical and biotech companies',
    owner_id: 'user-1',
    asset_count: 8,
    turnover_rate: 0.08,
    is_active: true,
    created_at: '2024-06-20T00:00:00Z',
    updated_at: '2025-01-27T15:45:00Z'
  },
  {
    id: '3',
    name: 'Energy Transition',
    description: 'Clean energy and traditional energy companies',
    owner_id: 'user-1',
    asset_count: 22,
    turnover_rate: 0.28,
    is_active: true,
    created_at: '2024-03-10T00:00:00Z',
    updated_at: '2025-01-26T09:15:00Z'
  }
];

const UniverseTableExample: React.FC = () => {
  const [temporalModeEnabled, setTemporalModeEnabled] = useState(false);
  const [loading, setLoading] = useState(false);

  // Standard handlers
  const handleUniverseSelect = (universe: Universe) => {
    console.log('Viewing universe:', universe.name);
  };

  const handleUniverseEdit = (universe: Universe) => {
    console.log('Editing universe:', universe.name);
  };

  const handleUniverseDelete = (universe: Universe) => {
    console.log('Deleting universe:', universe.name);
  };

  // Temporal handlers
  const handleTemporalModeToggle = (enabled: boolean) => {
    setTemporalModeEnabled(enabled);
    console.log('Temporal mode:', enabled ? 'enabled' : 'disabled');
  };

  const handleTimelineView = (universe: Universe) => {
    console.log('Opening timeline for universe:', universe.name);
    // Navigate to timeline view or open modal
  };

  const handleTemporalAnalysis = (universe: Universe) => {
    console.log('Opening temporal analysis for universe:', universe.name);
    // Navigate to analysis view or open modal
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Universe Management Dashboard
        </h1>
        <p className="text-gray-600">
          Example implementation of the enhanced UniverseTable component with temporal features.
        </p>
      </div>

      {/* Example 1: Basic Usage (No Temporal Features) */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          1. Basic Universe Table (Standard Mode)
        </h2>
        <div className="bg-white rounded-lg shadow border">
          <UniverseTable
            universes={sampleUniverses}
            loading={loading}
            onUniverseSelect={handleUniverseSelect}
            onUniverseEdit={handleUniverseEdit}
            onUniverseDelete={handleUniverseDelete}
          />
        </div>
      </div>

      {/* Example 2: With Temporal Features */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          2. Enhanced Table with Temporal Features
        </h2>
        <div className="bg-white rounded-lg shadow border">
          <UniverseTable
            universes={sampleUniverses}
            loading={loading}
            onUniverseSelect={handleUniverseSelect}
            onUniverseEdit={handleUniverseEdit}
            onUniverseDelete={handleUniverseDelete}
            // Temporal feature configuration
            showTemporalMode={true}
            temporalModeEnabled={temporalModeEnabled}
            onTemporalModeToggle={handleTemporalModeToggle}
            onTimelineView={handleTimelineView}
            onTemporalAnalysis={handleTemporalAnalysis}
          />
        </div>
      </div>

      {/* Example 3: Loading State */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          3. Loading State Example
        </h2>
        <div className="bg-white rounded-lg shadow border">
          <div className="mb-4 p-4 border-b">
            <button
              onClick={() => setLoading(!loading)}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              {loading ? 'Stop Loading' : 'Simulate Loading'}
            </button>
          </div>
          <UniverseTable
            universes={loading ? [] : sampleUniverses}
            loading={loading}
            onUniverseSelect={handleUniverseSelect}
            onUniverseEdit={handleUniverseEdit}
            onUniverseDelete={handleUniverseDelete}
            showTemporalMode={true}
            temporalModeEnabled={temporalModeEnabled}
            onTemporalModeToggle={handleTemporalModeToggle}
            onTimelineView={handleTimelineView}
            onTemporalAnalysis={handleTemporalAnalysis}
          />
        </div>
      </div>

      {/* Usage Code Examples */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Code Examples
        </h2>
        <div className="space-y-4">
          <div className="bg-gray-100 p-4 rounded-lg">
            <h3 className="font-medium mb-2">Basic Usage:</h3>
            <pre className="text-sm text-gray-800 overflow-x-auto">
{`<UniverseTable
  universes={universes}
  loading={loading}
  onUniverseSelect={handleSelect}
  onUniverseEdit={handleEdit}
  onUniverseDelete={handleDelete}
/>`}
            </pre>
          </div>

          <div className="bg-gray-100 p-4 rounded-lg">
            <h3 className="font-medium mb-2">With Temporal Features:</h3>
            <pre className="text-sm text-gray-800 overflow-x-auto">
{`<UniverseTable
  universes={universes}
  loading={loading}
  onUniverseSelect={handleSelect}
  onUniverseEdit={handleEdit}
  onUniverseDelete={handleDelete}
  // Temporal features
  showTemporalMode={true}
  temporalModeEnabled={temporalEnabled}
  onTemporalModeToggle={setTemporalEnabled}
  onTimelineView={handleTimelineView}
  onTemporalAnalysis={handleAnalysis}
/>`}
            </pre>
          </div>
        </div>
      </div>

      {/* Feature Summary */}
      <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
        <h2 className="text-lg font-semibold text-blue-900 mb-4">
          Enhanced Features Summary
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h3 className="font-medium text-blue-800 mb-2">Standard Features:</h3>
            <ul className="space-y-1 text-blue-700">
              <li>• Universe listing with asset counts</li>
              <li>• Turnover rate display</li>
              <li>• Status indicators</li>
              <li>• Edit/delete/view actions</li>
              <li>• Loading and empty states</li>
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-blue-800 mb-2">Temporal Features:</h3>
            <ul className="space-y-1 text-blue-700">
              <li>• Temporal mode toggle</li>
              <li>• Historical snapshot counts</li>
              <li>• Enhanced turnover badges</li>
              <li>• Timeline view buttons</li>
              <li>• Temporal analysis actions</li>
              <li>• Relative time display</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UniverseTableExample;