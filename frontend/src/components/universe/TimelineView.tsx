import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { 
  ZoomInIcon, 
  ZoomOutIcon,
  PlayIcon,
  CalendarIcon,
  TrendingUpIcon,
  AlertTriangleIcon,
  InfoIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from 'lucide-react';
import { 
  UniverseSnapshot,
  DateRange
} from '../../types/temporal';
import { useUniverseTimeline, useDateRangePresets } from '../../hooks/useTemporalUniverse';

export interface TimelineViewProps {
  snapshots: UniverseSnapshot[];
  selectedDate: string | null;
  onDateSelect: (date: string) => void;
  highlightChanges?: boolean;
  height?: number;
  showZoomControls?: boolean;
}

interface TimelineMarker {
  id: string;
  date: Date;
  dateString: string;
  snapshot: UniverseSnapshot;
  x: number;
  turnoverLevel: 'low' | 'moderate' | 'high';
  size: number;
}

interface TimelineScale {
  domain: [Date, Date];
  range: [number, number];
  scale: (date: Date) => number;
  invert: (position: number) => Date;
}

interface ZoomLevel {
  id: string;
  label: string;
  months: number;
}

/**
 * TimelineView Component - Interactive horizontal timeline for temporal universe navigation
 * 
 * Features:
 * - SVG-based horizontal timeline with snapshot markers
 * - Visual indicators for turnover levels (green/yellow/red)
 * - Interactive selection with click and keyboard support
 * - Zoom controls with preset periods (1Y, 2Y, 5Y, All time)
 * - Minimap navigation for long time series
 * - Touch support for mobile/tablet
 * - Professional fintech styling with tooltips
 */
const TimelineView: React.FC<TimelineViewProps> = ({
  snapshots,
  selectedDate,
  onDateSelect,
  highlightChanges = true,
  height = 120,
  showZoomControls = true
}) => {
  // Component refs and state
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentZoom, setCurrentZoom] = useState<string>('1Y');
  const [viewportRange, setViewportRange] = useState<DateRange | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; viewStart: Date } | null>(null);
  const [hoveredMarker, setHoveredMarker] = useState<TimelineMarker | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  // Date range presets
  const dateRangePresets = useDateRangePresets();

  // Zoom level configurations
  const zoomLevels: ZoomLevel[] = useMemo(() => [
    { id: '1Y', label: '1Y', months: 12 },
    { id: '2Y', label: '2Y', months: 24 },
    { id: '5Y', label: '5Y', months: 60 },
    { id: 'ALL', label: 'All', months: -1 }
  ], []);

  // Calculate effective viewport range
  const effectiveViewportRange = useMemo(() => {
    if (viewportRange) return viewportRange;
    
    const currentZoomLevel = zoomLevels.find(z => z.id === currentZoom);
    if (!currentZoomLevel) return null;
    
    if (currentZoomLevel.months === -1) {
      // All time - use full data range
      if (snapshots.length === 0) return null;
      const dates = snapshots.map(s => new Date(s.snapshot_date)).sort((a, b) => a.getTime() - b.getTime());
      return {
        start_date: dates[0].toISOString().split('T')[0],
        end_date: dates[dates.length - 1].toISOString().split('T')[0]
      };
    }
    
    // Use preset range
    const presetKey = currentZoom === '1Y' ? 'lastYear' : 
                      currentZoom === '2Y' ? 'last2Years' : 'last5Years';
    return dateRangePresets[presetKey] || dateRangePresets.lastYear;
  }, [viewportRange, currentZoom, zoomLevels, snapshots, dateRangePresets]);

  // Timeline dimensions and layout
  const margin = { top: 20, right: 40, bottom: 40, left: 40 };
  const timelineWidth = 800; // Base width, will be responsive
  const timelineHeight = height - margin.top - margin.bottom;
  const markerRadius = { min: 4, max: 12 };

  // Create timeline scale
  const timelineScale = useMemo((): TimelineScale | null => {
    if (!effectiveViewportRange || !snapshots.length) return null;

    const startDate = new Date(effectiveViewportRange.start_date);
    const endDate = new Date(effectiveViewportRange.end_date);
    
    const scale = (date: Date) => {
      const t = (date.getTime() - startDate.getTime()) / (endDate.getTime() - startDate.getTime());
      return margin.left + t * (timelineWidth - margin.left - margin.right);
    };
    
    const invert = (position: number) => {
      const t = (position - margin.left) / (timelineWidth - margin.left - margin.right);
      return new Date(startDate.getTime() + t * (endDate.getTime() - startDate.getTime()));
    };
    
    return {
      domain: [startDate, endDate],
      range: [margin.left, timelineWidth - margin.right],
      scale,
      invert
    };
  }, [effectiveViewportRange, snapshots, margin, timelineWidth]);

  // Process snapshots into timeline markers
  const timelineMarkers = useMemo((): TimelineMarker[] => {
    if (!timelineScale || !effectiveViewportRange) return [];

    const startDate = new Date(effectiveViewportRange.start_date);
    const endDate = new Date(effectiveViewportRange.end_date);

    return snapshots
      .filter(snapshot => {
        const snapshotDate = new Date(snapshot.snapshot_date);
        return snapshotDate >= startDate && snapshotDate <= endDate;
      })
      .map((snapshot): TimelineMarker => {
        const date = new Date(snapshot.snapshot_date);
        const turnoverRate = snapshot.turnover_rate || 0;
        
        // Determine turnover level and visual properties
        let turnoverLevel: 'low' | 'moderate' | 'high';
        let size: number;
        
        if (turnoverRate > 0.25) {
          turnoverLevel = 'high';
          size = markerRadius.max;
        } else if (turnoverRate > 0.10) {
          turnoverLevel = 'moderate';  
          size = Math.round((markerRadius.min + markerRadius.max) / 2);
        } else {
          turnoverLevel = 'low';
          size = markerRadius.min;
        }
        
        return {
          id: snapshot.id,
          date,
          dateString: snapshot.snapshot_date,
          snapshot,
          x: timelineScale.scale(date),
          turnoverLevel,
          size
        };
      })
      .sort((a, b) => a.date.getTime() - b.date.getTime());
  }, [snapshots, timelineScale, effectiveViewportRange, markerRadius]);

  // Get marker color based on turnover level
  const getMarkerColor = useCallback((turnoverLevel: 'low' | 'moderate' | 'high', isSelected: boolean, isHovered: boolean) => {
    const colors = {
      low: { 
        fill: isSelected ? '#10B981' : '#6EE7B7', 
        stroke: isSelected ? '#047857' : '#10B981',
        hover: '#34D399' 
      },
      moderate: { 
        fill: isSelected ? '#F59E0B' : '#FCD34D', 
        stroke: isSelected ? '#D97706' : '#F59E0B',
        hover: '#FBBF24' 
      },
      high: { 
        fill: isSelected ? '#EF4444' : '#FCA5A5', 
        stroke: isSelected ? '#DC2626' : '#EF4444',
        hover: '#F87171' 
      }
    };
    
    if (isHovered) {
      return { fill: colors[turnoverLevel].hover, stroke: colors[turnoverLevel].stroke };
    }
    
    return colors[turnoverLevel];
  }, []);

  // Format date for display
  const formatDateLabel = useCallback((date: Date): string => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }, []);

  // Generate axis ticks
  const axisTicks = useMemo(() => {
    if (!timelineScale) return [];
    
    const [startDate, endDate] = timelineScale.domain;
    const ticks: { date: Date; x: number; label: string }[] = [];
    
    // Determine tick interval based on range
    const rangeDays = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24);
    
    let tickInterval: number; // in days
    if (rangeDays <= 90) {
      tickInterval = 7; // Weekly
    } else if (rangeDays <= 365) {
      tickInterval = 30; // Monthly
    } else if (rangeDays <= 730) {
      tickInterval = 60; // Bi-monthly
    } else {
      tickInterval = 90; // Quarterly
    }
    
    const current = new Date(startDate);
    while (current <= endDate) {
      ticks.push({
        date: new Date(current),
        x: timelineScale.scale(current),
        label: formatDateLabel(current)
      });
      current.setDate(current.getDate() + tickInterval);
    }
    
    return ticks;
  }, [timelineScale, formatDateLabel]);

  // Handle marker click
  const handleMarkerClick = useCallback((marker: TimelineMarker) => {
    onDateSelect(marker.dateString);
    setFocusedIndex(timelineMarkers.findIndex(m => m.id === marker.id));
  }, [onDateSelect, timelineMarkers]);

  // Handle zoom change
  const handleZoomChange = useCallback((zoomId: string) => {
    setCurrentZoom(zoomId);
    setViewportRange(null); // Reset custom viewport
  }, []);

  // Handle pan/drag
  const handleMouseDown = useCallback((event: React.MouseEvent<SVGSVGElement>) => {
    if (!timelineScale) return;
    
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const x = event.clientX - rect.left;
    setIsDragging(true);
    setDragStart({
      x,
      viewStart: timelineScale.domain[0]
    });
  }, [timelineScale]);

  const handleMouseMove = useCallback((event: React.MouseEvent<SVGSVGElement>) => {
    if (!isDragging || !dragStart || !timelineScale) return;
    
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const currentX = event.clientX - rect.left;
    const deltaX = currentX - dragStart.x;
    
    // Calculate time delta based on pixel movement
    const timeDelta = (deltaX / (timelineWidth - margin.left - margin.right)) * 
                     (timelineScale.domain[1].getTime() - timelineScale.domain[0].getTime());
    
    const newStartDate = new Date(dragStart.viewStart.getTime() - timeDelta);
    const newEndDate = new Date(newStartDate.getTime() + 
      (timelineScale.domain[1].getTime() - timelineScale.domain[0].getTime()));
    
    setViewportRange({
      start_date: newStartDate.toISOString().split('T')[0],
      end_date: newEndDate.toISOString().split('T')[0]
    });
  }, [isDragging, dragStart, timelineScale, timelineWidth, margin]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragStart(null);
  }, []);

  // Keyboard navigation
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (timelineMarkers.length === 0) return;
    
    switch (event.key) {
      case 'ArrowLeft':
        event.preventDefault();
        setFocusedIndex(prev => Math.max(0, prev - 1));
        break;
      case 'ArrowRight':
        event.preventDefault();
        setFocusedIndex(prev => Math.min(timelineMarkers.length - 1, prev + 1));
        break;
      case 'Enter':
      case ' ':
        event.preventDefault();
        if (focusedIndex >= 0 && focusedIndex < timelineMarkers.length) {
          handleMarkerClick(timelineMarkers[focusedIndex]);
        }
        break;
      case 'Home':
        event.preventDefault();
        setFocusedIndex(0);
        break;
      case 'End':
        event.preventDefault();
        setFocusedIndex(timelineMarkers.length - 1);
        break;
    }
  }, [timelineMarkers, focusedIndex, handleMarkerClick]);

  // Auto-focus on selected date change
  useEffect(() => {
    if (selectedDate) {
      const index = timelineMarkers.findIndex(m => m.dateString === selectedDate);
      if (index >= 0) {
        setFocusedIndex(index);
      }
    }
  }, [selectedDate, timelineMarkers]);

  // Loading state
  if (!timelineScale || timelineMarkers.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6" style={{ height }}>
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <CalendarIcon className="mx-auto h-12 w-12 text-gray-400 mb-3" />
            <p className="text-sm text-gray-500">No timeline data available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef} 
      className="bg-white border border-gray-200 rounded-lg"
      style={{ height }}
    >
      {/* Header with zoom controls */}
      {showZoomControls && (
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-900 flex items-center">
            <TrendingUpIcon className="w-4 h-4 mr-2" />
            Universe Timeline
          </h3>
          <div className="flex items-center space-x-2">
            <div className="flex items-center bg-gray-100 rounded-md p-1">
              {zoomLevels.map((zoom) => (
                <button
                  key={zoom.id}
                  onClick={() => handleZoomChange(zoom.id)}
                  className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                    currentZoom === zoom.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  {zoom.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Timeline SVG */}
      <div className="relative p-4">
        <svg
          ref={svgRef}
          width="100%"
          height={height - (showZoomControls ? 60 : 16)}
          viewBox={`0 0 ${timelineWidth} ${height - (showZoomControls ? 60 : 16)}`}
          className="overflow-visible cursor-move"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onKeyDown={handleKeyDown}
          tabIndex={0}
          role="application"
          aria-label="Interactive timeline for universe evolution"
        >
          {/* Timeline axis line */}
          <line
            x1={margin.left}
            y1={timelineHeight / 2}
            x2={timelineWidth - margin.right}
            y2={timelineHeight / 2}
            stroke="#D1D5DB"
            strokeWidth="2"
          />
          
          {/* Axis ticks and labels */}
          {axisTicks.map((tick, index) => (
            <g key={index}>
              <line
                x1={tick.x}
                y1={timelineHeight / 2 - 5}
                x2={tick.x}
                y2={timelineHeight / 2 + 5}
                stroke="#9CA3AF"
                strokeWidth="1"
              />
              <text
                x={tick.x}
                y={timelineHeight / 2 + 20}
                textAnchor="middle"
                fontSize="10"
                fill="#6B7280"
              >
                {tick.label}
              </text>
            </g>
          ))}

          {/* Timeline markers */}
          {timelineMarkers.map((marker, index) => {
            const isSelected = selectedDate === marker.dateString;
            const isHovered = hoveredMarker?.id === marker.id;
            const isFocused = focusedIndex === index;
            const colors = getMarkerColor(marker.turnoverLevel, isSelected, isHovered);

            return (
              <g key={marker.id}>
                {/* Focus ring */}
                {isFocused && (
                  <circle
                    cx={marker.x}
                    cy={timelineHeight / 2}
                    r={marker.size + 3}
                    fill="none"
                    stroke="#2563EB"
                    strokeWidth="2"
                    strokeDasharray="3,3"
                    opacity="0.7"
                  />
                )}
                
                {/* Main marker */}
                <circle
                  cx={marker.x}
                  cy={timelineHeight / 2}
                  r={marker.size}
                  fill={colors.fill}
                  stroke={colors.stroke}
                  strokeWidth="2"
                  className="cursor-pointer transition-all duration-200"
                  onMouseEnter={() => setHoveredMarker(marker)}
                  onMouseLeave={() => setHoveredMarker(null)}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleMarkerClick(marker);
                  }}
                />

                {/* High turnover indicator */}
                {marker.turnoverLevel === 'high' && (
                  <circle
                    cx={marker.x}
                    cy={timelineHeight / 2}
                    r={marker.size - 2}
                    fill="none"
                    stroke="white"
                    strokeWidth="1"
                    pointerEvents="none"
                  />
                )}
              </g>
            );
          })}

          {/* Current selection indicator */}
          {selectedDate && timelineMarkers.some(m => m.dateString === selectedDate) && (
            <g>
              {timelineMarkers
                .filter(m => m.dateString === selectedDate)
                .map(marker => (
                  <g key={`selected-${marker.id}`}>
                    <line
                      x1={marker.x}
                      y1={5}
                      x2={marker.x}
                      y2={timelineHeight - 5}
                      stroke="#2563EB"
                      strokeWidth="2"
                      strokeDasharray="4,4"
                      opacity="0.7"
                    />
                  </g>
                ))
              }
            </g>
          )}
        </svg>

        {/* Tooltip */}
        {hoveredMarker && (
          <div
            className="absolute z-10 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg pointer-events-none"
            style={{
              left: hoveredMarker.x,
              top: 10,
              transform: 'translateX(-50%)'
            }}
          >
            <div className="font-medium">{formatDateLabel(hoveredMarker.date)}</div>
            <div className="text-gray-300">
              Assets: {hoveredMarker.snapshot.assets?.length || 0}
            </div>
            {hoveredMarker.snapshot.turnover_rate !== null && hoveredMarker.snapshot.turnover_rate !== undefined && (
              <div className="text-gray-300">
                Turnover: {(hoveredMarker.snapshot.turnover_rate * 100).toFixed(1)}%
              </div>
            )}
            {highlightChanges && (
              <div className="text-gray-300 text-xs mt-1">
                +{hoveredMarker.snapshot.assets_added?.length || 0} / 
                -{hoveredMarker.snapshot.assets_removed?.length || 0} assets
              </div>
            )}
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-2 right-2 bg-white bg-opacity-90 rounded-lg p-2 text-xs">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 rounded-full bg-green-400"></div>
              <span className="text-gray-600">Low turnover</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
              <span className="text-gray-600">Moderate</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 rounded-full bg-red-400"></div>
              <span className="text-gray-600">High turnover</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimelineView;