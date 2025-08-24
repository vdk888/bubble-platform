// API Response Types
export interface ServiceResult<T = any> {
  success: boolean;
  data?: T;
  message: string;
  next_actions?: string[];
  metadata?: Record<string, any>;
}

// Asset Types
export interface Asset {
  id: string;
  symbol: string;
  name: string;
  sector?: string;
  industry?: string;
  market_cap?: number;
  pe_ratio?: number;
  dividend_yield?: number;
  is_validated: boolean;
  last_validated_at?: string;
  asset_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// Universe Types
export interface Universe {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  // Asset relationships
  assets?: Asset[];
  asset_count?: number;
  turnover_rate?: number;
  last_screening_date?: string;
}

// Validation Types
export interface ValidationResult {
  symbol: string;
  is_valid: boolean;
  source: string;
  message?: string;
  asset_info?: Partial<Asset>;
  cached: boolean;
}

export interface BulkValidationResult {
  total_symbols: number;
  valid_count: number;
  invalid_count: number;
  pending_count: number;
  results: ValidationResult[];
}

// Search Types
export interface AssetSearchResult {
  assets: Asset[];
  total_count: number;
  page: number;
  per_page: number;
}

// User Types
export interface User {
  id: string;
  email: string;
  full_name?: string;
  subscription_tier: 'free' | 'pro' | 'enterprise';
  is_verified: boolean;
  created_at: string;
}

// Authentication Types
export interface AuthResponse extends ServiceResult<User> {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
}

// Component Props Types
export interface UniverseDashboardProps {
  chatMode?: boolean;
  onToggleChatMode?: () => void;
}

export interface AssetSearchProps {
  onAssetSelect: (asset: Asset) => void;
  selectedAssets?: Asset[];
  placeholder?: string;
  className?: string;
}

export interface UniverseTableProps {
  universes: Universe[];
  loading?: boolean;
  onUniverseSelect: (universe: Universe) => void;
  onUniverseEdit: (universe: Universe) => void;
  onUniverseDelete: (universe: Universe) => void;
}

// AI Integration Types
export interface AIToolCall {
  name: string;
  parameters: Record<string, any>;
  result?: any;
  error?: string;
}

export interface UniverseAITools {
  createUniverse: (name: string, symbols: string[], description?: string) => Promise<Universe>;
  searchAssets: (query: string, sector?: string) => Promise<Asset[]>;
  validateSymbols: (symbols: string[]) => Promise<ValidationResult[]>;
  bulkAddAssets: (universeId: string, symbols: string[]) => Promise<BulkValidationResult>;
}

// Progress Tracking Types
export interface ProgressUpdate {
  task_id: string;
  progress: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message?: string;
  results?: any;
}