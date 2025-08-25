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
  console.log('🚨 AXIOS CONFIG DEBUG:', {
    method: config.method?.toUpperCase(),
    url: config.url,
    baseURL: config.baseURL,
    fullURL: (config.baseURL || '') + (config.url || ''),
    configuredBaseURL: API_BASE_URL,
    actualUrl: config.url,
    finalRequestUrl: config.baseURL ? config.baseURL + config.url : config.url
  });
  
  // Critical debugging: Check if baseURL is being changed somehow
  if (config.baseURL !== API_BASE_URL) {
    console.error('🚨 BASEURL MISMATCH!', {
      expected: API_BASE_URL,
      actual: config.baseURL,
      thisWillBreakProxy: true
    });
  }
  
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

// DEBUGGING: Create fresh axios instance for universe API
const freshApiClient = axios.create({
  baseURL: '',  // Force empty baseURL for proxy
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to fresh client
freshApiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  console.log('🆕 FRESH CLIENT DEBUG:', {
    baseURL: config.baseURL,
    url: config.url,
    fullURL: (config.baseURL || '') + (config.url || ''),
    shouldUseProxy: true
  });
  return config;
});

// Universe API
export const universeAPI = {
  list: async (): Promise<ServiceResult<Universe[]>> => {
    console.log('🔍 UNIVERSE API DEBUG - Before request:', {
      apiClientBaseURL: apiClient.defaults.baseURL,
      expectedBaseURL: API_BASE_URL,
      urlPath: '/api/v1/universes',
      willRequestTo: (apiClient.defaults.baseURL || '') + '/api/v1/universes'
    });
    
    console.log('🧪 TESTING FRESH CLIENT vs ORIGINAL CLIENT');
    
    // TEST: Use fresh axios client instead of shared one
    const response = await freshApiClient.get('/api/v1/universes');
    return response.data;
  },

  get: async (id: string): Promise<ServiceResult<Universe>> => {
    const response = await apiClient.get(`/api/v1/universes/${id}`);
    return response.data;
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
    const response = await apiClient.post(`/api/v1/universes/${id}/assets`, { 
      action: 'add',
      symbols 
    });
    return response.data;
  },

  removeAssets: async (id: string, asset_ids: string[]): Promise<ServiceResult> => {
    const response = await apiClient.post(`/api/v1/universes/${id}/assets`, { 
      action: 'remove',
      asset_ids 
    });
    return response.data;
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
    const params: Record<string, any> = { query: query, limit };
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

  validate: async (symbols: string[]): Promise<ServiceResult<ValidationResult[]>> => {
    const response = await apiClient.post('/api/v1/assets/validate', { symbols });
    return response.data;
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