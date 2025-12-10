/**
 * GCP Architecture Store
 * Global state management for GCP architecture data with caching
 * 
 * Key Features:
 * - NO automatic fetching
 * - Manual refresh only (user clicks button)
 * - Persists across tab switches
 * - Memoized selectors for performance
 * - Client-side caching with TTL
 */

import { create } from 'zustand';
import { GCPArchitecture, GCPService } from '../types/gcp';
import { gcpApi } from '../services/gcpApi';
import { useMemo } from 'react';

// Cache configuration
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface GCPArchitectureState {
  // State
  architecture: GCPArchitecture | null;
  loading: boolean;
  error: Error | null;
  lastFetch: Date | null;

  // Actions
  fetchArchitecture: (credentials: any, project: string, regions?: string[]) => Promise<void>;
  clearArchitecture: () => void;
  isCacheValid: () => boolean;
}

export const useGCPArchitectureStore = create<GCPArchitectureState>((set, get) => ({
  // Initial state
  architecture: null,
  loading: false,
  error: null,
  lastFetch: null,

  // Check if cache is still valid
  isCacheValid: () => {
    const { lastFetch } = get();
    if (!lastFetch) return false;
    return Date.now() - lastFetch.getTime() < CACHE_TTL_MS;
  },

  // Manual fetch only - with cache check
  fetchArchitecture: async (credentials: any, project: string, regions?: string[]) => {
    const state = get();
    
    // Check if we have valid cached data for the same project
    if (
      state.architecture &&
      state.architecture.project === project &&
      state.isCacheValid()
    ) {
      console.log('📦 Using cached architecture data');
      return;
    }

    set({ loading: true, error: null });
    
    try {
      console.log('🔍 Manual fetch triggered for project:', project);
      
      const data = await gcpApi.discoverResources(credentials, project, regions);
      
      set({
        architecture: data,
        loading: false,
        error: null,
        lastFetch: new Date(),
      });
      
      console.log('✅ Architecture data stored:', data.resources.length, 'resources');
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch architecture');
      console.error('❌ Fetch failed:', error.message);
      
      set({
        loading: false,
        error,
      });
    }
  },

  // Clear architecture data
  clearArchitecture: () => {
    console.log('🗑️ Clearing architecture data');
    set({
      architecture: null,
      loading: false,
      error: null,
      lastFetch: null,
    });
  },
}));

// ===== Memoized Selectors =====

/**
 * Select resources grouped by type
 */
export const useResourcesByType = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return {};
    
    const grouped: Record<string, GCPService[]> = {};
    architecture.resources.forEach(resource => {
      const type = resource.type;
      if (!grouped[type]) {
        grouped[type] = [];
      }
      grouped[type].push(resource);
    });
    
    return grouped;
  }, [architecture]);
};

/**
 * Select resources by region
 */
export const useResourcesByRegion = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return {};
    
    const grouped: Record<string, GCPService[]> = {};
    architecture.resources.forEach(resource => {
      const region = resource.region || 'global';
      if (!grouped[region]) {
        grouped[region] = [];
      }
      grouped[region].push(resource);
    });
    
    return grouped;
  }, [architecture]);
};

/**
 * Select resources filtered by type
 */
export const useFilteredResources = (typeFilter: string | null, regionFilter: string | null) => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return [];
    
    let filtered = architecture.resources;
    
    if (typeFilter) {
      filtered = filtered.filter(r => r.type === typeFilter);
    }
    
    if (regionFilter) {
      filtered = filtered.filter(r => r.region === regionFilter);
    }
    
    return filtered;
  }, [architecture, typeFilter, regionFilter]);
};

/**
 * Select total cost
 */
export const useTotalCost = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  return useMemo(() => architecture?.totalCost ?? 0, [architecture]);
};

/**
 * Select cost by type
 */
export const useCostByType = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return {};
    
    const costs: Record<string, number> = {};
    architecture.resources.forEach(resource => {
      const type = resource.type;
      const cost = resource.costEstimate?.monthly ?? 0;
      costs[type] = (costs[type] || 0) + cost;
    });
    
    return costs;
  }, [architecture]);
};

/**
 * Select resource count by type
 */
export const useResourceCounts = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return {};
    
    const counts: Record<string, number> = {};
    architecture.resources.forEach(resource => {
      const type = resource.type;
      counts[type] = (counts[type] || 0) + 1;
    });
    
    return counts;
  }, [architecture]);
};

/**
 * Select unique regions
 */
export const useRegions = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return [];
    return architecture.regions;
  }, [architecture]);
};

/**
 * Select resource by ID
 */
export const useResourceById = (resourceId: string | null) => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture || !resourceId) return null;
    return architecture.resources.find(r => r.id === resourceId) || null;
  }, [architecture, resourceId]);
};

/**
 * Select application stacks
 */
export const useApplicationStacks = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return [];
    return architecture.applicationStacks;
  }, [architecture]);
};

/**
 * Select connections
 */
export const useConnections = () => {
  const architecture = useGCPArchitectureStore(state => state.architecture);
  
  return useMemo(() => {
    if (!architecture) return [];
    return architecture.connections;
  }, [architecture]);
};
