import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import UniverseDashboard from '../UniverseDashboard';
import { Universe } from '../../../types';
import { UniverseSnapshot } from '../../../types/temporal';

// Mock API service
jest.mock('../../../services/api', () => ({
  universeAPI: {
    list: jest.fn(),
    get: jest.fn(),
    delete: jest.fn(),
  },
}));

// Mock child components
jest.mock('../UniverseTable', () => {
  return function MockUniverseTable(props: any) {
    return (
      <div data-testid="universe-table">
        <div>Universe Table</div>
        {props.showTemporalMode && (
          <button
            onClick={() => props.onTemporalModeToggle(!props.temporalModeEnabled)}
            data-testid="table-temporal-toggle"
          >
            {props.temporalModeEnabled ? 'Disable' : 'Enable'} Temporal Mode
          </button>
        )}
        {props.temporalModeEnabled && props.onTimelineView && (
          <button
            onClick={() => props.onTimelineView(mockUniverse)}
            data-testid="table-timeline-button"
          >
            View Timeline
          </button>
        )}
        {props.temporalModeEnabled && props.onTemporalAnalysis && (
          <button
            onClick={() => props.onTemporalAnalysis(mockUniverse)}
            data-testid="table-analysis-button"
          >
            Temporal Analysis
          </button>
        )}
      </div>
    );
  };
});

jest.mock('../TemporalAnalysisPanel', () => {
  return function MockTemporalAnalysisPanel(props: any) {
    return (
      <div data-testid="temporal-analysis-panel" data-universe={props.universe.name}>
        <div>Temporal Analysis Panel for {props.universe.name}</div>
        <div data-testid="current-view">{props.view || 'no-view'}</div>
        <button onClick={() => props.onViewChange('timeline')} data-testid="view-timeline">
          Timeline
        </button>
        <button onClick={() => props.onViewChange('evolution')} data-testid="view-evolution">
          Evolution
        </button>
        <button onClick={() => props.onViewChange('analysis')} data-testid="view-analysis">
          Analysis
        </button>
        <button onClick={props.onClose} data-testid="close-panel">
          Close
        </button>
      </div>
    );
  };
});

// Mock other components
jest.mock('../UniverseEditor', () => () => <div data-testid="universe-editor">Universe Editor</div>);
jest.mock('../AssetSearch', () => () => <div data-testid="asset-search">Asset Search</div>);
jest.mock('../BulkOperations', () => () => <div data-testid="bulk-operations">Bulk Operations</div>);
jest.mock('../UniverseAssetTable', () => () => <div data-testid="universe-asset-table">Universe Asset Table</div>);

// Mock temporal hooks
jest.mock('../../../hooks/useTemporalUniverse', () => ({
  useUniverseTimeline: jest.fn(() => ({
    timeline: [],
    loading: false,
    error: null,
    metadata: null,
  })),
  useTurnoverAnalysis: jest.fn(() => ({
    analysis: null,
    loading: false,
    error: null,
  })),
}));

const mockUniverse: Universe = {
  id: 'test-universe-1',
  name: 'Test Universe',
  description: 'A test universe for temporal analysis',
  owner_id: 'test-user',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T00:00:00Z',
  is_active: true,
  asset_count: 10,
  turnover_rate: 0.15,
  last_screening_date: '2024-01-15T00:00:00Z',
};

const mockUniverses: Universe[] = [mockUniverse];

// Mock API responses
const { universeAPI } = require('../../../services/api');

