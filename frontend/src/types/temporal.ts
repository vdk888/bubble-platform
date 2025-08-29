// Temporal Universe Types
// Based on backend API responses from temporal universe endpoints

import { Asset } from './index';

// Asset composition data within a snapshot
export interface AssetComposition {
  symbol: string;
  name: string;
  weight?: number;
  reason_added?: string;
  sector?: string;
  market_cap?: number;
  added_at?: string;
}

// Universe snapshot data structure
export interface UniverseSnapshot {
  id: string;
  universe_id: string;
  snapshot_date: string;
  assets: AssetComposition[];
  screening_criteria?: Record<string, any>;
  turnover_rate?: number;
  assets_added?: string[];
  assets_removed?: string[];
  performance_metrics?: {
    expected_return?: number;
    volatility?: number;
    sharpe_estimate?: number;
  };
  created_at: string;
}

// Timeline response from GET /{universe_id}/timeline
export interface UniverseTimelineResponse {
  success: boolean;
  data: UniverseSnapshot[];
  message: string;
  metadata: {
    universe_id: string;
    period_start: string;
    period_end: string;
    frequency: string;
    total_snapshots: number;
    avg_turnover_rate?: number;
    timeline_statistics?: {
      min_asset_count: number;
      max_asset_count: number;
      avg_asset_count: number;
      most_stable_assets: string[];
      highest_turnover_periods: string[];
    };
  };
}

// Snapshots list response from GET /{universe_id}/snapshots
export interface UniverseSnapshotsResponse {
  success: boolean;
  data: UniverseSnapshot[];
  message: string;
  metadata: {
    universe_id: string;
    total_snapshots: number;
    date_range: {
      earliest_snapshot: string;
      latest_snapshot: string;
    };
    pagination?: {
      page: number;
      per_page: number;
      total_pages: number;
    };
  };
}

// Point-in-time composition from GET /{universe_id}/composition/{date}
export interface CompositionAtDateResponse {
  success: boolean;
  data: {
    snapshot_date: string;
    universe_id: string;
    assets: AssetComposition[];
    context: {
      is_exact_match: boolean;
      nearest_snapshot_date?: string;
      days_difference?: number;
      interpolation_method?: string;
    };
  };
  message: string;
  metadata: {
    query_date: string;
    universe_name: string;
    asset_count: number;
  };
}

// Snapshot creation request and response
export interface CreateSnapshotRequest {
  snapshot_date?: string; // Optional, defaults to current date
  screening_criteria?: Record<string, any>;
  force_update?: boolean;
}

export interface CreateSnapshotResponse {
  success: boolean;
  data: UniverseSnapshot;
  message: string;
  metadata: {
    universe_id: string;
    previous_snapshot_date?: string;
    turnover_analysis?: {
      turnover_rate: number;
      assets_added_count: number;
      assets_removed_count: number;
      assets_unchanged_count: number;
    };
  };
}

// Backfill request and response
export interface BackfillHistoryRequest {
  start_date: string;
  end_date: string;
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  overwrite_existing?: boolean;
}

export interface BackfillHistoryResponse {
  success: boolean;
  data: {
    universe_id: string;
    snapshots_created: number;
    snapshots_updated: number;
    snapshots_skipped: number;
    date_range: {
      start_date: string;
      end_date: string;
    };
    frequency: string;
  };
  message: string;
  metadata: {
    processing_time_seconds: number;
    total_snapshots_processed: number;
    error_count: number;
    warnings: string[];
  };
}

// Turnover analysis for patterns and trends
export interface TurnoverAnalysis {
  period_start: string;
  period_end: string;
  average_turnover_rate: number;
  turnover_trend: 'increasing' | 'decreasing' | 'stable';
  turnover_volatility: number;
  periods: Array<{
    date: string;
    turnover_rate: number;
    assets_added: number;
    assets_removed: number;
    total_assets: number;
  }>;
  asset_stability: {
    most_stable_assets: string[];
    most_volatile_assets: string[];
    core_holdings: string[]; // Assets present in >80% of snapshots
  };
}

// Date range utilities for timeline queries
export interface DateRange {
  start_date: string;
  end_date: string;
}

export interface TimelineFilter {
  date_range: DateRange;
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  show_empty_periods?: boolean;
  include_turnover_analysis?: boolean;
}

// Component props interfaces
export interface UniverseTimelineProps {
  universe_id: string;
  snapshots?: UniverseSnapshot[];
  loading?: boolean;
  error?: string;
  onSnapshotSelect?: (snapshot: UniverseSnapshot) => void;
  onAssetCompositionView?: (snapshot: UniverseSnapshot) => void;
  onDateRangeChange?: (range: DateRange) => void;
  onFrequencyChange?: (frequency: string) => void;
  showTurnoverColumn?: boolean;
  showActionsColumn?: boolean;
}

export interface TemporalUniverseContextType {
  // Current state
  selectedUniverse?: string;
  snapshots: UniverseSnapshot[];
  timeline: UniverseSnapshot[];
  loading: boolean;
  error: string | null;
  
  // Current filters
  dateRange: DateRange;
  frequency: string;
  
  // Actions
  loadTimeline: (universeId: string, filters: TimelineFilter) => Promise<void>;
  loadSnapshots: (universeId: string) => Promise<void>;
  createSnapshot: (universeId: string, request: CreateSnapshotRequest) => Promise<UniverseSnapshot>;
  getCompositionAtDate: (universeId: string, date: string) => Promise<AssetComposition[]>;
  backfillHistory: (universeId: string, request: BackfillHistoryRequest) => Promise<void>;
  
  // Utilities
  calculateTurnoverAnalysis: (snapshots: UniverseSnapshot[]) => TurnoverAnalysis;
  clearError: () => void;
  setDateRange: (range: DateRange) => void;
  setFrequency: (frequency: string) => void;
}

// Hook return types
export interface UseUniverseTimelineReturn {
  timeline: UniverseSnapshot[];
  loading: boolean;
  error: string | null;
  metadata: UniverseTimelineResponse['metadata'] | null;
  refetch: () => Promise<void>;
}

export interface UseUniverseSnapshotsReturn {
  snapshots: UniverseSnapshot[];
  loading: boolean;
  error: string | null;
  metadata: UniverseSnapshotsResponse['metadata'] | null;
  refetch: () => Promise<void>;
  createSnapshot: (request: CreateSnapshotRequest) => Promise<UniverseSnapshot>;
}

export interface UseTurnoverAnalysisReturn {
  analysis: TurnoverAnalysis | null;
  loading: boolean;
  error: string | null;
  calculateAnalysis: (snapshots: UniverseSnapshot[]) => void;
}

// Table column definitions for UniverseTimeline component
export interface TimelineColumn {
  key: keyof UniverseSnapshot | 'actions';
  header: string;
  sortable?: boolean;
  width?: string;
  formatter?: (value: any, snapshot: UniverseSnapshot) => string | React.ReactNode;
}

// Loading and error states
export interface TemporalLoadingState {
  timeline: boolean;
  snapshots: boolean;
  composition: boolean;
  backfill: boolean;
  creating: boolean;
}

export interface TemporalErrorState {
  timeline: string | null;
  snapshots: string | null;
  composition: string | null;
  backfill: string | null;
  creating: string | null;
}