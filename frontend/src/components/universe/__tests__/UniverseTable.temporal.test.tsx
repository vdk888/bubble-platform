import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import UniverseTable from '../UniverseTable';
import { Universe } from '../../../types';

// Mock the temporal API
jest.mock('../../../services/api', () => ({
  temporalUniverseAPI: {
    getTimeline: jest.fn()
  }
}));

const mockUniverses: Universe[] = [
  {
    id: '2976275e-3fd0-4751-b33d-12c8e8999661',
    name: 'Tech Leaders Portfolio',
    description: 'Technology sector leaders',
    asset_count: 50,
    turnover_rate: 0.15,
    is_active: true,
    created_at: '2025-06-01T00:00:00Z',
    updated_at: '2025-08-28T00:00:00Z',
    last_screening_date: '2025-08-28T00:00:00Z',
    assets: []
  }
];

describe('UniverseTable Temporal Mode', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should display correct snapshot count when temporal mode is enabled', async () => {
    // Mock the temporal API to return 4 snapshots
    const mockTemporalAPI = require('../../../services/api').temporalUniverseAPI;
    mockTemporalAPI.getTimeline.mockResolvedValue({
      success: true,
      data: [
        { id: '1', snapshot_date: '2025-06-01T00:00:00Z', assets: [], turnover_rate: 0.1 },
        { id: '2', snapshot_date: '2025-07-01T00:00:00Z', assets: [], turnover_rate: 0.15 },
        { id: '3', snapshot_date: '2025-08-01T00:00:00Z', assets: [], turnover_rate: 0.2 },
        { id: '4', snapshot_date: '2025-08-28T00:00:00Z', assets: [], turnover_rate: 0.12 }
      ],
      metadata: {
        total_snapshots: 4,
        date_range: {
          earliest_snapshot: '2025-06-01T00:00:00Z',
          latest_snapshot: '2025-08-28T00:00:00Z'
        }
      }
    });

    const mockProps = {
      universes: mockUniverses,
      loading: false,
      onUniverseSelect: jest.fn(),
      onUniverseEdit: jest.fn(),
      onUniverseDelete: jest.fn(),
      showTemporalMode: true,
      temporalModeEnabled: true,
      onTemporalModeToggle: jest.fn(),
      onTimelineView: jest.fn(),
      onTemporalAnalysis: jest.fn()
    };

    render(<UniverseTable {...mockProps} />);

    // Wait for the temporal data to be fetched
    await waitFor(() => {
      expect(mockTemporalAPI.getTimeline).toHaveBeenCalledWith(
        '2976275e-3fd0-4751-b33d-12c8e8999661',
        expect.objectContaining({
          frequency: 'monthly',
          show_empty_periods: false,
          include_turnover_analysis: true
        })
      );
    });

    // Wait for the snapshot count to be displayed
    await waitFor(() => {
      const snapshotCount = screen.getByText('4');
      expect(snapshotCount).toBeInTheDocument();
    });

    // Verify the temporal mode header is visible
    expect(screen.getByText('Snapshots')).toBeInTheDocument();
  });

  it('should show loading state while fetching temporal data', async () => {
    // Mock a delayed API response
    const mockTemporalAPI = require('../../../services/api').temporalUniverseAPI;
    mockTemporalAPI.getTimeline.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        success: true,
        data: [],
        metadata: { total_snapshots: 0 }
      }), 100))
    );

    const mockProps = {
      universes: mockUniverses,
      loading: false,
      onUniverseSelect: jest.fn(),
      onUniverseEdit: jest.fn(),
      onUniverseDelete: jest.fn(),
      showTemporalMode: true,
      temporalModeEnabled: true,
      onTemporalModeToggle: jest.fn(),
      onTimelineView: jest.fn(),
      onTemporalAnalysis: jest.fn()
    };

    render(<UniverseTable {...mockProps} />);

    // Should show loading spinners while fetching temporal data
    await waitFor(() => {
      const spinners = document.querySelectorAll('.animate-spin');
      expect(spinners.length).toBeGreaterThan(0);
    }, { timeout: 50 }); // Short timeout since the loading state is brief
  });

  it('should handle API errors gracefully', async () => {
    // Mock API error
    const mockTemporalAPI = require('../../../services/api').temporalUniverseAPI;
    mockTemporalAPI.getTimeline.mockRejectedValue(new Error('API Error'));

    const mockProps = {
      universes: mockUniverses,
      loading: false,
      onUniverseSelect: jest.fn(),
      onUniverseEdit: jest.fn(),
      onUniverseDelete: jest.fn(),
      showTemporalMode: true,
      temporalModeEnabled: true,
      onTemporalModeToggle: jest.fn(),
      onTimelineView: jest.fn(),
      onTemporalAnalysis: jest.fn()
    };

    render(<UniverseTable {...mockProps} />);

    // Wait for error handling
    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument();
    });
  });

  it('should not fetch temporal data when temporal mode is disabled', () => {
    const mockTemporalAPI = require('../../../services/api').temporalUniverseAPI;

    const mockProps = {
      universes: mockUniverses,
      loading: false,
      onUniverseSelect: jest.fn(),
      onUniverseEdit: jest.fn(),
      onUniverseDelete: jest.fn(),
      showTemporalMode: true,
      temporalModeEnabled: false, // Disabled
      onTemporalModeToggle: jest.fn(),
      onTimelineView: jest.fn(),
      onTemporalAnalysis: jest.fn()
    };

    render(<UniverseTable {...mockProps} />);

    // Should not call the temporal API
    expect(mockTemporalAPI.getTimeline).not.toHaveBeenCalled();
    
    // Should not show the Snapshots column
    expect(screen.queryByText('Snapshots')).not.toBeInTheDocument();
  });

  it('should clear temporal data when temporal mode is toggled off', async () => {
    const mockTemporalAPI = require('../../../services/api').temporalUniverseAPI;
    mockTemporalAPI.getTimeline.mockResolvedValue({
      success: true,
      data: [{ id: '1', snapshot_date: '2025-08-01T00:00:00Z', assets: [] }],
      metadata: { total_snapshots: 1 }
    });

    const mockProps = {
      universes: mockUniverses,
      loading: false,
      onUniverseSelect: jest.fn(),
      onUniverseEdit: jest.fn(),
      onUniverseDelete: jest.fn(),
      showTemporalMode: true,
      temporalModeEnabled: true,
      onTemporalModeToggle: jest.fn(),
      onTimelineView: jest.fn(),
      onTemporalAnalysis: jest.fn()
    };

    const { rerender } = render(<UniverseTable {...mockProps} />);

    // Wait for temporal data to load
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    // Toggle temporal mode off
    rerender(<UniverseTable {...mockProps} temporalModeEnabled={false} />);

    // Snapshots column should disappear
    expect(screen.queryByText('Snapshots')).not.toBeInTheDocument();
  });
});