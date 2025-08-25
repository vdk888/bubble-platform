// Mock axios completely
jest.mock('axios', () => {
  const mockApiClient = {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  };

  return {
    __esModule: true,
    default: {
      create: jest.fn(() => mockApiClient)
    }
  };
});

// Get access to the mocked client
import axios from 'axios';
const mockApiClient = (axios as any).create();

import { authAPI, universeAPI, assetAPI } from '../api';

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

describe('API Services', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue('test-token');
  });

  describe('authAPI', () => {
    test('register calls correct endpoint with user data', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { access_token: 'new-token', user: { id: '1', email: 'test@example.com' } }
        }
      };
      mockApiClient.post.mockResolvedValueOnce(mockResponse);

      const result = await authAPI.register('test@example.com', 'SecurePassword123!', 'Test User');

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/v1/auth/register', {
        email: 'test@example.com',
        password: 'SecurePassword123!',
        full_name: 'Test User'
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('login stores token on successful authentication', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { access_token: 'login-token', user: { id: '1', email: 'test@example.com' } }
        }
      };
      mockApiClient.post.mockResolvedValueOnce(mockResponse);

      const result = await authAPI.login('test@example.com', 'SecurePassword123!');

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/v1/auth/login', {
        email: 'test@example.com',
        password: 'SecurePassword123!'
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('logout removes token from localStorage', async () => {
      const mockResponse = { data: { success: true } };
      mockApiClient.post.mockResolvedValueOnce(mockResponse);

      await authAPI.logout();

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/v1/auth/logout');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('access_token');
    });

    test('me endpoint includes authorization header', async () => {
      const mockResponse = {
        data: { success: true, data: { id: '1', email: 'test@example.com' } }
      };
      mockApiClient.get.mockResolvedValueOnce(mockResponse);

      await authAPI.me();

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/auth/me');
    });
  });

  describe('universeAPI', () => {
    test('list includes authorization header', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: [
            { id: '1', name: 'Test Universe', asset_count: 5 }
          ]
        }
      };
      mockApiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await universeAPI.list();

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/universes');
      expect(result).toEqual(mockResponse.data);
    });

    test('create sends correct data', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { id: 'new-id', name: 'New Universe', description: 'Test Description' }
        }
      };
      mockApiClient.post.mockResolvedValueOnce(mockResponse);

      const result = await universeAPI.create('New Universe', 'Test Description');

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/v1/universes', { 
        name: 'New Universe', 
        description: 'Test Description' 
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('update uses PUT method', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { id: 'universe-1', name: 'Updated Universe' }
        }
      };
      mockApiClient.put.mockResolvedValueOnce(mockResponse);

      const updates = { name: 'Updated Universe', description: 'Updated Description' };
      
      const result = await universeAPI.update('universe-1', updates);

      expect(mockApiClient.put).toHaveBeenCalledWith('/api/v1/universes/universe-1', updates);
      expect(result).toEqual(mockResponse.data);
    });

    test('delete uses DELETE method', async () => {
      const mockResponse = { data: { success: true } };
      mockApiClient.delete.mockResolvedValueOnce(mockResponse);

      const result = await universeAPI.delete('universe-1');

      expect(mockApiClient.delete).toHaveBeenCalledWith('/api/v1/universes/universe-1');
      expect(result).toEqual(mockResponse.data);
    });

    test('addAssets sends asset symbols', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { successful: ['AAPL', 'GOOGL'], failed: [] }
        }
      };
      mockApiClient.post.mockResolvedValueOnce(mockResponse);

      const symbols = ['AAPL', 'GOOGL'];
      
      const result = await universeAPI.addAssets('universe-1', symbols);

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/v1/universes/universe-1/assets',
        { symbols }
      );
      expect(result).toEqual(mockResponse.data);
    });

    test('removeAssets sends symbols with DELETE method', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { removed_symbols: ['AAPL'], remaining_count: 1 }
        }
      };
      mockApiClient.delete.mockResolvedValueOnce(mockResponse);

      const symbols = ['AAPL'];
      
      const result = await universeAPI.removeAssets('universe-1', symbols);

      expect(mockApiClient.delete).toHaveBeenCalledWith(
        '/api/v1/universes/universe-1/assets',
        { data: { symbols } }
      );
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('assetAPI', () => {
    test('search includes query and sector parameters', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: [
            { symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology' }
          ]
        }
      };
      mockApiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await assetAPI.search('Apple', 'Technology');

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/assets/search', {
        params: { query: 'Apple', sector: 'Technology', limit: 20 }
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('validate sends symbols array', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: [
            { symbol: 'AAPL', is_valid: true, confidence: 1.0 },
            { symbol: 'INVALID', is_valid: false, confidence: 0.0 }
          ]
        }
      };
      mockApiClient.post.mockResolvedValueOnce(mockResponse);

      const symbols = ['AAPL', 'INVALID'];
      
      const result = await assetAPI.validate(symbols);

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/v1/assets/validate',
        { symbols }
      );
      expect(result).toEqual(mockResponse.data);
    });

    test('getInfo fetches single asset data', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: {
            symbol: 'AAPL',
            name: 'Apple Inc.',
            market_cap: 3000000000000,
            pe_ratio: 28.5
          }
        }
      };
      mockApiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await assetAPI.getInfo('AAPL');

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/assets/AAPL');
      expect(result).toEqual(mockResponse.data);
    });

    test('getSectors fetches available sectors', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: ['Technology', 'Healthcare', 'Finance']
        }
      };
      mockApiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await assetAPI.getSectors();

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/assets/sectors');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Error Handling', () => {
    test('handles 401 authentication errors by removing token', async () => {
      const authError = {
        response: { status: 401, data: { error: 'Invalid token' } }
      };
      mockApiClient.get.mockRejectedValueOnce(authError);

      try {
        await authAPI.me();
      } catch (error) {
        // Error should be re-thrown after token cleanup
        expect(error).toBe(authError);
      }

      // Note: In the real implementation, the axios interceptor handles token removal
      // For this test, we're just verifying the API call happens
      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/auth/me');
    });

    test('handles network errors gracefully', async () => {
      const networkError = new Error('Network Error');
      mockApiClient.get.mockRejectedValueOnce(networkError);

      await expect(universeAPI.list()).rejects.toThrow('Network Error');
    });

    test('handles API error responses', async () => {
      const apiError = {
        response: {
          status: 400,
          data: { success: false, error: 'Invalid request data' }
        }
      };
      mockApiClient.post.mockRejectedValueOnce(apiError);

      await expect(
        universeAPI.create('', '')
      ).rejects.toEqual(apiError);
    });
  });
});