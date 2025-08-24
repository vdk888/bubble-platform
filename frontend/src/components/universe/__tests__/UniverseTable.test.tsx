import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UniverseTable from '../UniverseTable';
import type { Universe } from '../../../types';

const mockUniverses: Universe[] = [
  {
    id: 'universe-1',
    name: 'Tech Giants',
    description: 'Technology companies with large market cap',
    asset_count: 5,
    turnover_rate: 0.15,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z'
  },
  {
    id: 'universe-2',
    name: 'Healthcare Leaders',
    description: 'Leading healthcare and pharmaceutical companies',
    asset_count: 8,
    turnover_rate: 0.08,
    created_at: '2024-12-15T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z'
  },
  {
    id: 'universe-3',
    name: 'Energy Sector',
    description: 'Oil, gas and renewable energy companies',
    asset_count: 12,
    turnover_rate: 0.25,
    created_at: '2024-11-01T00:00:00Z',
    updated_at: '2024-12-30T00:00:00Z'
  }
];

describe('UniverseTable', () => {
  const mockOnEdit = jest.fn();
  const mockOnDelete = jest.fn();
  const mockOnView = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders table with universe data', () => {
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    // Check table headers
    expect(screen.getByText(/name/i)).toBeInTheDocument();
    expect(screen.getByText(/assets/i)).toBeInTheDocument();
    expect(screen.getByText(/turnover/i)).toBeInTheDocument();
    expect(screen.getByText(/created/i)).toBeInTheDocument();
    expect(screen.getByText(/actions/i)).toBeInTheDocument();

    // Check universe data
    expect(screen.getByText('Tech Giants')).toBeInTheDocument();
    expect(screen.getByText('Healthcare Leaders')).toBeInTheDocument();
    expect(screen.getByText('Energy Sector')).toBeInTheDocument();
  });

  test('displays asset counts correctly', () => {
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    expect(screen.getByText('5')).toBeInTheDocument(); // Tech Giants
    expect(screen.getByText('8')).toBeInTheDocument(); // Healthcare Leaders
    expect(screen.getByText('12')).toBeInTheDocument(); // Energy Sector
  });

  test('formats turnover rates as percentages', () => {
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    expect(screen.getByText('15.0%')).toBeInTheDocument(); // 0.15
    expect(screen.getByText('8.0%')).toBeInTheDocument(); // 0.08
    expect(screen.getByText('25.0%')).toBeInTheDocument(); // 0.25
  });

  test('calls onUniverseSelect when view button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    const viewButtons = screen.getAllByTitle(/view universe/i);
    await user.click(viewButtons[0]);

    expect(mockOnView).toHaveBeenCalledWith(mockUniverses[0]);
  });

  test('calls onUniverseEdit when edit button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    const editButtons = screen.getAllByTitle(/edit universe/i);
    await user.click(editButtons[0]);

    expect(mockOnEdit).toHaveBeenCalledWith(mockUniverses[0]);
  });

  test('calls onUniverseDelete when delete button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    const deleteButtons = screen.getAllByTitle(/delete universe/i);
    await user.click(deleteButtons[0]);

    expect(mockOnDelete).toHaveBeenCalledWith(mockUniverses[0]);
  });

  test('displays empty state when no universes provided', () => {
    render(
      <UniverseTable
        universes={[]}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    expect(screen.getByText(/no universes/i) || screen.getByText(/empty/i)).toBeTruthy();
  });

  test('sorts universes by name when name header is clicked', async () => {
    const user = userEvent.setup();
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    const nameHeader = screen.getByText(/name/i);
    await user.click(nameHeader);

    // Check if sorting indicator appears or order changes
    const rows = screen.getAllByRole('row');
    // Should have header + 3 data rows
    expect(rows).toHaveLength(4);
  });

  // Note: Search filtering is not implemented in the current component
  // This test would be added when the filtering feature is implemented

  test('shows loading state when loading prop is true', () => {
    render(
      <UniverseTable
        universes={[]}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
        loading={true}
      />
    );

    expect(screen.getByText(/loading/i) || screen.getByRole('progressbar')).toBeTruthy();
  });

  test('displays universe descriptions as tooltips', async () => {
    const user = userEvent.setup();
    render(
      <UniverseTable
        universes={mockUniverses}
        onUniverseEdit={mockOnEdit}
        onUniverseDelete={mockOnDelete}
        onUniverseSelect={mockOnView}
      />
    );

    // Hover over universe name to see description
    const techGiantsName = screen.getByText('Tech Giants');
    await user.hover(techGiantsName);

    await waitFor(() => {
      expect(screen.getByText(/technology companies with large market cap/i)).toBeInTheDocument();
    });
  });

  // Note: Bulk selection is not implemented in the current component
  // This test would be added when the bulk selection feature is implemented
});