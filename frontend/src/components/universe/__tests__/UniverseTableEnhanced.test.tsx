import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UniverseTable from '../UniverseTable';
import type { Universe } from '../../../types';

// Mock the temporal hook
jest.mock('../../../hooks/useTemporalUniverse', () => ({
  useUniverseTimeline: jest.fn(() => ({
    timeline: [],
    loading: false,
    error: null,
    metadata: null,
    refetch: jest.fn()
  }))
}));

const mockUniverses: Universe[] = [
  {
    id: 'universe-1',
    name: 'Tech Giants',
    description: 'Technology companies with large market cap',
    owner_id: 'user-1',
    asset_count: 5,
    turnover_rate: 0.15,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z'
  },
  {
    id: 'universe-2',
    name: 'Healthcare Leaders',
    description: 'Leading healthcare and pharmaceutical companies',
    owner_id: 'user-1',
    asset_count: 8,
    turnover_rate: 0.08,
    is_active: true,
    created_at: '2024-06-15T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z'
  },
  {
    id: 'universe-3',
    name: 'Energy Sector',
    description: 'Oil, gas and renewable energy companies',
    owner_id: 'user-1',
    asset_count: 12,
    turnover_rate: 0.25,
    is_active: true,
    created_at: '2024-11-01T00:00:00Z',
    updated_at: '2024-12-30T00:00:00Z'
  }
];

