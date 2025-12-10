import React, { memo, useMemo, useCallback } from 'react';
import { GCPService } from '../../types/gcp';
import GCPResourceCard from './GCPResourceCard';

interface GCPZoneGroupProps {
  title: string;
  resources: GCPService[];
  selectedResourceId: string | null | undefined;
  onResourceSelect: (resource: GCPService | null) => void;
}

/**
 * Memoized GCPZoneGroup component
 * Renders a group of GCP resources with optimized re-rendering
 */
const GCPZoneGroup: React.FC<GCPZoneGroupProps> = memo(({ 
  title, 
  resources, 
  selectedResourceId, 
  onResourceSelect 
}) => {
  // Memoize resource count
  const resourceCount = useMemo(() => resources.length, [resources.length]);

  // Create stable select handlers
  const createSelectHandler = useCallback((resource: GCPService) => () => {
    onResourceSelect(resource);
  }, [onResourceSelect]);

  // Don't render if no resources
  if (resources.length === 0) {
    return null;
  }

  return (
    <section>
      {title && (
        <div className="flex items-center mb-4">
          <h4 className="text-md font-medium text-gray-400 capitalize">{title}</h4>
          <span className="ml-2 text-xs font-mono bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">
            {resourceCount}
          </span>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
        {resources.map((resource) => (
          <GCPResourceCard
            key={resource.id}
            resource={resource}
            isSelected={selectedResourceId === resource.id}
            onSelect={createSelectHandler(resource)}
          />
        ))}
      </div>
    </section>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for optimal re-rendering
  if (prevProps.title !== nextProps.title) return false;
  if (prevProps.selectedResourceId !== nextProps.selectedResourceId) return false;
  if (prevProps.resources.length !== nextProps.resources.length) return false;
  if (prevProps.onResourceSelect !== nextProps.onResourceSelect) return false;
  
  // Deep compare resource IDs and key properties
  for (let i = 0; i < prevProps.resources.length; i++) {
    const prev = prevProps.resources[i];
    const next = nextProps.resources[i];
    if (
      prev.id !== next.id ||
      prev.status !== next.status ||
      prev.healthStatus !== next.healthStatus
    ) {
      return false;
    }
  }
  
  return true;
});

GCPZoneGroup.displayName = 'GCPZoneGroup';

export default GCPZoneGroup;
