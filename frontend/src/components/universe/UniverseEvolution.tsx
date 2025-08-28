import React, { useState, useMemo, useCallback, useRef } from 'react';
import { 
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ScriptableContext,
  ChartOptions,
  InteractionItem,
  TooltipItem
} from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import { Line } from 'react-chartjs-2';
import { format, parseISO } from 'date-fns';
import { 
  TrendingUpIcon, 
  BarChart3Icon, 
  PieChartIcon, 
  ActivityIcon,
  DownloadIcon,
  RefreshCwIcon,
  InfoIcon,
  ChevronDownIcon,
  ZoomInIcon,
  ZoomOutIcon,
  RotateCcwIcon
} from 'lucide-react';
import { UniverseSnapshot, TurnoverAnalysis, DateRange } from '../../types/temporal';
import { useUniverseTimeline, useTurnoverAnalysis } from '../../hooks/useTemporalUniverse';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  zoomPlugin
);

interface UniverseEvolutionProps {
  universeId: string;
  dateRange?: DateRange;
  viewMode: 'asset_count' | 'turnover' | 'composition';
  onViewModeChange: (mode: string) => void;
  height?: number;
  snapshots?: UniverseSnapshot[];
  loading?: boolean;
  error?: string | null;
  className?: string;
}

type ViewMode = 'asset_count' | 'turnover' | 'composition';

// Professional fintech color palette
const FINTECH_COLORS = {
  primary: {
    blue: '#1E40AF',      // Professional blue
    lightBlue: '#3B82F6',  // Lighter blue
    navy: '#1E3A8A'        // Navy blue
  },
  performance: {
    green: '#059669',      // Positive performance
    red: '#DC2626',        // Negative performance
    amber: '#D97706'       // Warning/neutral
  },
  sectors: [
    '#1E40AF', '#059669', '#D97706', '#DC2626', '#7C3AED',
    '#0891B2', '#BE185D', '#0D9488', '#EA580C', '#6366F1'
  ],
  neutral: {
    gray: '#6B7280',
    lightGray: '#9CA3AF',
    darkGray: '#374151'
  }
};

interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    borderColor: string;
    backgroundColor: string | ((context: ScriptableContext<'line'>) => string | CanvasGradient);
    fill?: boolean;
    tension?: number;
    pointRadius?: number;
    pointHoverRadius?: number;
  }>;
}

