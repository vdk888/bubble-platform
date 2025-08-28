import React, { useState, useMemo, useCallback } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';
import { format, parseISO } from 'date-fns';
import { 
  TrendingUpIcon, 
  TrendingDownIcon,
  MinusIcon,
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  InfoIcon,
  BarChart3Icon,
  PieChartIcon,
  RefreshCwIcon,
  DownloadIcon
} from 'lucide-react';
import { UniverseSnapshot, TurnoverAnalysis } from '../../types/temporal';
import { useUniverseTimeline, useTurnoverAnalysis } from '../../hooks/useTemporalUniverse';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface TurnoverAnalysisProps {
  universe_id: string;
  snapshots?: UniverseSnapshot[];
  loading?: boolean;
  error?: string | null;
  className?: string;
}

type AnalysisView = 'overview' | 'distribution' | 'assets' | 'trends';

interface MetricCard {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  color: 'blue' | 'green' | 'red' | 'yellow' | 'gray';
  icon: React.ElementType;
}

const TurnoverAnalysisComponent: React.FC<TurnoverAnalysisProps> = ({
  universe_id,
  snapshots: externalSnapshots,
  loading: externalLoading = false,
  error: externalError = null,
  className = ''
}) => {
  const [analysisView, setAnalysisView] = useState<AnalysisView>('overview');

  // Use internal hook if external snapshots not provided
  const { timeline: internalTimeline, loading: internalLoading, error: internalError, refetch } = 
    useUniverseTimeline(universe_id, externalSnapshots ? undefined : {
      date_range: {
        start_date: new Date(Date.now() - 365 * 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 2 years
        end_date: new Date().toISOString().split('T')[0]
      },
      frequency: 'monthly',
      show_empty_periods: false,
      include_turnover_analysis: true
    });

  // Use external data if provided, otherwise use internal hook data
  const snapshots = externalSnapshots || internalTimeline;
  const loading = externalLoading || internalLoading;
  const error = externalError || internalError;

  // Get turnover analysis
  const { analysis, loading: analysisLoading, error: analysisError } = 
    useTurnoverAnalysis(snapshots, true);

  // Calculate key metrics
  const keyMetrics = useMemo((): MetricCard[] => {
    if (!analysis) return [];

    const avgTurnover = analysis.average_turnover_rate * 100;
    const volatility = analysis.turnover_volatility * 100;
    const stabilityScore = analysis.asset_stability.core_holdings.length / 
                          (analysis.asset_stability.most_stable_assets.length || 1) * 100;

    return [
      {
        title: 'Average Turnover',
        value: `${avgTurnover.toFixed(1)}%`,
        subtitle: `${analysis.periods.length} periods`,
        trend: analysis.turnover_trend === 'increasing' ? 'up' : 
               analysis.turnover_trend === 'decreasing' ? 'down' : 'stable',
        color: avgTurnover > 25 ? 'red' : avgTurnover > 15 ? 'yellow' : 'green',
        icon: avgTurnover > 25 ? TrendingUpIcon : avgTurnover < 5 ? TrendingDownIcon : MinusIcon
      },
      {
        title: 'Turnover Trend',
        value: analysis.turnover_trend,
        subtitle: `${format(parseISO(analysis.period_start), 'MMM yyyy')} - ${format(parseISO(analysis.period_end), 'MMM yyyy')}`,
        trend: analysis.turnover_trend === 'increasing' ? 'up' : 
               analysis.turnover_trend === 'decreasing' ? 'down' : 'stable',
        color: analysis.turnover_trend === 'increasing' ? 'red' : 
               analysis.turnover_trend === 'decreasing' ? 'green' : 'blue',
        icon: analysis.turnover_trend === 'increasing' ? TrendingUpIcon : 
              analysis.turnover_trend === 'decreasing' ? TrendingDownIcon : ActivityIcon
      },
      {
        title: 'Stability Score',
        value: `${stabilityScore.toFixed(0)}%`,
        subtitle: `${analysis.asset_stability.core_holdings.length} core holdings`,
        trend: stabilityScore > 70 ? 'up' : stabilityScore < 40 ? 'down' : 'stable',
        color: stabilityScore > 70 ? 'green' : stabilityScore < 40 ? 'red' : 'yellow',
        icon: stabilityScore > 70 ? CheckCircleIcon : stabilityScore < 40 ? AlertTriangleIcon : InfoIcon
      },
      {
        title: 'Volatility',
        value: `${volatility.toFixed(1)}%`,
        subtitle: 'Turnover variation',
        trend: volatility > 15 ? 'up' : volatility < 5 ? 'down' : 'stable',
        color: volatility > 15 ? 'red' : volatility < 5 ? 'green' : 'yellow',
        icon: volatility > 15 ? AlertTriangleIcon : CheckCircleIcon
      }
    ];
  }, [analysis]);

  // Turnover distribution data
  const distributionData = useMemo(() => {
    if (!analysis) return { labels: [], datasets: [] };

    // Create histogram bins
    const turnoverRates = analysis.periods.map(p => p.turnover_rate * 100);
    const bins = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 100];
    const binLabels = bins.slice(0, -1).map((bin, i) => 
      i === bins.length - 2 ? `${bin}%+` : `${bin}-${bins[i + 1]}%`
    );
    
    const binCounts = new Array(bins.length - 1).fill(0);
    turnoverRates.forEach(rate => {
      for (let i = 0; i < bins.length - 1; i++) {
        if (rate >= bins[i] && rate < bins[i + 1]) {
          binCounts[i]++;
          break;
        }
      }
    });

    return {
      labels: binLabels,
      datasets: [
        {
          label: 'Frequency',
          data: binCounts,
          backgroundColor: 'rgba(59, 130, 246, 0.6)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 1
        }
      ]
    };
  }, [analysis]);

  // Trend chart data
  const trendData = useMemo(() => {
    if (!analysis) return { labels: [], datasets: [] };

    const labels = analysis.periods.map(p => format(parseISO(p.date), 'MMM yyyy'));
    const turnoverData = analysis.periods.map(p => p.turnover_rate * 100);
    const assetCounts = analysis.periods.map(p => p.total_assets);

    return {
      labels,
      datasets: [
        {
          label: 'Turnover Rate (%)',
          data: turnoverData,
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          yAxisID: 'y',
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6
        },
        {
          label: 'Asset Count',
          data: assetCounts,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y1',
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6
        }
      ]
    };
  }, [analysis]);

  // Asset stability breakdown
  const assetStabilityData = useMemo(() => {
    if (!analysis) return { labels: [], datasets: [] };

    const coreCount = analysis.asset_stability.core_holdings.length;
    const stableCount = Math.max(0, analysis.asset_stability.most_stable_assets.length - coreCount);
    const volatileCount = analysis.asset_stability.most_volatile_assets.length;

    return {
      labels: ['Core Holdings (>80%)', 'Stable Assets', 'Volatile Assets'],
      datasets: [
        {
          data: [coreCount, stableCount, volatileCount],
          backgroundColor: [
            'rgba(16, 185, 129, 0.8)',   // Green for core
            'rgba(59, 130, 246, 0.8)',   // Blue for stable
            'rgba(239, 68, 68, 0.8)'     // Red for volatile
          ],
          borderColor: [
            'rgb(16, 185, 129)',
            'rgb(59, 130, 246)',
            'rgb(239, 68, 68)'
          ],
          borderWidth: 2
        }
      ]
    };
  }, [analysis]);

  const getMetricCardStyle = (color: MetricCard['color']) => {
    const styles = {
      blue: 'bg-blue-50 border-blue-200',
      green: 'bg-green-50 border-green-200',
      red: 'bg-red-50 border-red-200',
      yellow: 'bg-yellow-50 border-yellow-200',
      gray: 'bg-gray-50 border-gray-200'
    };
    return styles[color];
  };

  const getMetricValueStyle = (color: MetricCard['color']) => {
    const styles = {
      blue: 'text-blue-900',
      green: 'text-green-900',
      red: 'text-red-900',
      yellow: 'text-yellow-900',
      gray: 'text-gray-900'
    };
    return styles[color];
  };

  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon className="w-4 h-4 text-red-500" />;
      case 'down':
        return <TrendingDownIcon className="w-4 h-4 text-green-500" />;
      default:
        return <MinusIcon className="w-4 h-4 text-gray-500" />;
    }
  };

  // Export functionality
  const exportAnalysisToCSV = useCallback(() => {
    if (!analysis) return;

    const csvData = [
      // Header
      ['Turnover Analysis Report'],
      ['Generated on', new Date().toISOString()],
      ['Universe ID', universe_id],
      ['Analysis Period', `${analysis.period_start} to ${analysis.period_end}`],
      [''],
      
      // Key Metrics
      ['Key Metrics'],
      ['Average Turnover Rate', `${(analysis.average_turnover_rate * 100).toFixed(2)}%`],
      ['Turnover Trend', analysis.turnover_trend],
      ['Turnover Volatility', `${(analysis.turnover_volatility * 100).toFixed(2)}%`],
      ['Core Holdings Count', analysis.asset_stability.core_holdings.length],
      [''],
      
      // Periods Data
      ['Period Analysis'],
      ['Date', 'Turnover Rate (%)', 'Assets Added', 'Assets Removed', 'Total Assets'],
      ...analysis.periods.map(period => [
        period.date,
        `${(period.turnover_rate * 100).toFixed(2)}%`,
        period.assets_added,
        period.assets_removed,
        period.total_assets
      ]),
      [''],
      
      // Asset Stability
      ['Core Holdings (>80% presence)'],
      ...analysis.asset_stability.core_holdings.map(asset => [asset]),
      [''],
      
      ['Most Stable Assets'],
      ...analysis.asset_stability.most_stable_assets.slice(0, 10).map(asset => [asset]),
      [''],
      
      ['Most Volatile Assets'],
      ...analysis.asset_stability.most_volatile_assets.slice(0, 10).map(asset => [asset]),
    ];

    const csvContent = csvData.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `turnover-analysis-${universe_id}-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [analysis, universe_id]);

  // Loading state
  if (loading || analysisLoading) {
    return (
      <div className={`bg-white rounded-lg shadow ${className}`}>
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Analyzing turnover patterns...</span>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || analysisError) {
    return (
      <div className={`bg-white rounded-lg shadow ${className}`}>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <AlertTriangleIcon className="h-5 w-5 text-red-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Analysis Error</h3>
                <p className="mt-1 text-sm text-red-700">{error || analysisError}</p>
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

  // No data state
  if (!analysis) {
    return (
      <div className={`bg-white rounded-lg shadow ${className}`}>
        <div className="p-6">
          <div className="text-center py-12">
            <ActivityIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No Analysis Data</h3>
            <p className="mt-1 text-sm text-gray-500">
              At least 2 snapshots are required for turnover analysis.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      {/* Header with view controls */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Turnover Analysis</h3>
            <p className="mt-1 text-sm text-gray-500">
              Portfolio turnover patterns and asset stability insights
            </p>
          </div>
          
          {/* View selector */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center border border-gray-300 rounded-md">
              {([
                { key: 'overview', label: 'Overview', icon: BarChart3Icon },
                { key: 'distribution', label: 'Distribution', icon: BarChart3Icon },
                { key: 'assets', label: 'Assets', icon: PieChartIcon },
                { key: 'trends', label: 'Trends', icon: ActivityIcon }
              ] as const).map((view) => (
                <button
                  key={view.key}
                  onClick={() => setAnalysisView(view.key)}
                  className={`inline-flex items-center px-3 py-2 text-sm font-medium ${
                    analysisView === view.key
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  } ${view.key === 'overview' ? 'rounded-l-md' : view.key === 'trends' ? 'rounded-r-md' : ''}`}
                >
                  <view.icon className="w-4 h-4 mr-1" />
                  {view.label}
                </button>
              ))}
            </div>
            
            <button
              onClick={exportAnalysisToCSV}
              disabled={!analysis}
              className="p-2 border border-gray-300 rounded-md text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Export analysis to CSV"
            >
              <DownloadIcon className="w-4 h-4" />
            </button>
            
            <button
              onClick={() => refetch?.()}
              className="p-2 border border-gray-300 rounded-md text-gray-600 hover:bg-gray-100"
              title="Refresh analysis"
            >
              <RefreshCwIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content based on selected view */}
      <div className="p-6">
        {analysisView === 'overview' && (
          <div className="space-y-6">
            {/* Key metrics cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {keyMetrics.map((metric, index) => {
                const Icon = metric.icon;
                return (
                  <div
                    key={index}
                    className={`border rounded-lg p-4 ${getMetricCardStyle(metric.color)}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <Icon className={`w-5 h-5 mr-2 ${getMetricValueStyle(metric.color)}`} />
                        <span className="text-sm font-medium text-gray-700">
                          {metric.title}
                        </span>
                      </div>
                      {getTrendIcon(metric.trend || 'stable')}
                    </div>
                    <div className="mt-2">
                      <div className={`text-2xl font-bold ${getMetricValueStyle(metric.color)}`}>
                        {typeof metric.value === 'string' 
                          ? metric.value 
                          : metric.value.toLocaleString()}
                      </div>
                      {metric.subtitle && (
                        <div className="text-xs text-gray-500 mt-1">
                          {metric.subtitle}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Risk indicators */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <h4 className="text-sm font-medium text-gray-900 mb-3">Turnover Risk Assessment</h4>
                <div className="space-y-3">
                  <div className={`flex items-center p-3 rounded-lg ${
                    analysis.average_turnover_rate > 0.3 ? 'bg-red-50' : 
                    analysis.average_turnover_rate > 0.15 ? 'bg-yellow-50' : 'bg-green-50'
                  }`}>
                    <div className={`w-3 h-3 rounded-full mr-3 ${
                      analysis.average_turnover_rate > 0.3 ? 'bg-red-500' : 
                      analysis.average_turnover_rate > 0.15 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}></div>
                    <div>
                      <div className="text-sm font-medium">
                        {analysis.average_turnover_rate > 0.3 ? 'High Turnover Risk' : 
                         analysis.average_turnover_rate > 0.15 ? 'Moderate Turnover Risk' : 'Low Turnover Risk'}
                      </div>
                      <div className="text-xs text-gray-600">
                        Average {(analysis.average_turnover_rate * 100).toFixed(1)}% turnover may impact performance through transaction costs
                      </div>
                    </div>
                  </div>

                  <div className={`flex items-center p-3 rounded-lg ${
                    analysis.asset_stability.core_holdings.length < 3 ? 'bg-red-50' : 
                    analysis.asset_stability.core_holdings.length < 8 ? 'bg-yellow-50' : 'bg-green-50'
                  }`}>
                    <div className={`w-3 h-3 rounded-full mr-3 ${
                      analysis.asset_stability.core_holdings.length < 3 ? 'bg-red-500' : 
                      analysis.asset_stability.core_holdings.length < 8 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}></div>
                    <div>
                      <div className="text-sm font-medium">
                        {analysis.asset_stability.core_holdings.length < 3 ? 'Low Portfolio Stability' : 
                         analysis.asset_stability.core_holdings.length < 8 ? 'Moderate Portfolio Stability' : 'High Portfolio Stability'}
                      </div>
                      <div className="text-xs text-gray-600">
                        {analysis.asset_stability.core_holdings.length} core holdings provide portfolio consistency
                      </div>
                    </div>
                  </div>

                  <div className={`flex items-center p-3 rounded-lg ${
                    analysis.turnover_trend === 'increasing' ? 'bg-red-50' : 
                    analysis.turnover_trend === 'decreasing' ? 'bg-green-50' : 'bg-blue-50'
                  }`}>
                    <div className={`w-3 h-3 rounded-full mr-3 ${
                      analysis.turnover_trend === 'increasing' ? 'bg-red-500' : 
                      analysis.turnover_trend === 'decreasing' ? 'bg-green-500' : 'bg-blue-500'
                    }`}></div>
                    <div>
                      <div className="text-sm font-medium capitalize">
                        {analysis.turnover_trend} Turnover Trend
                      </div>
                      <div className="text-xs text-gray-600">
                        Turnover rate is {analysis.turnover_trend} over the analysis period
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Top Stable Assets</h4>
                <div className="space-y-2">
                  {analysis.asset_stability.core_holdings.slice(0, 8).map((asset, index) => (
                    <div key={asset} className="flex items-center justify-between text-sm">
                      <span className="font-mono text-blue-600">{asset}</span>
                      <span className="text-xs text-gray-500">Core</span>
                    </div>
                  ))}
                  {analysis.asset_stability.core_holdings.length > 8 && (
                    <div className="text-xs text-gray-500 text-center pt-2">
                      +{analysis.asset_stability.core_holdings.length - 8} more
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {analysisView === 'distribution' && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-4">Turnover Rate Distribution</h4>
            <div className="h-64">
              <Bar 
                data={distributionData} 
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      display: false
                    },
                    title: {
                      display: true,
                      text: 'Frequency of Turnover Rates'
                    }
                  },
                  scales: {
                    x: {
                      title: {
                        display: true,
                        text: 'Turnover Rate Range'
                      }
                    },
                    y: {
                      title: {
                        display: true,
                        text: 'Number of Periods'
                      },
                      beginAtZero: true
                    }
                  }
                }}
              />
            </div>
          </div>
        )}

        {analysisView === 'assets' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-4">Asset Stability Breakdown</h4>
                <div className="h-64">
                  <Doughnut 
                    data={assetStabilityData} 
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'bottom'
                        }
                      }
                    }}
                  />
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-4">Asset Change Analysis</h4>
                <div className="space-y-4">
                  <div>
                    <h5 className="text-xs font-medium text-green-700 uppercase tracking-wide mb-2">
                      Most Stable Assets
                    </h5>
                    <div className="space-y-1">
                      {analysis.asset_stability.most_stable_assets.slice(0, 5).map((asset) => (
                        <div key={asset} className="text-sm font-mono text-green-800 bg-green-50 px-2 py-1 rounded">
                          {asset}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h5 className="text-xs font-medium text-red-700 uppercase tracking-wide mb-2">
                      Most Volatile Assets
                    </h5>
                    <div className="space-y-1">
                      {analysis.asset_stability.most_volatile_assets.slice(0, 5).map((asset) => (
                        <div key={asset} className="text-sm font-mono text-red-800 bg-red-50 px-2 py-1 rounded">
                          {asset}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {analysisView === 'trends' && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-4">Turnover and Asset Count Trends</h4>
            <div className="h-80">
              <Line 
                data={trendData} 
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  interaction: {
                    mode: 'index',
                    intersect: false,
                  },
                  scales: {
                    x: {
                      display: true,
                      title: {
                        display: true,
                        text: 'Period'
                      }
                    },
                    y: {
                      type: 'linear',
                      display: true,
                      position: 'left',
                      title: {
                        display: true,
                        text: 'Turnover Rate (%)'
                      }
                    },
                    y1: {
                      type: 'linear',
                      display: true,
                      position: 'right',
                      title: {
                        display: true,
                        text: 'Asset Count'
                      },
                      grid: {
                        drawOnChartArea: false,
                      },
                    }
                  },
                  plugins: {
                    legend: {
                      position: 'top'
                    },
                    title: {
                      display: true,
                      text: 'Portfolio Evolution Over Time'
                    }
                  }
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TurnoverAnalysisComponent;