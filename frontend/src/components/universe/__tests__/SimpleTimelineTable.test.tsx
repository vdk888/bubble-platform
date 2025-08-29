import React from 'react';
import { render, screen } from '@testing-library/react';
import SimpleTimelineTable from '../SimpleTimelineTable';
import { UniverseSnapshot } from '../../../types/temporal';

// Mock data for testing
const mockSnapshots: UniverseSnapshot[] = [
  {
    id: '1',
    universe_id: 'universe-1',
    snapshot_date: '2025-01-01',
    assets: [
      { symbol: 'AAPL', name: 'Apple Inc.' },
      { symbol: 'GOOGL', name: 'Alphabet Inc.' },
      { symbol: 'META', name: 'Meta Platforms Inc.' }
    ],
    created_at: '2025-01-01T00:00:00Z'
  },
  {
    id: '2',
    universe_id: 'universe-1',
    snapshot_date: '2025-01-02',
    assets: [
      { symbol: 'MSFT', name: 'Microsoft Corporation' },
      { symbol: 'AMZN', name: 'Amazon.com Inc.' },
      { symbol: 'NFLX', name: 'Netflix Inc.' }
    ],
    created_at: '2025-01-02T00:00:00Z'
  },
  {
    id: '3',
    universe_id: 'universe-1',
    snapshot_date: '2025-01-03',
    assets: [
      { symbol: 'TSLA', name: 'Tesla Inc.' },
      { symbol: 'NVDA', name: 'NVIDIA Corporation' },
      { symbol: 'JPM', name: 'JPMorgan Chase & Co.' }
    ],
    created_at: '2025-01-03T00:00:00Z'
  }
];

describe('SimpleTimelineTable', () => {
  test('renders simple timeline table with asset symbols', () => {
    render(
      <SimpleTimelineTable
        snapshots={mockSnapshots}
        maxDatesToShow={5}
      />
    );

    // Check that the component renders
    expect(screen.getByText('Portfolio Timeline')).toBeInTheDocument();

    // Check that date headers are displayed
    expect(screen.getByText('01/01/2025')).toBeInTheDocument();
    expect(screen.getByText('01/02/2025')).toBeInTheDocument();
    expect(screen.getByText('01/03/2025')).toBeInTheDocument();

    // Check that asset counts are shown in headers
    expect(screen.getAllByText('3 assets')).toHaveLength(3); // One for each date column

    // Check that asset symbols are displayed in cells
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('GOOGL')).toBeInTheDocument();
    expect(screen.getByText('META')).toBeInTheDocument();
    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.getByText('AMZN')).toBeInTheDocument();
    expect(screen.getByText('NFLX')).toBeInTheDocument();
    expect(screen.getByText('TSLA')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('JPM')).toBeInTheDocument();
  });

  test('handles empty snapshots gracefully', () => {
    render(
      <SimpleTimelineTable
        snapshots={[]}
        maxDatesToShow={5}
      />
    );

    expect(screen.getByText('No Timeline Data')).toBeInTheDocument();
    expect(screen.getByText('No snapshots available to display in timeline format.')).toBeInTheDocument();
  });

  test('respects maxDatesToShow limit', () => {
    const manySnapshots = Array.from({ length: 10 }, (_, i) => ({
      ...mockSnapshots[0],
      id: `snapshot-${i}`,
      snapshot_date: `2025-01-${String(i + 1).padStart(2, '0')}`,
    }));

    render(
      <SimpleTimelineTable
        snapshots={manySnapshots}
        maxDatesToShow={3}
      />
    );

    // Should only show 3 snapshots
    expect(screen.getByText('Timeline showing 3 snapshots')).toBeInTheDocument();
  });

  test('displays timeline period correctly', () => {
    render(
      <SimpleTimelineTable
        snapshots={mockSnapshots}
        maxDatesToShow={5}
      />
    );

    expect(screen.getByText(/Period: 01\/01\/2025 to 01\/03\/2025/)).toBeInTheDocument();
  });

  test('formats asset symbols with correct styling', () => {
    render(
      <SimpleTimelineTable
        snapshots={mockSnapshots}
        maxDatesToShow={5}
      />
    );

    // Asset symbols should have specific CSS classes
    const aaplElement = screen.getByText('AAPL');
    expect(aaplElement).toHaveClass('font-mono', 'font-medium', 'text-gray-900');
  });
});