const UniverseEvolution: React.FC<UniverseEvolutionProps> = ({
  universeId,
  dateRange,
  viewMode: externalViewMode,
  onViewModeChange,
  height = 400,
  snapshots: externalSnapshots,
  loading: externalLoading = false,
  error: externalError = null,
  className = ''
}) => {
  const [internalViewMode, setInternalViewMode] = useState<ViewMode>('asset_count');
  const [showDataPoints, setShowDataPoints] = useState(true);
  const [zoomEnabled, setZoomEnabled] = useState(false);
  const chartRef = useRef<ChartJS<'line'>>(null);
  
  // Use external viewMode if provided, otherwise internal state
  const viewMode = externalViewMode || internalViewMode;
  const handleViewModeChange = (mode: ViewMode) => {
    if (onViewModeChange) {
      onViewModeChange(mode);
    } else {
      setInternalViewMode(mode);
    }
  };

  // Use internal hook if external snapshots not provided
  const timelineResult = useUniverseTimeline(universeId, externalSnapshots ? undefined : {
    date_range: dateRange || {
      start_date: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0]
    },
    frequency: 'monthly',
    show_empty_periods: false,
    include_turnover_analysis: true
  });

  const internalTimeline = timelineResult?.timeline || [];
  const internalLoading = timelineResult?.loading || false;
  const internalError = timelineResult?.error || null;
  const metadata = timelineResult?.metadata || null;
  const refetch = timelineResult?.refetch || (() => Promise.resolve());

  // Use external data if provided, otherwise use internal hook data
  const snapshots = externalSnapshots || internalTimeline;
  const loading = externalLoading || internalLoading;
  const error = externalError || internalError;

  // Get turnover analysis
  const turnoverAnalysisResult = useTurnoverAnalysis(snapshots, true);
  const turnoverAnalysis = turnoverAnalysisResult?.analysis || null;

  // Sector composition analysis
  const sectorComposition = useMemo(() => {
    if (!snapshots || snapshots.length === 0) return {};
    
    const sectorsByDate: Record<string, Record<string, number>> = {};
    
    snapshots.forEach(snapshot => {
      const sectors: Record<string, number> = {};
      snapshot.assets.forEach(asset => {
        if (asset.sector) {
          sectors[asset.sector] = (sectors[asset.sector] || 0) + (asset.weight || 1);
        }
      });
      sectorsByDate[snapshot.snapshot_date] = sectors;
    });
    
    return sectorsByDate;
  }, [snapshots]);

  // Chart zoom and pan handlers
  const handleZoomReset = useCallback(() => {
    if (chartRef.current) {
      chartRef.current.resetZoom();
    }
  }, []);

  const handleZoomIn = useCallback(() => {
    if (chartRef.current) {
      chartRef.current.zoom(1.1);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (chartRef.current) {
      chartRef.current.zoom(0.9);
    }
  }, []);

  // Enhanced export functionality
  const handleExport = useCallback(async (format: 'png' | 'svg' = 'png') => {
    if (!chartRef.current) return;

    try {
      const canvas = chartRef.current.canvas;
      if (!canvas) return;

      if (format === 'png') {
        // Export as PNG
        const url = canvas.toDataURL('image/png', 1.0);
        const link = document.createElement('a');
        link.download = `universe-evolution-${viewMode}-${new Date().toISOString().split('T')[0]}.png`;
        link.href = url;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        // For SVG export, we'd need additional library like chart.js-to-svg
        // For now, fallback to PNG
        console.warn('SVG export not implemented, using PNG instead');
        handleExport('png');
      }
    } catch (error) {
      console.error('Failed to export chart:', error);
    }
  }, [viewMode]);

  // Chart data based on view mode
  const chartData: ChartData = useMemo(() => {
    if (!snapshots || snapshots.length === 0) {
      return { labels: [], datasets: [] };
    }

    const sortedSnapshots = [...snapshots].sort((a, b) => 
      new Date(a.snapshot_date).getTime() - new Date(b.snapshot_date).getTime()
    );

    const labels = sortedSnapshots.map(snapshot => 
      format(parseISO(snapshot.snapshot_date), 'MMM yyyy')
    );

    switch (viewMode) {
      case 'asset_count': {
        const data = sortedSnapshots.map(snapshot => snapshot.assets.length);
        return {
          labels,
          datasets: [
            {
              label: 'Asset Count',
              data,
              borderColor: FINTECH_COLORS.primary.blue,
              backgroundColor: (context: ScriptableContext<'line'>) => {
                const ctx = context.chart.ctx;
                const gradient = ctx.createLinearGradient(0, 0, 0, height * 0.8);
                gradient.addColorStop(0, `${FINTECH_COLORS.primary.blue}33`);
                gradient.addColorStop(1, `${FINTECH_COLORS.primary.blue}0D`);
                return gradient as any; // Chart.js supports CanvasGradient at runtime
              },
              fill: true,
              tension: 0.4,
              pointRadius: showDataPoints ? 4 : 0,
              pointHoverRadius: 6
            }
          ]
        };
      }

      case 'turnover': {
        const data = sortedSnapshots.map(snapshot => 
          snapshot.turnover_rate ? snapshot.turnover_rate * 100 : 0
        );
        return {
          labels,
          datasets: [
            {
              label: 'Turnover Rate (%)',
              data,
              borderColor: FINTECH_COLORS.performance.red,
              backgroundColor: (context: ScriptableContext<'line'>) => {
                const ctx = context.chart.ctx;
                const gradient = ctx.createLinearGradient(0, 0, 0, height * 0.8);
                gradient.addColorStop(0, `${FINTECH_COLORS.performance.red}33`);
                gradient.addColorStop(1, `${FINTECH_COLORS.performance.red}0D`);
                return gradient as any; // Chart.js supports CanvasGradient at runtime
              },
              fill: true,
              tension: 0.4,
              pointRadius: showDataPoints ? 4 : 0,
              pointHoverRadius: 6
            }
          ]
        };
      }

      case 'composition': {
        // Show top 5 sectors as stacked area chart
        const allSectors = new Set<string>();
        Object.values(sectorComposition).forEach(sectors => {
          Object.keys(sectors).forEach(sector => allSectors.add(sector));
        });

        const sectorCounts = Array.from(allSectors).map(sector => ({
          sector,
          totalCount: Object.values(sectorComposition).reduce((sum, sectors) => 
            sum + (sectors[sector] || 0), 0
          )
        }));

        const topSectors = sectorCounts
          .sort((a, b) => b.totalCount - a.totalCount)
          .slice(0, 5)
          .map(s => s.sector);

        const colors = FINTECH_COLORS.sectors.slice(0, 5);

        const datasets = topSectors.map((sector, index) => ({
          label: sector,
          data: sortedSnapshots.map(snapshot => {
            const sectorData = sectorComposition[snapshot.snapshot_date] || {};
            return sectorData[sector] || 0;
          }),
          borderColor: colors[index],
          backgroundColor: `${colors[index]}33`,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 4
        }));

        return { labels, datasets };
      }

      default:
        return { labels: [], datasets: [] };
    }
  }, [snapshots, viewMode, showDataPoints, sectorComposition, height]);

  // Chart options with zoom and professional styling
  const chartOptions: ChartOptions<'line'> = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 12
          },
          color: FINTECH_COLORS.neutral.darkGray
        }
      },
      title: {
        display: true,
        text: getViewModeTitle(viewMode),
        font: {
          size: 16,
          weight: 'bold' as const,
          family: 'Inter, system-ui, sans-serif'
        },
        color: FINTECH_COLORS.neutral.darkGray,
        padding: {
          bottom: 20
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: true,
        titleFont: {
          family: 'Inter, system-ui, sans-serif',
          size: 13,
          weight: 600
        },
        bodyFont: {
          family: 'Inter, system-ui, sans-serif',
          size: 12
        },
        callbacks: {
          title: (context: any) => {
            const index = context[0].dataIndex;
            const snapshot = snapshots?.[index];
            return snapshot ? format(parseISO(snapshot.snapshot_date), 'MMM dd, yyyy') : '';
          },
          afterBody: (context: any) => {
            const index = context[0].dataIndex;
            const snapshot = snapshots?.[index];
            if (!snapshot) return [];
            
            const lines = [];
            if (snapshot.assets_added && snapshot.assets_added.length > 0) {
              lines.push(`Added: ${snapshot.assets_added.join(', ')}`);
            }
            if (snapshot.assets_removed && snapshot.assets_removed.length > 0) {
              lines.push(`Removed: ${snapshot.assets_removed.join(', ')}`);
            }
            
            return lines;
          }
        }
      },
      zoom: {
        zoom: {
          wheel: {
            enabled: zoomEnabled
          },
          pinch: {
            enabled: zoomEnabled
          },
          mode: 'x' as const
        },
        pan: {
          enabled: zoomEnabled,
          mode: 'x' as const
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time Period',
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 12,
            weight: 500
          },
          color: FINTECH_COLORS.neutral.darkGray
        },
        grid: {
          display: false
        },
        ticks: {
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 11
          },
          color: FINTECH_COLORS.neutral.gray
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: getYAxisLabel(viewMode),
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 12,
            weight: 500
          },
          color: FINTECH_COLORS.neutral.darkGray
        },
        beginAtZero: true,
        grid: {
          color: 'rgba(107, 114, 128, 0.1)',
          lineWidth: 1
        },
        ticks: {
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 11
          },
          color: FINTECH_COLORS.neutral.gray,
          callback: function(value: any) {
            if (viewMode === 'turnover') {
              return `${value}%`;
            }
            return value;
          }
        }
      }
    }
  }), [viewMode, snapshots, zoomEnabled]);

  function getViewModeTitle(mode: ViewMode): string {
    switch (mode) {
      case 'asset_count': return 'Universe Size Evolution';
      case 'turnover': return 'Portfolio Turnover Analysis';  
      case 'composition': return 'Sector Composition Changes';
      default: return 'Universe Evolution';
    }
  }

  function getYAxisLabel(mode: ViewMode): string {
    switch (mode) {
      case 'asset_count': return 'Number of Assets';
      case 'turnover': return 'Turnover Rate (%)';
      case 'composition': return 'Asset Count by Sector';
      default: return 'Value';
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow ${className}`}>
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="h-6 bg-gray-200 rounded w-48 animate-pulse"></div>
            <div className="h-8 bg-gray-200 rounded w-32 animate-pulse"></div>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-center" style={{ height }}>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading evolution chart...</span>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`bg-white rounded-lg shadow ${className}`}>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <InfoIcon className="h-5 w-5 text-red-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Chart Error</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
              <button
                onClick={() => refetch?.()}
                className="ml-auto bg-red-100 px-3 py-1 text-sm font-medium rounded-md text-red-800 hover:bg-red-200"
              >
                <RefreshCwIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      {/* Header with view mode controls */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Universe Evolution</h3>
            <p className="mt-1 text-sm text-gray-500">
              Professional temporal analytics visualization for institutional-grade analysis
              {metadata && (
                <span className="ml-2">
                  • {metadata.total_snapshots} snapshots
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {/* View mode selector */}
            <div className="relative">
              <select
                value={viewMode}
                onChange={(e) => handleViewModeChange(e.target.value as ViewMode)}
                className="appearance-none bg-white border border-gray-300 rounded-md px-4 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="asset_count">Asset Count</option>
                <option value="turnover">Turnover Rate</option>
                <option value="composition">Sector Composition</option>
              </select>
              <ChevronDownIcon className="absolute right-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>

            {/* Chart controls */}
            <div className="flex items-center space-x-1 border-l border-gray-200 pl-2">
              <button
                onClick={() => setShowDataPoints(!showDataPoints)}
                className={`p-2 rounded-md text-sm ${
                  showDataPoints 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
                title="Toggle data points"
              >
                <BarChart3Icon className="w-4 h-4" />
              </button>
              
              <button
                onClick={() => setZoomEnabled(!zoomEnabled)}
                className={`p-2 rounded-md text-sm ${
                  zoomEnabled 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
                title="Toggle zoom mode"
              >
                <ZoomInIcon className="w-4 h-4" />
              </button>
              
              {zoomEnabled && (
                <>
                  <button
                    onClick={handleZoomIn}
                    className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
                    title="Zoom in"
                  >
                    <ZoomInIcon className="w-3 h-3" />
                  </button>
                  
                  <button
                    onClick={handleZoomOut}
                    className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
                    title="Zoom out"
                  >
                    <ZoomOutIcon className="w-3 h-3" />
                  </button>
                  
                  <button
                    onClick={handleZoomReset}
                    className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
                    title="Reset zoom"
                  >
                    <RotateCcwIcon className="w-3 h-3" />
                  </button>
                </>
              )}
              
              <button
                onClick={() => handleExport('png')}
                className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
                title="Export chart as PNG"
              >
                <DownloadIcon className="w-4 h-4" />
              </button>
              
              <button
                onClick={() => refetch?.()}
                className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
                title="Refresh data"
              >
                <RefreshCwIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Chart container */}
      <div className="p-6">
        {chartData.datasets.length > 0 ? (
          <div style={{ height }}>
            <Line 
              ref={chartRef as any}
              data={chartData} 
              options={chartOptions} 
            />
          </div>
        ) : (
          <div className="flex items-center justify-center text-gray-500" style={{ height }}>
            <div className="text-center">
              <ActivityIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No Chart Data</h3>
              <p className="mt-1 text-sm text-gray-500">
                No historical data available for the selected view mode.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Summary footer */}
      {turnoverAnalysis && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Period:</span>
              <span className="ml-1 font-medium">
                {format(parseISO(turnoverAnalysis.period_start), 'MMM yyyy')} - 
                {format(parseISO(turnoverAnalysis.period_end), 'MMM yyyy')}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Avg Turnover:</span>
              <span className="ml-1 font-medium">
                {(turnoverAnalysis.average_turnover_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-gray-600">Trend:</span>
              <span className={`ml-1 font-medium capitalize ${
                turnoverAnalysis.turnover_trend === 'increasing' ? 'text-red-600' :
                turnoverAnalysis.turnover_trend === 'decreasing' ? 'text-green-600' :
                'text-gray-600'
              }`}>
                {turnoverAnalysis.turnover_trend}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Core Holdings:</span>
              <span className="ml-1 font-medium">
                {turnoverAnalysis.asset_stability.core_holdings.length}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UniverseEvolution;