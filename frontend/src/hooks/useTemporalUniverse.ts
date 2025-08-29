import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { temporalUniverseAPI } from '../services/api';
import {
  UniverseSnapshot,
  UniverseTimelineResponse,
  UniverseSnapshotsResponse,
  CompositionAtDateResponse,
  CreateSnapshotRequest,
  BackfillHistoryRequest,
  TimelineFilter,
  TurnoverAnalysis,
  UseUniverseTimelineReturn,
  UseUniverseSnapshotsReturn,
  UseTurnoverAnalysisReturn,
  DateRange,
  AssetComposition
} from '../types/temporal';

/**
 * Hook for managing universe timeline data
 * Handles date range filtering, frequency selection, and timeline visualization
 */
export function useUniverseTimeline(
  universeId: string,
  initialFilters?: Partial<TimelineFilter>
): UseUniverseTimelineReturn {
  const [timeline, setTimeline] = useState<UniverseSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<UniverseTimelineResponse['metadata'] | null>(null);
  
  // Track the last request to prevent duplicate calls
  const lastRequestRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);

  // Default filters - last 6 months, monthly frequency  
  // Use a stable date that doesn't change on every render
  const defaultFilters: TimelineFilter = useMemo(() => {
    const now = Date.now();
    const endDate = new Date(now);
    const startDate = new Date(now);
    startDate.setMonth(startDate.getMonth() - 6);

    return {
      date_range: {
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0]
      },
      frequency: 'monthly',
      show_empty_periods: false,
      include_turnover_analysis: true
    };
  }, []); // This memo only runs once on mount

  const filters = useMemo(() => ({
    ...defaultFilters,
    ...initialFilters
  }), [defaultFilters, JSON.stringify(initialFilters || {})]); // Use JSON.stringify for stable comparison

  const fetchTimeline = useCallback(async () => {
    if (!universeId || !isMountedRef.current) return;

    // Create a unique request key to prevent duplicate calls
    const requestKey = `${universeId}-${JSON.stringify(filters)}`;
    
    // Skip if we already have the same request pending
    if (lastRequestRef.current === requestKey) {
      console.log('🚫 useUniverseTimeline: Skipping duplicate request', { requestKey });
      return;
    }

    try {
      lastRequestRef.current = requestKey;
      setLoading(true);
      setError(null);
      
      console.log('🔄 useUniverseTimeline: Fetching timeline', { universeId, filters });
      
      const response = await temporalUniverseAPI.getTimeline(universeId, filters);
      
      if (response.success) {
        setTimeline(response.data);
        setMetadata(response.metadata);
        console.log('✅ useUniverseTimeline: Timeline loaded', {
          snapshotCount: response.data.length,
          dateRange: `${filters.date_range.start_date} to ${filters.date_range.end_date}`
        });
        
        // Clear request tracking after successful load (allow refresh after 5 seconds)
        setTimeout(() => {
          if (lastRequestRef.current === requestKey) {
            lastRequestRef.current = null;
          }
        }, 5000);
      } else {
        setError(response.message || 'Failed to fetch timeline');
        setTimeline([]);
        setMetadata(null);
        console.error('❌ useUniverseTimeline: API returned error', response.message);
        lastRequestRef.current = null; // Allow retry immediately on error
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Network error while fetching timeline';
      setError(errorMessage);
      setTimeline([]);
      setMetadata(null);
      console.error('❌ useUniverseTimeline: Exception occurred', err);
      lastRequestRef.current = null; // Allow retry immediately on error
    } finally {
      setLoading(false);
    }
  }, [universeId, JSON.stringify(filters)]); // Use JSON.stringify for stable filters comparison

  // Auto-fetch on universe change or filter change
  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return {
    timeline,
    loading,
    error,
    metadata,
    refetch: fetchTimeline
  };
}

/**
 * Hook for managing universe snapshots with pagination
 * Handles snapshot creation and list management
 */