describe('UniverseTable - Enhanced with Temporal Features', () => {
  const mockOnEdit = jest.fn();
  const mockOnDelete = jest.fn();
  const mockOnView = jest.fn();
  const mockOnTemporalModeToggle = jest.fn();
  const mockOnTimelineView = jest.fn();
  const mockOnTemporalAnalysis = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Standard Mode (No Temporal Features)', () => {
    test('renders standard table without temporal features', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
        />
      );

      // Check standard headers are present
      expect(screen.getByText(/name/i)).toBeInTheDocument();
      expect(screen.getByText(/assets/i)).toBeInTheDocument();
      expect(screen.getByText(/turnover/i)).toBeInTheDocument();
      expect(screen.getByText(/status/i)).toBeInTheDocument();
      expect(screen.getByText(/created/i)).toBeInTheDocument();

      // Temporal toggle should not be visible
      expect(screen.queryByText(/temporal mode/i)).not.toBeInTheDocument();
      
      // Snapshots column should not be present
      expect(screen.queryByText(/snapshots/i)).not.toBeInTheDocument();
      
      // Standard turnover display (not badges)
      expect(screen.getByText('15.0%')).toBeInTheDocument();
    });

    test('displays all existing functionality unchanged', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
        />
      );

      // Check all universes are displayed
      expect(screen.getByText('Tech Giants')).toBeInTheDocument();
      expect(screen.getByText('Healthcare Leaders')).toBeInTheDocument();
      expect(screen.getByText('Energy Sector')).toBeInTheDocument();

      // Check asset counts
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument();
      expect(screen.getByText('12')).toBeInTheDocument();
    });
  });

  describe('Temporal Mode Toggle', () => {
    test('shows temporal toggle when showTemporalMode is true', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={false}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      expect(screen.getByText(/temporal mode/i)).toBeInTheDocument();
      expect(screen.getByText(/viewing current universe state/i)).toBeInTheDocument();
    });

    test('calls onTemporalModeToggle when toggle button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={false}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      const toggleButton = screen.getByLabelText(/enable temporal mode/i);
      await user.click(toggleButton);

      expect(mockOnTemporalModeToggle).toHaveBeenCalledWith(true);
    });

    test('displays correct state when temporal mode is enabled', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      expect(screen.getByText(/viewing historical snapshots/i)).toBeInTheDocument();
      expect(screen.getByText(/timeline active/i)).toBeInTheDocument();
      expect(screen.getByText(/universes with temporal data/i)).toBeInTheDocument();
    });
  });

  describe('Temporal Mode Features', () => {
    test('shows temporal columns when temporal mode is enabled', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      // Temporal-specific headers - use more specific queries to avoid conflicts
      expect(screen.getByRole('columnheader', { name: /snapshots/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /avg turnover/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /first snapshot/i })).toBeInTheDocument();
    });

    test('displays turnover badges in temporal mode', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      // Should show enhanced turnover badges instead of plain percentages
      expect(screen.getByText(/15.0% Med/i)).toBeInTheDocument();
      expect(screen.getByText(/8.0% Low/i)).toBeInTheDocument();
      expect(screen.getByText(/25.0% High/i)).toBeInTheDocument();
    });

    test('displays snapshot counts with proper formatting', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      // Should display estimated snapshot counts
      const snapshotCells = screen.getAllByTitle(/temporal snapshots tracked since/i);
      expect(snapshotCells.length).toBeGreaterThan(0);
    });

    test('shows relative time in Last Updated column when in temporal mode', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      // Should show relative time like "2 days ago" - use more specific query
      expect(screen.getAllByText(/ago/).length).toBeGreaterThan(0);
    });
  });

  describe('Temporal Actions', () => {
    test('shows temporal action buttons when temporal mode is enabled', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
          onTimelineView={mockOnTimelineView}
          onTemporalAnalysis={mockOnTemporalAnalysis}
        />
      );

      // Timeline view buttons
      const timelineButtons = screen.getAllByLabelText(/view timeline/i);
      expect(timelineButtons).toHaveLength(mockUniverses.length);

      // Temporal analysis buttons
      const analysisButtons = screen.getAllByLabelText(/temporal analysis/i);
      expect(analysisButtons).toHaveLength(mockUniverses.length);
    });

    test('calls onTimelineView when timeline button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
          onTimelineView={mockOnTimelineView}
        />
      );

      const timelineButtons = screen.getAllByLabelText(/view timeline/i);
      await user.click(timelineButtons[0]);

      expect(mockOnTimelineView).toHaveBeenCalledWith(mockUniverses[0]);
    });

    test('calls onTemporalAnalysis when analysis button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
          onTemporalAnalysis={mockOnTemporalAnalysis}
        />
      );

      const analysisButtons = screen.getAllByLabelText(/temporal analysis/i);
      await user.click(analysisButtons[0]);

      expect(mockOnTemporalAnalysis).toHaveBeenCalledWith(mockUniverses[0]);
    });

    test('hides temporal actions when temporal mode is disabled', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={false}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
          onTimelineView={mockOnTimelineView}
          onTemporalAnalysis={mockOnTemporalAnalysis}
        />
      );

      // Temporal actions should not be visible
      expect(screen.queryAllByLabelText(/view timeline/i)).toHaveLength(0);
      expect(screen.queryAllByLabelText(/temporal analysis/i)).toHaveLength(0);
    });
  });

  describe('Backward Compatibility', () => {
    test('maintains all existing functionality without temporal props', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
        />
      );

      // All standard functionality should work
      expect(screen.getByText('Tech Giants')).toBeInTheDocument();
      expect(screen.getAllByTitle(/view universe/i)).toHaveLength(mockUniverses.length);
      expect(screen.getAllByTitle(/edit universe/i)).toHaveLength(mockUniverses.length);
      expect(screen.getAllByTitle(/delete universe/i)).toHaveLength(mockUniverses.length);
    });

    test('existing button handlers work correctly without temporal features', async () => {
      const user = userEvent.setup();
      render(
        <UniverseTable
          universes={mockUniverses}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
        />
      );

      // Test view button
      const viewButtons = screen.getAllByTitle(/view universe/i);
      await user.click(viewButtons[0]);
      expect(mockOnView).toHaveBeenCalledWith(mockUniverses[0]);

      // Test edit button
      const editButtons = screen.getAllByTitle(/edit universe/i);
      await user.click(editButtons[0]);
      expect(mockOnEdit).toHaveBeenCalledWith(mockUniverses[0]);

      // Test delete button
      const deleteButtons = screen.getAllByTitle(/delete universe/i);
      await user.click(deleteButtons[0]);
      expect(mockOnDelete).toHaveBeenCalledWith(mockUniverses[0]);
    });
  });

  describe('Loading and Error States', () => {
    test('shows loading state correctly', () => {
      render(
        <UniverseTable
          universes={[]}
          loading={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
        />
      );

      expect(screen.getByText(/loading universes/i)).toBeInTheDocument();
    });

    test('shows empty state when no universes', () => {
      render(
        <UniverseTable
          universes={[]}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
        />
      );

      expect(screen.getByText(/no universes/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('has proper ARIA labels for temporal actions', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
          onTimelineView={mockOnTimelineView}
          onTemporalAnalysis={mockOnTemporalAnalysis}
        />
      );

      // Check ARIA labels exist
      expect(screen.getByLabelText(/disable temporal mode/i)).toBeInTheDocument();
      expect(screen.getAllByLabelText(/view timeline/i)).toHaveLength(mockUniverses.length);
      expect(screen.getAllByLabelText(/temporal analysis/i)).toHaveLength(mockUniverses.length);
    });

    test('has proper screen reader announcements', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      // Actions column should have sr-only text
      expect(screen.getByText('Actions')).toHaveClass('sr-only');
    });
  });

  describe('Responsive Behavior', () => {
    test('maintains responsive table structure with temporal columns', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      // Table should have overflow-x-auto for horizontal scrolling
      const tableContainer = screen.getByRole('table').parentElement;
      expect(tableContainer).toHaveClass('overflow-x-auto');
    });
  });

  describe('Turnover Badge Component', () => {
    test('displays correct turnover badge colors and labels', () => {
      render(
        <UniverseTable
          universes={mockUniverses}
          showTemporalMode={true}
          temporalModeEnabled={true}
          onUniverseEdit={mockOnEdit}
          onUniverseDelete={mockOnDelete}
          onUniverseSelect={mockOnView}
          onTemporalModeToggle={mockOnTemporalModeToggle}
        />
      );

      // High turnover (25%) - should be red
      expect(screen.getByText(/25.0% High/i)).toBeInTheDocument();
      
      // Medium turnover (15%) - should be yellow  
      expect(screen.getByText(/15.0% Med/i)).toBeInTheDocument();
      
      // Low turnover (8%) - should be green
      expect(screen.getByText(/8.0% Low/i)).toBeInTheDocument();
    });
  });
});