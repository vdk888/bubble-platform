import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UniverseDashboard from '../UniverseDashboard';

// Mock the API service
jest.mock('../../../services/api', () => ({
  universeAPI: {
    list: jest.fn().mockResolvedValue({
      success: true,
      data: [
        {
          id: 'test-universe-1',
          name: 'Test Universe',
          description: 'Test Description',
          asset_count: 5,
          turnover_rate: 0.1,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z'
        }
      ]
    }),
    create: jest.fn().mockResolvedValue({
      success: true,
      data: {
        id: 'new-universe',
        name: 'New Universe',
        description: 'New Description'
      }
    })
  }
}));

// Mock Recharts components
jest.mock('recharts', () => ({
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
}));

describe('UniverseDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders dashboard in default view mode', async () => {
    render(<UniverseDashboard />);
    
    expect(screen.getByRole('heading', { name: /investment universes/i })).toBeInTheDocument();
    
    // Check for main sections
    await waitFor(() => {
      expect(screen.getByText(/test universe/i)).toBeInTheDocument();
    });
  });

  test('toggles to chat mode when chat mode is enabled', () => {
    const mockToggleChatMode = jest.fn();
    render(
      <UniverseDashboard 
        chatMode={true} 
        onToggleChatMode={mockToggleChatMode} 
      />
    );
    
    expect(screen.getByText(/ai chat interface/i)).toBeInTheDocument();
    
    const toggleButton = screen.getByRole('button', { name: /switch to dashboard/i });
    fireEvent.click(toggleButton);
    
    expect(mockToggleChatMode).toHaveBeenCalledTimes(1);
  });

  test('displays universe statistics correctly', async () => {
    render(<UniverseDashboard />);
    
    await waitFor(() => {
      // Should display total universes count
      expect(screen.getByText(/total universes/i)).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument(); // From mocked data
    });
  });

  test('shows create universe button and handles click', async () => {
    render(<UniverseDashboard />);
    
    const createButton = screen.getByRole('button', { name: /create universe/i });
    expect(createButton).toBeInTheDocument();
    
    fireEvent.click(createButton);
    
    // Should show create universe modal/form
    await waitFor(() => {
      expect(screen.getByText(/create new universe/i)).toBeInTheDocument();
    });
  });

  test('handles loading and error states', () => {
    const { rerender } = render(<UniverseDashboard />);
    
    // Initial loading state should be handled gracefully
    expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    
    // Component should not crash on rerender
    rerender(<UniverseDashboard chatMode={false} />);
    expect(screen.getByRole('heading', { name: /universe management/i })).toBeInTheDocument();
  });

  test('renders chart components for analytics', async () => {
    render(<UniverseDashboard />);
    
    await waitFor(() => {
      // Check for chart elements
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });
  });
});