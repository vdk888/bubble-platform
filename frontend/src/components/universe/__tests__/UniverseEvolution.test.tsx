import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import UniverseEvolution from '../UniverseEvolution';
import { UniverseSnapshot } from '../../../types/temporal';

// Mock Chart.js
jest.mock('chart.js', () => ({
  Chart: {
    register: jest.fn(),
  },
  CategoryScale: jest.fn(),
  LinearScale: jest.fn(),
  PointElement: jest.fn(),
  LineElement: jest.fn(),
  AreaElement: jest.fn(),
  Title: jest.fn(),
  Tooltip: jest.fn(),
  Legend: jest.fn(),
  Filler: jest.fn(),
}));

jest.mock('react-chartjs-2', () => ({
  Line: ({ data, options }: any) => (
    <div data-testid="line-chart">
      <div data-testid="chart-data">{JSON.stringify(data)}</div>
      <div data-testid="chart-options">{JSON.stringify(options)}</div>
    </div>
  ),
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  format: (date: Date, formatStr: string) => date.toISOString().split('T')[0],
  parseISO: (dateStr: string) => new Date(dateStr),
}));

// Mock hooks
jest.mock('../../../hooks/useTemporalUniverse', () => ({
  useUniverseTimeline: jest.fn(() => ({
    timeline: [],
    loading: false,
    error: null,
    metadata: null,
    refetch: jest.fn(),
  })),
  useTurnoverAnalysis: jest.fn(() => ({
    analysis: null,
    loading: false,
    error: null,
    calculateAnalysis: jest.fn(),
  })),
}));

const mockSnapshots: UniverseSnapshot[] = [
  {
    id: '1',
    universe_id: 'universe-1',
    snapshot_date: '2024-01-01',
    assets: [
      { symbol: 'AAPL', name: 'Apple Inc.' },
      { symbol: 'GOOGL', name: 'Alphabet Inc.' },
    ],
    turnover_rate: 0.15,
    assets_added: ['AAPL'],
    assets_removed: [],
    created_at: '2024-01-01T10:00:00Z',
  },
  {
    id: '2',
    universe_id: 'universe-1',
    snapshot_date: '2024-02-01',
    assets: [
      { symbol: 'AAPL', name: 'Apple Inc.' },
      { symbol: 'GOOGL', name: 'Alphabet Inc.' },
      { symbol: 'MSFT', name: 'Microsoft Corporation' },
    ],
    turnover_rate: 0.25,
    assets_added: ['MSFT'],
    assets_removed: [],
    created_at: '2024-02-01T10:00:00Z',
  },
];

describe('UniverseEvolution', () => {
  const defaultProps = {
    universeId: 'universe-1',
    viewMode: 'asset_count' as const,
    onViewModeChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders with loading state', () => {
    const { useUniverseTimeline } = require('../../../hooks/useTemporalUniverse');
    useUniverseTimeline.mockReturnValue({
      timeline: [],
      loading: true,
      error: null,
      metadata: null,
      refetch: jest.fn(),
    });

    render(<UniverseEvolution {...defaultProps} />);

    expect(screen.getByText('Loading evolution chart...')).toBeInTheDocument();
  });

  test('renders with error state', () => {
    const { useUniverseTimeline } = require('../../../hooks/useTemporalUniverse');
    useUniverseTimeline.mockReturnValue({
      timeline: [],
      loading: false,
      error: 'Failed to load data',
      metadata: null,
      refetch: jest.fn(),
    });

    render(<UniverseEvolution {...defaultProps} />);

    expect(screen.getByText('Chart Error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load data')).toBeInTheDocument();
  });

  test('renders chart with external snapshots', () => {
    render(<UniverseEvolution {...defaultProps} snapshots={mockSnapshots} />);

    expect(screen.getByText('Universe Evolution')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  test('handles view mode changes', async () => {
    const onViewModeChange = jest.fn();
    render(<UniverseEvolution {...defaultProps} snapshots={mockSnapshots} onViewModeChange={onViewModeChange} />);

    const viewSelector = screen.getByRole('combobox');
    fireEvent.change(viewSelector, { target: { value: 'turnover' } });

    expect(onViewModeChange).toHaveBeenCalledWith('turnover');
  });

  test('displays metadata information', () => {
    const { useUniverseTimeline } = require('../../../hooks/useTemporalUniverse');
    useUniverseTimeline.mockReturnValue({
      timeline: mockSnapshots,
      loading: false,
      error: null,
      metadata: {
        total_snapshots: 2,
        period_start: '2024-01-01',
        period_end: '2024-02-01',
      },
      refetch: jest.fn(),
    });

    render(<UniverseEvolution {...defaultProps} />);

    expect(screen.getByText(/2 snapshots/)).toBeInTheDocument();
  });

  test('toggles data points visibility', async () => {
    render(<UniverseEvolution {...defaultProps} snapshots={mockSnapshots} />);

    const toggleButton = screen.getByTitle('Toggle data points');
    fireEvent.click(toggleButton);

    await waitFor(() => {
      const chartData = screen.getByTestId('chart-data');
      const dataObj = JSON.parse(chartData.textContent || '{}');
      expect(dataObj.datasets[0].pointRadius).toBe(0);
    });
  });

  test('renders turnover analysis summary', () => {
    const { useTurnoverAnalysis } = require('../../../hooks/useTemporalUniverse');
    useTurnoverAnalysis.mockReturnValue({
      analysis: {
        period_start: '2024-01-01',
        period_end: '2024-02-01',
        average_turnover_rate: 0.20,
        turnover_trend: 'increasing',
        asset_stability: {
          core_holdings: ['AAPL', 'GOOGL'],
        },
      },
      loading: false,
      error: null,
    });

    render(<UniverseEvolution {...defaultProps} snapshots={mockSnapshots} />);

    expect(screen.getByText('Avg Turnover:')).toBeInTheDocument();
    expect(screen.getByText('20.0%')).toBeInTheDocument();
    expect(screen.getByText('Trend:')).toBeInTheDocument();
    expect(screen.getByText('increasing')).toBeInTheDocument();
  });

  test('handles composition view mode with sector data', async () => {
    const snapshotsWithSectors = mockSnapshots.map(snapshot => ({
      ...snapshot,
      assets: snapshot.assets.map((asset, index) => ({
        ...asset,
        sector: index === 0 ? 'Technology' : 'Communication Services',
      })),
    }));

    render(<UniverseEvolution {...defaultProps} viewMode="composition" snapshots={snapshotsWithSectors} />);

    await waitFor(() => {
      const chartData = screen.getByTestId('chart-data');
      const dataObj = JSON.parse(chartData.textContent || '{}');
      expect(dataObj.datasets.some((dataset: any) => dataset.label === 'Technology')).toBe(true);
    });
  });

  test('handles turnover view mode', async () => {
    render(<UniverseEvolution {...defaultProps} viewMode="turnover" snapshots={mockSnapshots} />);

    await waitFor(() => {
      const chartData = screen.getByTestId('chart-data');
      const dataObj = JSON.parse(chartData.textContent || '{}');
      expect(dataObj.datasets[0].label).toBe('Turnover Rate (%)');
    });
  });

  test('shows no data message when snapshots are empty', () => {
    render(<UniverseEvolution {...defaultProps} snapshots={[]} />);

    expect(screen.getByText('No Chart Data')).toBeInTheDocument();
    expect(screen.getByText('No historical data available for the selected view mode.')).toBeInTheDocument();
  });
});