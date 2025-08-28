import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import UniverseTimeline from '../UniverseTimeline';
import { UniverseSnapshot } from '../../../types/temporal';

// Mock data - define before mocks
const mockSnapshots: UniverseSnapshot[] = [
  {
    id: '1',
    universe_id: 'universe-1',
    snapshot_date: '2024-08-01',
    assets: [
      { symbol: 'AAPL', name: 'Apple Inc.' },
      { symbol: 'GOOGL', name: 'Alphabet Inc.' },
      { symbol: 'MSFT', name: 'Microsoft Corp.' }
    ],
    turnover_rate: 0.15,
    assets_added: ['MSFT'],
    assets_removed: ['TSLA'],
    created_at: '2024-08-01T10:00:00Z'
  },
  {
    id: '2',
    universe_id: 'universe-1',
    snapshot_date: '2024-07-01',
    assets: [
      { symbol: 'AAPL', name: 'Apple Inc.' },
      { symbol: 'GOOGL', name: 'Alphabet Inc.' },
      { symbol: 'TSLA', name: 'Tesla Inc.' }
    ],
    turnover_rate: 0.05,
    assets_added: ['GOOGL'],
    assets_removed: [],
    created_at: '2024-07-01T10:00:00Z'
  }
];

const mockMetadata = {
  universe_id: 'universe-1',
  period_start: '2024-07-01',
  period_end: '2024-08-01',
  frequency: 'monthly',
  total_snapshots: 2,
  avg_turnover_rate: 0.10
};

// Mock the temporal universe hooks
jest.mock('../../../hooks/useTemporalUniverse', () => ({
  useUniverseTimeline: jest.fn(),
  useDateRangePresets: jest.fn(() => ({
    last30Days: { start_date: '2024-07-28', end_date: '2024-08-28' },
    last3Months: { start_date: '2024-05-28', end_date: '2024-08-28' },
    last6Months: { start_date: '2024-02-28', end_date: '2024-08-28' }
  }))
}));

// Get the mocked hook
const mockUseUniverseTimeline = require('../../../hooks/useTemporalUniverse').useUniverseTimeline;

describe('UniverseTimeline Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Setup default mock return value
    mockUseUniverseTimeline.mockReturnValue({
      timeline: [],
      loading: false,
      error: null,
      metadata: null,
      refetch: jest.fn()
    });
  });

  it('renders timeline table with snapshots', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        snapshots={mockSnapshots}
      />
    );

    // Check if the table headers are present
    expect(screen.getByText('Date')).toBeInTheDocument();
    expect(screen.getByText('Asset Count')).toBeInTheDocument();
    expect(screen.getByText('Turnover')).toBeInTheDocument();
    expect(screen.getByText('Added')).toBeInTheDocument();
    expect(screen.getByText('Removed')).toBeInTheDocument();

    // Check if snapshot data is displayed
    expect(screen.getByText('Aug 1, 2024')).toBeInTheDocument();
    expect(screen.getByText('Jul 1, 2024')).toBeInTheDocument();
    expect(screen.getByText('15.0%')).toBeInTheDocument(); // turnover rate
    expect(screen.getByText('5.0%')).toBeInTheDocument(); // turnover rate
  });

  it('displays loading state correctly', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        loading={true}
      />
    );

    expect(screen.getByText('Loading timeline...')).toBeInTheDocument();
  });

  it('displays error state correctly', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        error="Failed to load timeline"
      />
    );

    expect(screen.getByText('Timeline Error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load timeline')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('displays empty state when no snapshots', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        snapshots={[]}
      />
    );

    expect(screen.getByText('No Timeline Data')).toBeInTheDocument();
    expect(screen.getByText('No historical snapshots found for the selected date range.')).toBeInTheDocument();
  });

  it('handles snapshot selection', () => {
    const mockOnSnapshotSelect = jest.fn();
    
    render(
      <UniverseTimeline
        universe_id="universe-1"
        snapshots={mockSnapshots}
        onSnapshotSelect={mockOnSnapshotSelect}
      />
    );

    // Click on the first row
    const firstRow = screen.getByText('Aug 1, 2024').closest('tr');
    fireEvent.click(firstRow!);

    expect(mockOnSnapshotSelect).toHaveBeenCalledWith(mockSnapshots[0]);
  });

  it('displays correct asset counts', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        snapshots={mockSnapshots}
      />
    );

    // Both snapshots have 3 assets each
    const assetCounts = screen.getAllByText('3');
    expect(assetCounts).toHaveLength(2);
  });

  it('can hide turnover column', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        snapshots={mockSnapshots}
        showTurnoverColumn={false}
      />
    );

    expect(screen.queryByText('Turnover')).not.toBeInTheDocument();
    expect(screen.queryByText('15.0%')).not.toBeInTheDocument();
  });

  it('shows filters when filter button is clicked', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        snapshots={mockSnapshots}
      />
    );

    const filtersButton = screen.getByText('Filters');
    fireEvent.click(filtersButton);

    expect(screen.getByText('Date Range')).toBeInTheDocument();
    expect(screen.getByText('Frequency')).toBeInTheDocument();
  });

  it('formats turnover rates correctly', () => {
    render(
      <UniverseTimeline
        universe_id="universe-1"
        snapshots={mockSnapshots}
      />
    );

    // Check if turnover rates are formatted as percentages
    expect(screen.getByText('15.0%')).toBeInTheDocument();
    expect(screen.getByText('5.0%')).toBeInTheDocument();
  });
});