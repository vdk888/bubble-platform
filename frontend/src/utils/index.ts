import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility function to merge Tailwind classes
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format currency values
export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

// Format large numbers (for market cap, etc.)
export function formatLargeNumber(num: number): string {
  if (num >= 1e12) {
    return `$${(num / 1e12).toFixed(1)}T`;
  } else if (num >= 1e9) {
    return `$${(num / 1e9).toFixed(1)}B`;
  } else if (num >= 1e6) {
    return `$${(num / 1e6).toFixed(1)}M`;
  } else if (num >= 1e3) {
    return `$${(num / 1e3).toFixed(1)}K`;
  }
  return `$${num.toFixed(0)}`;
}

// Format percentage
export function formatPercentage(num: number, decimals: number = 1): string {
  return `${(num * 100).toFixed(decimals)}%`;
}

// Format date
export function formatDate(dateString: string, format: 'short' | 'long' = 'short'): string {
  const date = new Date(dateString);
  
  if (format === 'long') {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
  
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Validate symbol format (basic)
export function isValidSymbol(symbol: string): boolean {
  // Basic symbol validation - 1-5 characters, letters only
  return /^[A-Z]{1,5}$/.test(symbol.toUpperCase());
}

// Parse symbols from text input
export function parseSymbols(text: string): string[] {
  return text
    .split(/[,\s\n]+/)
    .map(s => s.trim().toUpperCase())
    .filter(s => s.length > 0 && isValidSymbol(s));
}

// Debounce function
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Generate unique ID
export function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}

// Color utilities for charts and status indicators
export const colors = {
  primary: {
    50: '#eff6ff',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
  },
  success: {
    50: '#f0fdf4',
    500: '#22c55e',
    600: '#16a34a',
  },
  warning: {
    50: '#fefce8',
    500: '#eab308',
    600: '#ca8a04',
  },
  error: {
    50: '#fef2f2',
    500: '#ef4444',
    600: '#dc2626',
  },
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
};

// Status badge utilities
export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'active':
    case 'validated':
    case 'success':
      return 'bg-success-100 text-success-800';
    case 'pending':
    case 'processing':
    case 'warning':
      return 'bg-warning-100 text-warning-800';
    case 'inactive':
    case 'failed':
    case 'error':
      return 'bg-error-100 text-error-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

// Local storage utilities with error handling
export const storage = {
  get: (key: string, defaultValue: any = null) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },
  
  set: (key: string, value: any) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn('Failed to save to localStorage:', error);
    }
  },
  
  remove: (key: string) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to remove from localStorage:', error);
    }
  },
};