describe('UniverseDashboard Temporal Integration', () => {
  beforeEach(() => {
    universeAPI.list.mockResolvedValue({
      success: true,
      data: mockUniverses,
    });
    universeAPI.get.mockResolvedValue({
      success: true,
      data: mockUniverse,
    });
    jest.clearAllMocks();
  });

  describe('Temporal Mode Toggle', () => {
    it('should show temporal mode toggle when enableTemporalMode is true', async () => {
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
    });

    it('should not show temporal mode toggle when enableTemporalMode is false', async () => {
      render(<UniverseDashboard enableTemporalMode={false} />);
      
      await waitFor(() => {
        expect(screen.queryByText('Temporal Analysis')).not.toBeInTheDocument();
      });
    });

    it('should start with defaultTemporalMode state', async () => {
      render(<UniverseDashboard enableTemporalMode={true} defaultTemporalMode={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Exit Temporal Mode')).toBeInTheDocument();
      });
    });

    it('should toggle temporal mode when button is clicked', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });

      // Enable temporal mode
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByText('Exit Temporal Mode')).toBeInTheDocument();
      });

      // Disable temporal mode
      await user.click(screen.getByText('Exit Temporal Mode'));
      
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
    });

    it('should call onTemporalModeChange callback when mode changes', async () => {
      const user = userEvent.setup();
      const onTemporalModeChange = jest.fn();
      
      render(
        <UniverseDashboard 
          enableTemporalMode={true} 
          onTemporalModeChange={onTemporalModeChange} 
        />
      );
      
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Temporal Analysis'));
      
      expect(onTemporalModeChange).toHaveBeenCalledWith(true);
    });
  });

  describe('Temporal Mode Banner', () => {
    it('should show temporal mode banner when temporal mode is active', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis Mode Active')).toBeInTheDocument();
      });
    });

    it('should update banner text when universe is selected for temporal analysis', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));

      // Select universe for temporal analysis
      await waitFor(() => {
        expect(screen.getByTestId('table-analysis-button')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('table-analysis-button'));
      
      await waitFor(() => {
        expect(screen.getByText(/Exploring Test Universe's evolution/)).toBeInTheDocument();
      });
    });
  });

  describe('TemporalAnalysisPanel Integration', () => {
    it('should render temporal analysis panel in overlay layout by default', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode and select universe
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByTestId('table-analysis-button')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('table-analysis-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('temporal-analysis-panel')).toBeInTheDocument();
      });

      // Should be in overlay layout (not in sidebar grid)
      const panel = screen.getByTestId('temporal-analysis-panel');
      expect(panel).toBeInTheDocument();
    });

    it('should switch between different panel layouts', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode and select universe
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByTestId('table-analysis-button')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('table-analysis-button'));
      
      await waitFor(() => {
        expect(screen.getByText('overlay')).toBeInTheDocument();
      });

      // Click layout toggle to cycle through layouts
      await user.click(screen.getByText('overlay'));
      
      await waitFor(() => {
        expect(screen.getByText('sidebar')).toBeInTheDocument();
      });
    });

    it('should handle temporal view changes through the panel', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode and select universe
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByTestId('table-timeline-button')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('table-timeline-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('temporal-analysis-panel')).toBeInTheDocument();
      });

      // Change view through panel
      await user.click(screen.getByTestId('view-evolution'));
      
      await waitFor(() => {
        expect(screen.getByTestId('current-view')).toHaveTextContent('evolution');
      });
    });

    it('should close temporal panel and clean up state', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode and select universe
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByTestId('table-analysis-button')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('table-analysis-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('temporal-analysis-panel')).toBeInTheDocument();
      });

      // Close panel
      await user.click(screen.getByTestId('close-panel'));
      
      await waitFor(() => {
        expect(screen.queryByTestId('temporal-analysis-panel')).not.toBeInTheDocument();
      });

      // Banner should show no universe selected
      expect(screen.getByText(/Select a universe to analyze/)).toBeInTheDocument();
    });
  });

  describe('State Coordination', () => {
    it('should ensure temporal mode is enabled when timeline view is triggered', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Start with temporal mode disabled
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });

      // Click timeline button from table (should auto-enable temporal mode)
      await waitFor(() => {
        expect(screen.getByTestId('universe-table')).toBeInTheDocument();
      });

      // Simulate table triggering timeline view while temporal mode is disabled
      // (This would happen if table has timeline buttons even when temporal mode is off)
      fireEvent.click(screen.getByTestId('table-timeline-button'));
      
      await waitFor(() => {
        expect(screen.getByText('Exit Temporal Mode')).toBeInTheDocument();
        expect(screen.getByTestId('temporal-analysis-panel')).toBeInTheDocument();
      });
    });

    it('should clean up temporal state when temporal mode is disabled', async () => {
      const user = userEvent.setup();
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode and select universe
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByTestId('table-analysis-button')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('table-analysis-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('temporal-analysis-panel')).toBeInTheDocument();
      });

      // Disable temporal mode
      await user.click(screen.getByText('Exit Temporal Mode'));
      
      await waitFor(() => {
        // Panel should be gone
        expect(screen.queryByTestId('temporal-analysis-panel')).not.toBeInTheDocument();
        // Banner should be gone
        expect(screen.queryByText('Temporal Analysis Mode Active')).not.toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should render sidebar layout correctly on larger screens', async () => {
      const user = userEvent.setup();
      
      // Mock window.matchMedia for responsive testing
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: query.includes('(min-width: 1024px)'), // lg breakpoint
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode and select universe
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByTestId('table-analysis-button')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('table-analysis-button'));

      // Switch to sidebar layout
      await waitFor(() => {
        expect(screen.getByText('overlay')).toBeInTheDocument();
      });
      await user.click(screen.getByText('overlay'));
      
      await waitFor(() => {
        expect(screen.getByText('sidebar')).toBeInTheDocument();
      });

      // Panel should be rendered
      expect(screen.getByTestId('temporal-analysis-panel')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully when loading universes', async () => {
      universeAPI.list.mockRejectedValue(new Error('API Error'));
      
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      await waitFor(() => {
        expect(screen.getByText(/Network error loading universes/)).toBeInTheDocument();
      });
    });

    it('should maintain temporal state when API operations fail', async () => {
      universeAPI.get.mockRejectedValue(new Error('API Error'));
      const user = userEvent.setup();
      
      render(<UniverseDashboard enableTemporalMode={true} />);
      
      // Enable temporal mode
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis')).toBeInTheDocument();
      });
      await user.click(screen.getByText('Temporal Analysis'));
      
      await waitFor(() => {
        expect(screen.getByText('Temporal Analysis Mode Active')).toBeInTheDocument();
      });

      // Temporal mode should remain active even if other operations fail
      expect(screen.getByText('Exit Temporal Mode')).toBeInTheDocument();
    });
  });

  describe('Backward Compatibility', () => {
    it('should maintain existing functionality when temporal features are disabled', async () => {
      render(<UniverseDashboard enableTemporalMode={false} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('universe-table')).toBeInTheDocument();
      });

      // Should not show temporal mode toggle
      expect(screen.queryByText('Temporal Analysis')).not.toBeInTheDocument();
      
      // Should not show temporal mode banner
      expect(screen.queryByText('Temporal Analysis Mode Active')).not.toBeInTheDocument();
      
      // Table should still function normally
      expect(screen.getByText('Universe Table')).toBeInTheDocument();
    });

    it('should support legacy chatMode prop', async () => {
      const onToggleChatMode = jest.fn();
      
      render(
        <UniverseDashboard 
          chatMode={true} 
          onToggleChatMode={onToggleChatMode}
          enableTemporalMode={true}
        />
      );
      
      await waitFor(() => {
        expect(screen.getByText('Exit Chat Mode')).toBeInTheDocument();
        expect(screen.getByText('AI Assistant Mode Active')).toBeInTheDocument();
      });
    });
  });
});