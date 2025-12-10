import React, { memo, useMemo, useCallback, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import GCPResourceCard from './gcp/GCPResourceCard';
import { GCPService } from '../types/gcp';

interface VirtualizedGCPResourceListProps {
  resources: GCPService[];
  selectedResourceId: string | null | undefined;
  onResourceSelect: (resource: GCPService | null) => void;
  /** Number of columns in the grid */
  columns?: number;
  /** Enable virtualization threshold */
  virtualizationThreshold?: number;
}

// Estimated card dimensions
const CARD_HEIGHT = 180;
const CARD_GAP = 16;

/**
 * Virtualized GCP Resource List
 * Efficiently renders large lists of GCP resources using virtualization
 */
const VirtualizedGCPResourceList: React.FC<VirtualizedGCPResourceListProps> = memo(({
  resources,
  selectedResourceId,
  onResourceSelect,
  columns = 3,
  virtualizationThreshold = 30,
}) => {
  const parentRef = useRef<HTMLDivElement>(null);

  // Group resources into rows for grid layout
  const rows = useMemo(() => {
    const result: GCPService[][] = [];
    for (let i = 0; i < resources.length; i += columns) {
      result.push(resources.slice(i, i + columns));
    }
    return result;
  }, [resources, columns]);

  // Determine if we should use virtualization
  const useVirtualization = resources.length > virtualizationThreshold;

  // Setup virtualizer for rows
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => CARD_HEIGHT + CARD_GAP,
    overscan: 3,
  });

  // Create stable select handler
  const createSelectHandler = useCallback((resource: GCPService) => () => {
    onResourceSelect(resource);
  }, [onResourceSelect]);

  if (!useVirtualization) {
    // Regular grid rendering for small lists
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {resources.map((resource) => (
          <GCPResourceCard
            key={resource.id}
            resource={resource}
            isSelected={selectedResourceId === resource.id}
            onSelect={createSelectHandler(resource)}
          />
        ))}
      </div>
    );
  }

  // Virtualized grid rendering
  return (
    <div 
      ref={parentRef}
      className="h-full overflow-y-auto"
      style={{ contain: 'strict' }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const row = rows[virtualRow.index];
          return (
            <div
              key={virtualRow.index}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size - CARD_GAP}px`,
                transform: `translateY(${virtualRow.start}px)`,
                paddingBottom: `${CARD_GAP}px`,
              }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {row.map((resource) => (
                  <GCPResourceCard
                    key={resource.id}
                    resource={resource}
                    isSelected={selectedResourceId === resource.id}
                    onSelect={createSelectHandler(resource)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Virtualization stats (dev mode) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-gray-400 text-xs px-2 py-1 rounded shadow">
          📜 {virtualizer.getVirtualItems().length * columns}/{resources.length} resources rendered
        </div>
      )}
    </div>
  );
});

VirtualizedGCPResourceList.displayName = 'VirtualizedGCPResourceList';

export default VirtualizedGCPResourceList;