export function useUniverseSnapshots(
  universeId: string,
  page?: number,
  perPage?: number
): UseUniverseSnapshotsReturn {
  const [snapshots, setSnapshots] = useState<UniverseSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<UniverseSnapshotsResponse['metadata'] | null>(null);
  const [creating, setCreating] = useState(false);

  const fetchSnapshots = useCallback(async () => {
    if (!universeId) return;

    try {
      setLoading(true);
      setError(null);
      
      console.log('🔄 useUniverseSnapshots: Fetching snapshots', { universeId, page, perPage });
      
      const response = await temporalUniverseAPI.getSnapshots(universeId, page, perPage);
      
      if (response.success) {
        setSnapshots(response.data);
        setMetadata(response.metadata);
        console.log('✅ useUniverseSnapshots: Snapshots loaded', {
          snapshotCount: response.data.length,
          totalSnapshots: response.metadata.total_snapshots
        });
      } else {
        setError(response.message || 'Failed to fetch snapshots');
        setSnapshots([]);
        setMetadata(null);
        console.error('❌ useUniverseSnapshots: API returned error', response.message);
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Network error while fetching snapshots';
      setError(errorMessage);
      setSnapshots([]);
      setMetadata(null);
      console.error('❌ useUniverseSnapshots: Exception occurred', err);
    } finally {
      setLoading(false);
    }
  }, [universeId, page, perPage]);

  const createSnapshot = useCallback(async (request: CreateSnapshotRequest = {}): Promise<UniverseSnapshot> => {
    if (!universeId) {
      throw new Error('Universe ID is required');
    }

    try {
      setCreating(true);
      setError(null);
      
      console.log('🔄 useUniverseSnapshots: Creating snapshot', { universeId, request });
      
      const response = await temporalUniverseAPI.createSnapshot(universeId, request);
      
      if (response.success) {
        const newSnapshot = response.data;
        
        // Add new snapshot to the list (at the beginning since it's most recent)
        setSnapshots(prev => [newSnapshot, ...prev]);
        
        // Update metadata if available
        if (metadata) {
          setMetadata({
            ...metadata,
            total_snapshots: metadata.total_snapshots + 1,
            date_range: {
              ...metadata.date_range,
              latest_snapshot: newSnapshot.snapshot_date
            }
          });
        }
        
        console.log('✅ useUniverseSnapshots: Snapshot created', {
          snapshotId: newSnapshot.id,
          snapshotDate: newSnapshot.snapshot_date,
          assetCount: newSnapshot.assets.length
        });
        
        return newSnapshot;
      } else {
        throw new Error(response.message || 'Failed to create snapshot');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Network error while creating snapshot';
      setError(errorMessage);
      console.error('❌ useUniverseSnapshots: Create snapshot failed', err);
      throw err;
    } finally {
      setCreating(false);
    }
  }, [universeId]); // Remove metadata from deps to prevent infinite re-creation

  // Auto-fetch on universe change
  useEffect(() => {
    fetchSnapshots();
  }, [fetchSnapshots]);

  return {
    snapshots,
    loading: loading || creating,
    error,
    metadata,
    refetch: fetchSnapshots,
    createSnapshot
  };
}

/**
 * Hook for turnover analysis and pattern detection
 * Calculates turnover trends, volatility, and asset stability patterns
 */
export function useTurnoverAnalysis(
  snapshots: UniverseSnapshot[],
  autoCalculate: boolean = true
): UseTurnoverAnalysisReturn {
  const [analysis, setAnalysis] = useState<TurnoverAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateAnalysis = useCallback((snapshotsToAnalyze: UniverseSnapshot[] = snapshots) => {
    if (!snapshotsToAnalyze || snapshotsToAnalyze.length < 2) {
      setAnalysis(null);
      setError('At least 2 snapshots are required for turnover analysis');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      console.log('🔄 useTurnoverAnalysis: Calculating turnover analysis', {
        snapshotCount: snapshotsToAnalyze.length
      });
      
      // Sort snapshots by date
      const sortedSnapshots = [...snapshotsToAnalyze].sort((a, b) => 
        new Date(a.snapshot_date).getTime() - new Date(b.snapshot_date).getTime()
      );
      
      // Extract turnover rates and calculate statistics
      const turnoverRates = sortedSnapshots
        .filter(s => s.turnover_rate !== null && s.turnover_rate !== undefined)
        .map(s => s.turnover_rate as number);
      
      if (turnoverRates.length === 0) {
        setAnalysis(null);
        setError('No turnover rate data available in snapshots');
        return;
      }
      
      const averageTurnover = turnoverRates.reduce((sum, rate) => sum + rate, 0) / turnoverRates.length;
      
      // Calculate turnover volatility (standard deviation)
      const variance = turnoverRates.reduce((sum, rate) => sum + Math.pow(rate - averageTurnover, 2), 0) / turnoverRates.length;
      const volatility = Math.sqrt(variance);
      
      // Determine trend (simple linear regression slope)
      const n = turnoverRates.length;
      const x = Array.from({ length: n }, (_, i) => i);
      const y = turnoverRates;
      const sumX = x.reduce((a, b) => a + b, 0);
      const sumY = y.reduce((a, b) => a + b, 0);
      const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
      const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);
      
      const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
      const trend: 'increasing' | 'decreasing' | 'stable' = 
        slope > 0.01 ? 'increasing' : slope < -0.01 ? 'decreasing' : 'stable';
      
      // Build periods array
      const periods = sortedSnapshots.map(snapshot => ({
        date: snapshot.snapshot_date,
        turnover_rate: snapshot.turnover_rate || 0,
        assets_added: snapshot.assets_added?.length || 0,
        assets_removed: snapshot.assets_removed?.length || 0,
        total_assets: snapshot.assets.length
      }));
      
      // Asset stability analysis
      const allAssets = new Set<string>();
      const assetOccurrences = new Map<string, number>();
      
      sortedSnapshots.forEach(snapshot => {
        snapshot.assets.forEach(asset => {
          allAssets.add(asset.symbol);
          assetOccurrences.set(asset.symbol, (assetOccurrences.get(asset.symbol) || 0) + 1);
        });
      });
      
      const totalSnapshots = sortedSnapshots.length;
      const stabilityThreshold = Math.ceil(totalSnapshots * 0.8); // Present in >80% of snapshots
      
      const assetStabilityEntries = Array.from(assetOccurrences.entries());
      assetStabilityEntries.sort((a, b) => b[1] - a[1]);
      
      const mostStableAssets = assetStabilityEntries
        .slice(0, 10)
        .map(([symbol]) => symbol);
        
      const mostVolatileAssets = assetStabilityEntries
        .slice(-10)
        .map(([symbol]) => symbol)
        .reverse();
        
      const coreHoldings = assetStabilityEntries
        .filter(([, count]) => count >= stabilityThreshold)
        .map(([symbol]) => symbol);
      
      const analysisResult: TurnoverAnalysis = {
        period_start: sortedSnapshots[0].snapshot_date,
        period_end: sortedSnapshots[sortedSnapshots.length - 1].snapshot_date,
        average_turnover_rate: averageTurnover,
        turnover_trend: trend,
        turnover_volatility: volatility,
        periods,
        asset_stability: {
          most_stable_assets: mostStableAssets,
          most_volatile_assets: mostVolatileAssets,
          core_holdings: coreHoldings
        }
      };
      
      setAnalysis(analysisResult);
      
      console.log('✅ useTurnoverAnalysis: Analysis completed', {
        averageTurnover: averageTurnover.toFixed(4),
        trend,
        volatility: volatility.toFixed(4),
        coreHoldingsCount: coreHoldings.length,
        periodsAnalyzed: periods.length
      });
      
    } catch (err: any) {
      const errorMessage = err.message || 'Error calculating turnover analysis';
      setError(errorMessage);
      setAnalysis(null);
      console.error('❌ useTurnoverAnalysis: Calculation failed', err);
    } finally {
      setLoading(false);
    }
  }, [snapshots]);

  // Auto-calculate when snapshots change (if enabled)
  useEffect(() => {
    if (autoCalculate && snapshots.length > 1) {
      calculateAnalysis(snapshots);
    }
  }, [snapshots, autoCalculate]); // Remove calculateAnalysis from deps to prevent circular dependency

  return {
    analysis,
    loading,
    error,
    calculateAnalysis
  };
}

/**
 * Hook for fetching composition at a specific date
 * Useful for point-in-time analysis and historical reconstruction
 */
export function useCompositionAtDate(universeId: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<CompositionAtDateResponse | null>(null);

  const getComposition = useCallback(async (date: string): Promise<AssetComposition[]> => {
    if (!universeId) {
      throw new Error('Universe ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      
      console.log('🔄 useCompositionAtDate: Fetching composition', { universeId, date });
      
      const response = await temporalUniverseAPI.getCompositionAtDate(universeId, date);
      setLastResponse(response);
      
      if (response.success) {
        console.log('✅ useCompositionAtDate: Composition retrieved', {
          queryDate: date,
          snapshotDate: response.data.snapshot_date,
          assetCount: response.data.assets.length,
          isExactMatch: response.data.context.is_exact_match
        });
        
        return response.data.assets;
      } else {
        throw new Error(response.message || 'Failed to fetch composition');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Network error while fetching composition';
      setError(errorMessage);
      console.error('❌ useCompositionAtDate: Fetch failed', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [universeId]);

  return {
    getComposition,
    loading,
    error,
    lastResponse
  };
}

/**
 * Hook for managing backfill operations
 * Handles historical snapshot generation with progress tracking
 */
export function useBackfillHistory(universeId: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<BackfillHistoryRequest | null>(null);

  const startBackfill = useCallback(async (request: BackfillHistoryRequest) => {
    if (!universeId) {
      throw new Error('Universe ID is required');
    }

    try {
      setLoading(true);
      setError(null);
      
      console.log('🔄 useBackfillHistory: Starting backfill', { universeId, request });
      
      const response = await temporalUniverseAPI.backfillHistory(universeId, request);
      
      if (response.success) {
        setLastResult(request);
        
        console.log('✅ useBackfillHistory: Backfill completed', {
          snapshotsCreated: response.data.snapshots_created,
          snapshotsUpdated: response.data.snapshots_updated,
          snapshotsSkipped: response.data.snapshots_skipped,
          processingTime: response.metadata.processing_time_seconds
        });
        
        return response;
      } else {
        throw new Error(response.message || 'Backfill operation failed');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Network error during backfill';
      setError(errorMessage);
      console.error('❌ useBackfillHistory: Backfill failed', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [universeId]);

  return {
    startBackfill,
    loading,
    error,
    lastResult
  };
}

/**
 * Utility hook for common date range presets
 * Provides standard date ranges used in temporal analysis
 */
export function useDateRangePresets(): Record<string, DateRange> {
  return useMemo(() => {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    
    const getDateDaysAgo = (days: number): string => {
      const date = new Date(now);
      date.setDate(date.getDate() - days);
      return date.toISOString().split('T')[0];
    };
    
    const getDateMonthsAgo = (months: number): string => {
      const date = new Date(now);
      date.setMonth(date.getMonth() - months);
      return date.toISOString().split('T')[0];
    };
    
    const getDateYearsAgo = (years: number): string => {
      const date = new Date(now);
      date.setFullYear(date.getFullYear() - years);
      return date.toISOString().split('T')[0];
    };

    return {
      last30Days: {
        start_date: getDateDaysAgo(30),
        end_date: today
      },
      last3Months: {
        start_date: getDateMonthsAgo(3),
        end_date: today
      },
      last6Months: {
        start_date: getDateMonthsAgo(6),
        end_date: today
      },
      lastYear: {
        start_date: getDateYearsAgo(1),
        end_date: today
      },
      last2Years: {
        start_date: getDateYearsAgo(2),
        end_date: today
      },
      last5Years: {
        start_date: getDateYearsAgo(5),
        end_date: today
      },
      ytd: {
        start_date: `${now.getFullYear()}-01-01`,
        end_date: today
      }
    };
  }, []);
}