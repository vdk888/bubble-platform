import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AssetSearch from '../AssetSearch';

// Mock the API service
jest.mock('../../../services/api', () => ({
  assetAPI: {
    search: jest.fn().mockResolvedValue({
      success: true,
      data: [
        {
          symbol: 'AAPL',
          name: 'Apple Inc.',
          sector: 'Technology',
          industry: 'Consumer Electronics',
          market_cap: 3000000000000,
          is_valid: true
        },
        {
          symbol: 'GOOGL',
          name: 'Alphabet Inc.',
          sector: 'Technology',
          industry: 'Internet Services',
          market_cap: 2000000000000,
          is_valid: true
        }
      ]
    }),
    validate: jest.fn().mockResolvedValue({
      success: true,
      data: [
        { symbol: 'AAPL', is_valid: true, confidence: 1.0 },
        { symbol: 'GOOGL', is_valid: true, confidence: 0.95 }
      ]
    }),
    getSectors: jest.fn().mockResolvedValue({
      success: true,
      data: ['Technology', 'Healthcare', 'Finance']
    })
  }
}));

describe('AssetSearch', () => {
  const mockOnAssetSelect = jest.fn();
  const mockOnClose = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders search input and handles typing', async () => {
    const user = userEvent.setup();
    render(<AssetSearch onAssetSelect={mockOnAssetSelect} onClose={mockOnClose} />);
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    expect(searchInput).toBeInTheDocument();
    
    await user.type(searchInput, 'AAPL');
    expect(searchInput).toHaveValue('AAPL');
  });

  test('displays search results when typing', async () => {
    const user = userEvent.setup();
    render(<AssetSearch onAssetSelect={mockOnAssetSelect} onClose={mockOnClose} />);
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    await user.type(searchInput, 'App');
    
    await waitFor(() => {
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });
  });

  test('calls onAssetSelect when asset is clicked', async () => {
    const user = userEvent.setup();
    render(<AssetSearch onAssetSelect={mockOnAssetSelect} onClose={mockOnClose} />);
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    await user.type(searchInput, 'Apple');
    
    await waitFor(() => {
      const appleResult = screen.getByText('Apple Inc.');
      expect(appleResult).toBeInTheDocument();
    });
    
    const appleResult = screen.getByText('Apple Inc.');
    await user.click(appleResult);
    
    expect(mockOnAssetSelect).toHaveBeenCalledWith(expect.objectContaining({
      symbol: 'AAPL',
      name: 'Apple Inc.'
    }));
  });

  test('shows validation feedback for selected assets', async () => {
    const user = userEvent.setup();
    render(<AssetSearch onAssetSelect={mockOnAssetSelect} onClose={mockOnClose} />);
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    await user.type(searchInput, 'AAPL');
    
    await waitFor(() => {
      expect(screen.getByText(/apple inc/i)).toBeInTheDocument();
    });
    
    // Click on asset to select it
    const appleResult = screen.getByText(/apple inc/i);
    await user.click(appleResult);
    
    // Should show validation status
    await waitFor(() => {
      expect(screen.getByText(/valid/i) || screen.getByTestId('validation-success')).toBeTruthy();
    });
  });

  test('handles empty search results gracefully', async () => {
    // Mock empty search results
    const mockAssetAPI = require('../../../services/api').assetAPI;
    mockAssetAPI.search.mockResolvedValueOnce({
      success: true,
      data: []
    });
    
    const user = userEvent.setup();
    render(<AssetSearch onAssetSelect={mockOnAssetSelect} onClose={mockOnClose} />);
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    await user.type(searchInput, 'NONEXISTENT');
    
    await waitFor(() => {
      expect(screen.getByText(/no assets found/i) || screen.getByText(/no results/i)).toBeTruthy();
    });
  });

  test('shows loading state during search', async () => {
    // Mock delayed search response
    const mockAssetAPI = require('../../../services/api').assetAPI;
    mockAssetAPI.search.mockImplementationOnce(
      () => new Promise(resolve => setTimeout(() => resolve({
        success: true,
        data: []
      }), 100))
    );
    
    const user = userEvent.setup();
    render(<AssetSearch onAssetSelect={mockOnAssetSelect} onClose={mockOnClose} />);
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    await user.type(searchInput, 'AAPL');
    
    // Should show loading indicator
    expect(screen.getByText(/searching/i) || screen.getByRole('progressbar')).toBeTruthy();
  });

  test('filters by sector when sector filter is provided', async () => {
    const user = userEvent.setup();
    render(
      <AssetSearch 
        onAssetSelect={mockOnAssetSelect} 
        onClose={mockOnClose}
        sectorFilter="Technology"
      />
    );
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    await user.type(searchInput, 'tech');
    
    await waitFor(() => {
      // Should only show technology sector assets
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText('Alphabet Inc.')).toBeInTheDocument();
    });
  });

  test('clears search results when input is cleared', async () => {
    const user = userEvent.setup();
    render(<AssetSearch onAssetSelect={mockOnAssetSelect} onClose={mockOnClose} />);
    
    const searchInput = screen.getByPlaceholderText(/search for assets/i);
    await user.type(searchInput, 'Apple');
    
    await waitFor(() => {
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    });
    
    await user.clear(searchInput);
    
    await waitFor(() => {
      expect(screen.queryByText('Apple Inc.')).not.toBeInTheDocument();
    });
  });
});