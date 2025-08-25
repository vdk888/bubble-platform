import axios from 'axios';
import { 
  ServiceResult, 
  Universe, 
  Asset, 
  ValidationResult, 
  BulkValidationResult,
  AssetSearchResult,
  AuthResponse,
  ProgressUpdate 
} from '../types';

// API Configuration - use proxy in development, direct URL in production
const API_BASE_URL = process.env.NODE_ENV === 'development' ? '' : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

console.log('🔧 API Configuration:', {
  NODE_ENV: process.env.NODE_ENV,
  REACT_APP_API_URL: process.env.REACT_APP_API_URL,
  API_BASE_URL
});

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add authentication token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired, clear tokens but let React handle routing
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    return Promise.reject(error);
  }
);

// Authentication API
export const authAPI = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/v1/auth/login', { email, password });
    return response.data;
  },

  register: async (email: string, password: string, full_name?: string): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/v1/auth/register', { 
      email, 
      password, 
      full_name 
    });
    return response.data;
  },

  me: async (): Promise<ServiceResult> => {
    const response = await apiClient.get('/api/v1/auth/me');
    return response.data;
  },

  logout: async (): Promise<ServiceResult> => {
    const response = await apiClient.post('/api/v1/auth/logout');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    return response.data;
  },
};


// Universe API
export const universeAPI = {
  list: async (): Promise<ServiceResult<Universe[]>> => {
    const response = await apiClient.get('/api/v1/universes');
    return response.data;
  },

  get: async (id: string): Promise<ServiceResult<Universe>> => {
    try {
      console.log('📤 API: Fetching universe details', { id });
      const response = await apiClient.get(`/api/v1/universes/${id}`);
      console.log('📥 API: Get universe response', {
        success: response.data?.success,
        universeId: response.data?.data?.id,
        universeName: response.data?.data?.name,
        assetCount: response.data?.data?.asset_count || response.data?.data?.assets?.length || 0,
        assetsLength: response.data?.data?.assets?.length || 0
      });
      
      // Ensure we return the universe data in the expected format
      const result = response.data;
      if (result.success && result.data) {
        // Transform the API response to match our Universe interface
        const universe = result.data;
        return {
          success: true,
          data: {
            ...universe,
            asset_count: universe.asset_count || universe.assets?.length || 0
          },
          message: result.message || 'Universe retrieved successfully'
        };
      }
      
      return result;
    } catch (error: any) {
      console.error('❌ API: Get universe failed', error);
      // Transform axios error to consistent format
      if (error.response?.data) {
        return {
          success: false,
          message: error.response.data.message || error.response.data.detail || 'Failed to fetch universe',
          data: undefined
        };
      }
      return {
        success: false,
        message: 'Network error while fetching universe',
        data: undefined
      };
    }
  },

  create: async (name: string, description?: string): Promise<ServiceResult<Universe>> => {
    const response = await apiClient.post('/api/v1/universes', { 
      name, 
      description 
    });
    return response.data;
  },

  update: async (id: string, data: Partial<Universe>): Promise<ServiceResult<Universe>> => {
    const response = await apiClient.put(`/api/v1/universes/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<ServiceResult> => {
    const response = await apiClient.delete(`/api/v1/universes/${id}`);
    return response.data;
  },

  addAssets: async (id: string, symbols: string[]): Promise<ServiceResult<BulkValidationResult>> => {
    try {
      console.log('📤 API: Adding assets to universe', { id, symbols });
      const response = await apiClient.post(`/api/v1/universes/${id}/assets`, { 
        symbols 
      });
      console.log('📥 API: Add assets response', {
        success: response.data?.success,
        message: response.data?.message,
        addedCount: response.data?.data?.added_count,
        totalRequested: response.data?.data?.total_requested,
        successfulSymbols: response.data?.data?.successful_symbols
      });
      
      const result = response.data;
      if (result.success) {
        console.log('✅ Assets successfully added to universe:', {
          universeId: id,
          addedSymbols: result.data?.successful_symbols || [],
          failedSymbols: result.data?.failed_symbols || []
        });
      }
      
      return result;
    } catch (error: any) {
      console.error('❌ API: Add assets failed', error);
      // Transform axios error to consistent format
      if (error.response?.data) {
        return {
          success: false,
          message: error.response.data.message || error.response.data.detail || 'Failed to add assets',
          data: undefined
        };
      }
      return {
        success: false,
        message: 'Network error while adding assets',
        data: undefined
      };
    }
  },

  removeAssets: async (id: string, symbols: string[]): Promise<ServiceResult> => {
    try {
      console.log('📤 API: Removing assets from universe', { id, symbols });
      const response = await apiClient.delete(`/api/v1/universes/${id}/assets`, { 
        data: { symbols }
      });
      console.log('📥 API: Remove assets response', {
        success: response.data?.success,
        message: response.data?.message,
        removedCount: response.data?.data?.added_count, // This is actually removed count in the API
        totalRequested: response.data?.data?.total_requested,
        successfulSymbols: response.data?.data?.successful_symbols
      });
      
      const result = response.data;
      if (result.success) {
        console.log('✅ Assets successfully removed from universe:', {
          universeId: id,
          removedSymbols: result.data?.successful_symbols || [],
          failedSymbols: result.data?.failed_symbols || []
        });
      }
      
      return result;
    } catch (error: any) {
      console.error('❌ API: Remove assets failed', error);
      // Transform axios error to consistent format
      if (error.response?.data) {
        return {
          success: false,
          message: error.response.data.message || error.response.data.detail || 'Failed to remove assets',
          data: null
        };
      }
      return {
        success: false,
        message: 'Network error while removing assets',
        data: null
      };
    }
  },
};

// Asset API
export const assetAPI = {
  search: async (
    query: string, 
    sector?: string, 
    limit: number = 20, 
    filters?: Record<string, any>
  ): Promise<ServiceResult<AssetSearchResult>> => {
    const params: Record<string, any> = { query, limit };
    if (sector) params.sector = sector;
    
    // Add multi-metric filters (Sprint 2 Step 1)
    if (filters) {
      if (filters.marketCapMin !== undefined) params.market_cap_min = filters.marketCapMin;
      if (filters.marketCapMax !== undefined) params.market_cap_max = filters.marketCapMax;
      if (filters.peRatioMin !== undefined) params.pe_ratio_min = filters.peRatioMin;
      if (filters.peRatioMax !== undefined) params.pe_ratio_max = filters.peRatioMax;
      if (filters.dividendYieldMin !== undefined) params.dividend_yield_min = filters.dividendYieldMin;
      if (filters.dividendYieldMax !== undefined) params.dividend_yield_max = filters.dividendYieldMax;
    }
    
    const response = await apiClient.get('/api/v1/assets/search', { params });
    return response.data;
  },

  getInfo: async (symbol: string): Promise<ServiceResult<Asset>> => {
    const response = await apiClient.get(`/api/v1/assets/${symbol}`);
    return response.data;
  },

  validate: async (symbols: string[]): Promise<ServiceResult<BulkValidationResult>> => {
    try {
      console.log('📤 API: Validating asset symbols', { symbols });
      const response = await apiClient.post('/api/v1/assets/validate', { symbols });
      console.log('📥 API: Validation response', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ API: Asset validation failed', error);
      // Transform axios error to consistent format
      if (error.response?.data) {
        return {
          success: false,
          message: error.response.data.message || error.response.data.detail || 'Failed to validate assets',
          data: undefined
        };
      }
      return {
        success: false,
        message: 'Network error while validating assets',
        data: undefined
      };
    }
  },

  getSectors: async (): Promise<ServiceResult<string[]>> => {
    const response = await apiClient.get('/api/v1/assets/sectors');
    return response.data;
  },
};

// Progress Tracking API
export const progressAPI = {
  getProgress: async (taskId: string): Promise<ServiceResult<ProgressUpdate>> => {
    const response = await apiClient.get(`/health/workers/progress/${taskId}`);
    return response.data;
  },
};

// Health API
export const healthAPI = {
  check: async (): Promise<ServiceResult> => {
    const response = await apiClient.get('/health');
    return response.data;
  },

  workers: async (): Promise<ServiceResult> => {
    const response = await apiClient.get('/health/workers');
    return response.data;
  },
};

export default apiClient;