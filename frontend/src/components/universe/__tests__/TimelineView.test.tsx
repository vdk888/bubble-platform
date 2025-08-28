import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TimelineView from '../TimelineView';
import { UniverseSnapshot } from '../../../types/temporal';

// Mock the temporal universe hooks
jest.mock('../../../hooks/useTemporalUniverse', () => ({
  useUniverseTimeline: jest.fn(() => ({
    timeline: [],
    loading: false,
    error: null,
    metadata: null,
    refetch: jest.fn()
  })),
  useDateRangePresets: jest.fn(() => ({
    last30Days: {
      start_date: '2024-07-29',
      end_date: '2024-08-28'
    },
    last3Months: {
      start_date: '2024-05-28',
      end_date: '2024-08-28'
    },
    last6Months: {
      start_date: '2024-02-28',
      end_date: '2024-08-28'
    },
    lastYear: {
      start_date: '2023-08-28',
      end_date: '2024-08-28'
    },
    last2Years: {
      start_date: '2022-08-28',
      end_date: '2024-08-28'
    },
    last5Years: {
      start_date: '2019-08-28',
      end_date: '2024-08-28'
    },
    ytd: {
      start_date: '2024-01-01',
      end_date: '2024-08-28'
    }
  }))
}));

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  ZoomInIcon: () => <div data-testid="zoom-in-icon">ZoomIn</div>,
  ZoomOutIcon: () => <div data-testid="zoom-out-icon">ZoomOut</div>,
  PlayIcon: () => <div data-testid="play-icon">Play</div>,
  CalendarIcon: () => <div data-testid="calendar-icon">Calendar</div>,
  TrendingUpIcon: () => <div data-testid="trending-up-icon">TrendingUp</div>,
  AlertTriangleIcon: () => <div data-testid="alert-triangle-icon">AlertTriangle</div>,
  InfoIcon: () => <div data-testid="info-icon">Info</div>,
  ChevronLeftIcon: () => <div data-testid="chevron-left-icon">ChevronLeft</div>,
  ChevronRightIcon: () => <div data-testid="chevron-right-icon">ChevronRight</div>
}));

// Sample test data
const createMockSnapshot = (
  id: string,
  date: string,
  assetCount: number,
  turnoverRate: number,
  assetsAdded: number = 0,
  assetsRemoved: number = 0
): UniverseSnapshot => ({
  id,
  universe_id: 'test-universe',
  snapshot_date: date,
  assets: Array(assetCount).fill(null).map((_, i) => ({
    symbol: `ASSET${i + 1}`,
    name: `Asset ${i + 1}`,
    weight: 1 / assetCount,
    sector: 'Technology'
  })),
  turnover_rate: turnoverRate,
  assets_added: Array(assetsAdded).fill(null).map((_, i) => `ADDED${i + 1}`),
  assets_removed: Array(assetsRemoved).fill(null).map((_, i) => `REMOVED${i + 1}`),
  performance_metrics: {
    expected_return: 0.08,
    volatility: 0.15,
    sharpe_estimate: 0.53
  },
  created_at: date
});

const mockSnapshots: UniverseSnapshot[] = [
  createMockSnapshot('snap1', '2024-01-15', 10, 0.05, 1, 0), // Low turnover
  createMockSnapshot('snap2', '2024-03-15', 12, 0.15, 3, 1), // Moderate turnover
  createMockSnapshot('snap3', '2024-06-15', 8, 0.30, 2, 4),  // High turnover
  createMockSnapshot('snap4', '2024-08-15', 11, 0.08, 2, 1), // Low turnover
];

