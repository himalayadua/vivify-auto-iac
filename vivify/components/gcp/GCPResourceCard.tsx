import React, { memo, useMemo, useCallback } from 'react';
import { GCPService } from '../../types/gcp';
import { getGCPIcon } from '../../utils/gcp';

interface GCPResourceCardProps {
  resource: GCPService;
  isSelected: boolean;
  onSelect: () => void;
}

// Move constants outside component to prevent recreation
const HEALTH_STATUS_CONFIG = {
  healthy: { dot: 'bg-green-500', border: 'border-l-green-500' },
  warning: { dot: 'bg-yellow-500', border: 'border-l-yellow-500' },
  critical: { dot: 'bg-red-500', border: 'border-l-red-500' },
  unknown: { dot: 'bg-gray-500', border: 'border-l-gray-500' },
} as const;

const STATUS_CONFIG = {
  running: 'text-green-400 bg-green-900/50',
  stopped: 'text-yellow-400 bg-yellow-900/50',
  deploying: 'text-blue-400 bg-blue-900/50',
  error: 'text-red-400 bg-red-900/50',
} as const;

/**
 * Memoized GCP Resource Card component
 * Optimized for rendering in large lists
 */
const GCPResourceCard: React.FC<GCPResourceCardProps> = memo(({ resource, isSelected, onSelect }) => {
  // Memoize icon component
  const Icon = useMemo(() => getGCPIcon(resource.type), [resource.type]);
  
  // Memoize config lookups
  const healthConfig = useMemo(() => 
    HEALTH_STATUS_CONFIG[resource.healthStatus] || HEALTH_STATUS_CONFIG.unknown,
    [resource.healthStatus]
  );
  
  const statusConfig = useMemo(() => 
    STATUS_CONFIG[resource.status] || STATUS_CONFIG.error,
    [resource.status]
  );

  // Memoize formatted type name
  const typeName = useMemo(() => 
    resource.type.replace('google_', '').replace(/_/g, ' '),
    [resource.type]
  );

  // Memoize cost display
  const costDisplay = useMemo(() => 
    resource.costEstimate ? `$${resource.costEstimate.monthly.toFixed(2)}` : null,
    [resource.costEstimate?.monthly]
  );

  // Memoize location display
  const locationDisplay = useMemo(() => 
    resource.zone || resource.region,
    [resource.zone, resource.region]
  );

  // Memoize card class name
  const cardClassName = useMemo(() => 
    `bg-gray-800 rounded-lg p-3 cursor-pointer transition-all duration-200 shadow-md hover:shadow-lg hover:scale-[1.02] border-l-4 ${healthConfig.border} ${isSelected ? 'ring-2 ring-blue-500' : 'ring-0 ring-transparent'}`,
    [healthConfig.border, isSelected]
  );

  // Stable click handler
  const handleClick = useCallback(() => {
    onSelect();
  }, [onSelect]);

  return (
    <div
      onClick={handleClick}
      className={cardClassName}
    >
      {/* Card Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-gray-700 rounded-md">
            <Icon className="w-5 h-5 text-gray-300" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-white truncate w-32" title={resource.name}>
              {resource.name}
            </h3>
            <p className="text-xs text-gray-400 capitalize">{typeName}</p>
          </div>
        </div>
        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusConfig}`}>
          {resource.status}
        </span>
      </div>
      
      {/* Card Body - Key Metrics */}
      <ResourceMetrics 
        cpu={resource.metrics?.cpu}
        memory={resource.metrics?.memory}
        cost={costDisplay}
      />

      {/* Card Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-700">
        <div className="flex items-center space-x-2">
          <span className={`w-2.5 h-2.5 rounded-full ${healthConfig.dot}`}></span>
          <span className="text-xs text-gray-400 capitalize">{resource.healthStatus}</span>
        </div>
        <div className="text-xs text-gray-500">
          {locationDisplay}
        </div>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for optimal re-rendering
  return (
    prevProps.resource.id === nextProps.resource.id &&
    prevProps.resource.status === nextProps.resource.status &&
    prevProps.resource.healthStatus === nextProps.resource.healthStatus &&
    prevProps.resource.metrics?.cpu === nextProps.resource.metrics?.cpu &&
    prevProps.resource.metrics?.memory === nextProps.resource.metrics?.memory &&
    prevProps.resource.costEstimate?.monthly === nextProps.resource.costEstimate?.monthly &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onSelect === nextProps.onSelect
  );
});

GCPResourceCard.displayName = 'GCPResourceCard';

/**
 * Memoized metrics display component
 */
interface ResourceMetricsProps {
  cpu?: number;
  memory?: number;
  cost: string | null;
}

const ResourceMetrics: React.FC<ResourceMetricsProps> = memo(({ cpu, memory, cost }) => {
  // Skip rendering if no metrics
  if (cpu === undefined && memory === undefined && !cost) {
    return <div className="my-3" />;
  }

  return (
    <div className="text-xs text-gray-400 space-y-1 my-3">
      {cpu !== undefined && (
        <div className="flex justify-between">
          <span>CPU</span>
          <span className="font-mono text-gray-200">{cpu}%</span>
        </div>
      )}
      {memory !== undefined && (
        <div className="flex justify-between">
          <span>Memory</span>
          <span className="font-mono text-gray-200">{memory}%</span>
        </div>
      )}
      {cost && (
        <div className="flex justify-between">
          <span>Cost/Mo</span>
          <span className="font-mono text-gray-200">{cost}</span>
        </div>
      )}
    </div>
  );
});

ResourceMetrics.displayName = 'ResourceMetrics';

export default GCPResourceCard;