describe('TimelineView', () => {
  const defaultProps = {
    snapshots: mockSnapshots,
    selectedDate: null,
    onDateSelect: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Rendering', () => {
    it('renders empty state when no snapshots provided', () => {
      render(
        <TimelineView
          {...defaultProps}
          snapshots={[]}
        />
      );

      expect(screen.getByTestId('calendar-icon')).toBeInTheDocument();
      expect(screen.getByText('No timeline data available')).toBeInTheDocument();
    });

    it('renders timeline with snapshots', () => {
      render(<TimelineView {...defaultProps} />);

      expect(screen.getByText('Universe Timeline')).toBeInTheDocument();
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument();
      
      // Should render SVG timeline
      const svg = screen.getByRole('application');
      expect(svg).toHaveAttribute('aria-label', 'Interactive timeline for universe evolution');
    });

    it('renders zoom controls when showZoomControls is true', () => {
      render(<TimelineView {...defaultProps} showZoomControls={true} />);

      expect(screen.getByText('1Y')).toBeInTheDocument();
      expect(screen.getByText('2Y')).toBeInTheDocument();
      expect(screen.getByText('5Y')).toBeInTheDocument();
      expect(screen.getByText('All')).toBeInTheDocument();
    });

    it('hides zoom controls when showZoomControls is false', () => {
      render(<TimelineView {...defaultProps} showZoomControls={false} />);

      expect(screen.queryByText('1Y')).not.toBeInTheDocument();
      expect(screen.queryByText('2Y')).not.toBeInTheDocument();
    });

    it('renders legend with turnover level indicators', () => {
      render(<TimelineView {...defaultProps} />);

      expect(screen.getByText('Low turnover')).toBeInTheDocument();
      expect(screen.getByText('Moderate')).toBeInTheDocument();
      expect(screen.getByText('High turnover')).toBeInTheDocument();
    });

    it('applies custom height prop', () => {
      const { container } = render(<TimelineView {...defaultProps} height={200} />);
      
      const timelineContainer = container.querySelector('div[style*="height: 200px"]');
      expect(timelineContainer).toBeInTheDocument();
    });
  });

  describe('Timeline Markers', () => {
    it('renders markers for each snapshot', () => {
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      const circles = within(svg).getAllByRole('button'); // Markers are clickable
      expect(circles).toHaveLength(mockSnapshots.length);
    });

    it('applies correct visual styling based on turnover levels', async () => {
      const { container } = render(<TimelineView {...defaultProps} />);
      
      // Check that different marker sizes are rendered for different turnover levels
      const svg = container.querySelector('svg');
      const circles = svg?.querySelectorAll('circle[r]') || [];
      
      // Should have different radius values for different turnover levels
      const radii = Array.from(circles).map(circle => circle.getAttribute('r'));
      const uniqueRadii = [...new Set(radii)];
      expect(uniqueRadii.length).toBeGreaterThan(1);
    });

    it('shows selection indicator for selected date', () => {
      render(
        <TimelineView
          {...defaultProps}
          selectedDate="2024-03-15"
        />
      );

      const svg = screen.getByRole('application');
      // Should render selection line indicator
      const selectionLines = svg.querySelectorAll('line[stroke-dasharray="4,4"]');
      expect(selectionLines.length).toBeGreaterThan(0);
    });
  });

  describe('Interactions', () => {
    it('calls onDateSelect when marker is clicked', async () => {
      const onDateSelect = jest.fn();
      const user = userEvent.setup();

      render(
        <TimelineView
          {...defaultProps}
          onDateSelect={onDateSelect}
        />
      );

      const svg = screen.getByRole('application');
      const firstMarker = within(svg).getAllByRole('button')[0];
      
      await user.click(firstMarker);

      expect(onDateSelect).toHaveBeenCalledWith('2024-01-15');
    });

    it('handles zoom control clicks', async () => {
      const user = userEvent.setup();
      render(<TimelineView {...defaultProps} showZoomControls={true} />);

      const twoYearButton = screen.getByText('2Y');
      await user.click(twoYearButton);

      // Button should become active (blue background)
      expect(twoYearButton).toHaveClass('bg-blue-600', 'text-white');
    });

    it('handles keyboard navigation', async () => {
      const onDateSelect = jest.fn();
      const user = userEvent.setup();

      render(
        <TimelineView
          {...defaultProps}
          onDateSelect={onDateSelect}
        />
      );

      const svg = screen.getByRole('application');
      
      // Focus the timeline
      await user.click(svg);
      
      // Navigate with arrow keys
      await user.keyboard('[ArrowRight]');
      await user.keyboard('[Enter]');

      expect(onDateSelect).toHaveBeenCalled();
    });

    it('handles Home/End key navigation', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      await user.click(svg);
      
      // Should not throw errors
      await user.keyboard('[Home]');
      await user.keyboard('[End]');
    });

    it('shows tooltip on marker hover', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      const firstMarker = within(svg).getAllByRole('button')[0];
      
      await user.hover(firstMarker);

      await waitFor(() => {
        expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument();
        expect(screen.getByText(/Assets: 10/)).toBeInTheDocument();
        expect(screen.getByText(/Turnover: 5.0%/)).toBeInTheDocument();
      });
    });

    it('hides tooltip on marker unhover', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      const firstMarker = within(svg).getAllByRole('button')[0];
      
      await user.hover(firstMarker);
      await waitFor(() => {
        expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument();
      });
      
      await user.unhover(firstMarker);
      await waitFor(() => {
        expect(screen.queryByText(/Jan 15, 2024/)).not.toBeInTheDocument();
      });
    });
  });

  describe('Tooltip Content', () => {
    it('displays asset count and turnover in tooltip', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      const moderateTurnoverMarker = within(svg).getAllByRole('button')[1]; // March snapshot
      
      await user.hover(moderateTurnoverMarker);

      await waitFor(() => {
        expect(screen.getByText(/Assets: 12/)).toBeInTheDocument();
        expect(screen.getByText(/Turnover: 15.0%/)).toBeInTheDocument();
      });
    });

    it('shows asset changes when highlightChanges is enabled', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} highlightChanges={true} />);

      const svg = screen.getByRole('application');
      const highTurnoverMarker = within(svg).getAllByRole('button')[2]; // June snapshot
      
      await user.hover(highTurnoverMarker);

      await waitFor(() => {
        expect(screen.getByText(/\+2 \/ -4 assets/)).toBeInTheDocument();
      });
    });

    it('handles null turnover rate gracefully', async () => {
      const snapshotsWithNullTurnover = [
        {
          ...mockSnapshots[0],
          turnover_rate: null
        }
      ];

      const user = userEvent.setup();
      
      render(
        <TimelineView 
          {...defaultProps}
          snapshots={snapshotsWithNullTurnover}
        />
      );

      const svg = screen.getByRole('application');
      const marker = within(svg).getAllByRole('button')[0];
      
      await user.hover(marker);

      // Should not show turnover rate when null
      await waitFor(() => {
        expect(screen.getByText(/Assets: 10/)).toBeInTheDocument();
        expect(screen.queryByText(/Turnover:/)).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('provides proper ARIA labels', () => {
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      expect(svg).toHaveAttribute('aria-label', 'Interactive timeline for universe evolution');
      expect(svg).toHaveAttribute('tabIndex', '0');
    });

    it('supports keyboard focus management', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      
      // Should be focusable
      await user.tab();
      expect(svg).toHaveFocus();
    });

    it('provides semantic button elements for markers', () => {
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      const markers = within(svg).getAllByRole('button');
      
      expect(markers).toHaveLength(mockSnapshots.length);
    });
  });

  describe('Date Formatting and Axis', () => {
    it('formats dates correctly in US format', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} />);

      const svg = screen.getByRole('application');
      const firstMarker = within(svg).getAllByRole('button')[0];
      
      await user.hover(firstMarker);

      await waitFor(() => {
        // Should format as "Jan 15, 2024"
        expect(screen.getByText('Jan 15, 2024')).toBeInTheDocument();
      });
    });

    it('renders axis ticks with appropriate intervals', () => {
      const { container } = render(<TimelineView {...defaultProps} />);
      
      const svg = container.querySelector('svg');
      const ticks = svg?.querySelectorAll('line[stroke="#9CA3AF"]') || [];
      
      // Should render axis ticks
      expect(ticks.length).toBeGreaterThan(0);
    });

    it('renders axis labels', () => {
      const { container } = render(<TimelineView {...defaultProps} />);
      
      const svg = container.querySelector('svg');
      const labels = svg?.querySelectorAll('text[fill="#6B7280"]') || [];
      
      // Should render axis labels
      expect(labels.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('handles single snapshot', () => {
      render(
        <TimelineView
          {...defaultProps}
          snapshots={[mockSnapshots[0]]}
        />
      );

      const svg = screen.getByRole('application');
      const markers = within(svg).getAllByRole('button');
      expect(markers).toHaveLength(1);
    });

    it('handles snapshots with zero turnover', () => {
      const zeroTurnoverSnapshot = [
        createMockSnapshot('zero', '2024-01-15', 10, 0, 0, 0)
      ];

      render(
        <TimelineView
          {...defaultProps}
          snapshots={zeroTurnoverSnapshot}
        />
      );

      const svg = screen.getByRole('application');
      expect(within(svg).getAllByRole('button')).toHaveLength(1);
    });

    it('handles very high turnover rates', () => {
      const highTurnoverSnapshot = [
        createMockSnapshot('high', '2024-01-15', 10, 0.95, 8, 7)
      ];

      render(
        <TimelineView
          {...defaultProps}
          snapshots={highTurnoverSnapshot}
        />
      );

      const svg = screen.getByRole('application');
      expect(within(svg).getAllByRole('button')).toHaveLength(1);
    });

    it('handles snapshots without asset arrays', () => {
      const snapshotWithoutAssets = [{
        ...mockSnapshots[0],
        assets: undefined as any,
        assets_added: undefined,
        assets_removed: undefined
      }];

      render(
        <TimelineView
          {...defaultProps}
          snapshots={snapshotWithoutAssets}
        />
      );

      // Should not crash
      const svg = screen.getByRole('application');
      expect(svg).toBeInTheDocument();
    });
  });

  describe('Performance and Memory', () => {
    it('handles large dataset efficiently', () => {
      // Create 100 snapshots
      const largeDataset = Array(100).fill(null).map((_, i) => 
        createMockSnapshot(
          `snap-${i}`,
          `2024-0${Math.floor(i/30) + 1}-${(i % 30) + 1}`.padStart(10, '0'),
          Math.floor(Math.random() * 20) + 5,
          Math.random() * 0.4,
          Math.floor(Math.random() * 5),
          Math.floor(Math.random() * 5)
        )
      );

      const startTime = performance.now();
      
      render(
        <TimelineView
          {...defaultProps}
          snapshots={largeDataset}
        />
      );

      const endTime = performance.now();
      
      // Should render within reasonable time (< 100ms)
      expect(endTime - startTime).toBeLessThan(100);

      // Should still render all markers
      const svg = screen.getByRole('application');
      const markers = within(svg).getAllByRole('button');
      expect(markers).toHaveLength(largeDataset.length);
    });

    it('handles rapid prop changes without memory leaks', () => {
      const { rerender } = render(<TimelineView {...defaultProps} />);

      // Rapidly change selected date
      for (let i = 0; i < 10; i++) {
        rerender(
          <TimelineView
            {...defaultProps}
            selectedDate={mockSnapshots[i % mockSnapshots.length].snapshot_date}
          />
        );
      }

      // Should not crash and should render final state
      expect(screen.getByText('Universe Timeline')).toBeInTheDocument();
    });
  });

  describe('Integration with Zoom Controls', () => {
    it('changes active zoom level on button click', async () => {
      const user = userEvent.setup();
      
      render(<TimelineView {...defaultProps} showZoomControls={true} />);

      // Initially 1Y should be active
      expect(screen.getByText('1Y')).toHaveClass('bg-blue-600', 'text-white');

      // Click 2Y
      await user.click(screen.getByText('2Y'));

      expect(screen.getByText('2Y')).toHaveClass('bg-blue-600', 'text-white');
      expect(screen.getByText('1Y')).not.toHaveClass('bg-blue-600', 'text-white');
    });

    it('filters snapshots based on zoom level', async () => {
      const user = userEvent.setup();
      
      // Create snapshots spanning multiple years
      const multiYearSnapshots = [
        createMockSnapshot('old1', '2020-01-15', 10, 0.05),
        createMockSnapshot('old2', '2021-03-15', 12, 0.15),
        createMockSnapshot('recent1', '2024-06-15', 8, 0.30),
        createMockSnapshot('recent2', '2024-08-15', 11, 0.08),
      ];

      render(
        <TimelineView
          {...defaultProps}
          snapshots={multiYearSnapshots}
          showZoomControls={true}
        />
      );

      // Click "All" to show all snapshots
      await user.click(screen.getByText('All'));

      const svg = screen.getByRole('application');
      const allMarkers = within(svg).getAllByRole('button');
      expect(allMarkers.length).toBeGreaterThan(0);
    });
  });
});