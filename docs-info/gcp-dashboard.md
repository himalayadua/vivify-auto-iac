# GCP Architecture Dashboard - Detailed Implementation Prompt

## Overview

Create a comprehensive GCP (Google Cloud Platform) Architecture Dashboard that visualizes GCP infrastructure resources on an interactive canvas. The dashboard should use VivifyRT for resource discovery and display resources with their relationships, metrics, costs, and health status in a beautiful, modern UI similar to the AWS Architecture Dashboard pattern.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Backend Service (Python)                                     │
│                                                               │
│  1. VivifyRT Integration Layer                               │
│     - discover_gcp_resources(project, regions)               │
│     - Uses tools.py VivifyRT functions                      │
│     - Returns structured resource metadata                   │
│                                                               │
│  2. GCP API Enrichment Layer                                 │
│     - Fetch live metrics from Cloud Monitoring               │
│     - Get cost estimates from Billing API                   │
│     - Retrieve health status from various APIs              │
│                                                               │
│  3. Relationship Detection                                   │
│     - Parse network_interface references                    │
│     - Map firewall rules to instances                       │
│     - Link buckets to functions/instances                    │
│     - Connect GKE clusters to node pools                    │
│                                                               │
│  4. Data Transformation                                      │
│     - Convert VivifyRT output → GCPArchitecture format      │
│     - Group by zones/regions                                 │
│     - Build connection graph                                 │
│                                                               │
│  5. API Endpoint                                             │
│     - GET /api/gcp/architecture?project=X&regions=Y,Z       │
│     - Returns JSON matching GCPArchitecture interface        │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Frontend (React + TypeScript)                                │
│                                                               │
│  GCPArchitectureDashboard Component                          │
│    - Resource cards with GCP-specific styling                │
│    - Zone/region grouping                                    │
│    - Network topology visualization                          │
│    - Inspector panel with tabs                              │
│    - GCP Console integration                                 │
└─────────────────────────────────────────────────────────────┘
```

## Backend Implementation Requirements

### 1. Python Service Structure

Create a new file: `gcp_discovery_service.py`

```python
"""
GCP Discovery Service
Integrates VivifyRT with GCP APIs to provide enriched resource data for visualization
"""

from typing import Dict, List, Optional, Any
from tools import fetch_resource_state_via_terraform, get_provider_schema
from google.cloud import monitoring_v3, compute_v1, storage, container_v1
from google.cloud import billing_v1
import json

class GCPDiscoveryService:
    """
    Discovers GCP resources using VivifyRT and enriches with live data
    """
    
    def discover_resources(
        self,
        project: str,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main discovery function
        
        Returns:
        {
            "project": "my-project",
            "lastRefresh": "2025-01-27T10:30:00Z",
            "regions": ["us-central1", "us-east1"],
            "zones": {
                "us-central1-a": [...],
                "us-central1-b": [...]
            },
            "resources": [...],
            "connections": [...],
            "totalCost": 1234.56,
            "applicationStacks": [...]
        }
        """
        pass
    
    def _discover_compute_instances(self, project: str, zones: List[str]) -> List[Dict]:
        """Discover VM instances using VivifyRT"""
        pass
    
    def _discover_storage_buckets(self, project: str) -> List[Dict]:
        """Discover GCS buckets"""
        pass
    
    def _discover_gke_clusters(self, project: str, regions: List[str]) -> List[Dict]:
        """Discover GKE clusters"""
        pass
    
    def _discover_networks(self, project: str) -> List[Dict]:
        """Discover VPC networks"""
        pass
    
    def _enrich_with_metrics(self, resource: Dict) -> Dict:
        """Add Cloud Monitoring metrics"""
        pass
    
    def _enrich_with_costs(self, resource: Dict) -> Dict:
        """Add cost estimates"""
        pass
    
    def _detect_relationships(self, resources: List[Dict]) -> List[Dict]:
        """Build connection graph"""
        pass
```

### 2. Resource Type Mappings

Map VivifyRT resource types to dashboard display:

| VivifyRT Type | Display Name | Icon | Color Scheme |
|--------------|--------------|------|--------------|
| `google_compute_instance` | Compute Engine VM | Server/CPU icon | Blue (#4285F4) |
| `google_storage_bucket` | Cloud Storage | Bucket/Storage icon | Green (#34A853) |
| `google_container_cluster` | GKE Cluster | Kubernetes icon | Blue (#4285F4) |
| `google_compute_network` | VPC Network | Network icon | Gray (#5F6368) |
| `google_compute_firewall` | Firewall Rule | Shield icon | Orange (#EA4335) |
| `google_cloud_functions_function` | Cloud Function | Function icon | Purple (#9C27B0) |
| `google_sql_database_instance` | Cloud SQL | Database icon | Blue (#4285F4) |
| `google_compute_disk` | Persistent Disk | Disk icon | Gray (#5F6368) |
| `google_compute_address` | Static IP | IP icon | Gray (#5F6368) |
| `google_compute_forwarding_rule` | Load Balancer | Load Balancer icon | Orange (#FBBC04) |
| `google_pubsub_topic` | Pub/Sub Topic | Message icon | Blue (#4285F4) |
| `google_pubsub_subscription` | Pub/Sub Subscription | Subscription icon | Blue (#4285F4) |
| `google_bigquery_dataset` | BigQuery Dataset | Analytics icon | Blue (#4285F4) |
| `google_cloud_run_service` | Cloud Run | Container icon | Green (#34A853) |
| `google_app_engine_application` | App Engine | App Engine icon | Blue (#4285F4) |

### 3. Data Enrichment Requirements

For each resource discovered via VivifyRT, enrich with:

**Metrics (from Cloud Monitoring API):**
- CPU utilization (%)
- Memory utilization (%)
- Network bytes in/out
- Disk I/O operations
- Request count (for load balancers, functions)
- Error rate
- Latency (p50, p95, p99)

**Cost Estimates (from Billing API or pricing calculator):**
- Monthly cost estimate
- Cost breakdown by component
- Cost trends (if historical data available)

**Health Status:**
- `healthy` - All checks passing
- `warning` - Some metrics above thresholds
- `critical` - Resource failing or degraded
- `unknown` - No metrics available

**Status:**
- `running` - Resource is active
- `stopped` - Resource is stopped
- `deploying` - Resource is being created/updated
- `error` - Resource has errors

### 4. Relationship Detection

Detect and map relationships:

**Network Relationships:**
- Instance → Network (via `network_interface.network`)
- Instance → Subnetwork (via network)
- Firewall → Network (via `network` field)
- Load Balancer → Backend instances

**Storage Relationships:**
- Function → Storage Bucket (via environment variables or code analysis)
- Instance → Storage Bucket (via service account permissions or metadata)

**GKE Relationships:**
- Cluster → Node Pool
- Cluster → Network
- Service → Cluster

**Data Flow:**
- Pub/Sub Topic → Subscription → Function
- Cloud Storage → Function (via triggers)
- BigQuery → Function (via triggers)

## Frontend Implementation Requirements

### 1. TypeScript Type Definitions

Create `types/gcp.ts`:

```typescript
export interface GCPService {
  id: string;
  name: string;
  type: string;  // 'google_compute_instance', 'google_storage_bucket', etc.
  status: 'running' | 'stopped' | 'deploying' | 'error';
  region: string;
  zone?: string;
  project: string;
  description?: string;
  configuration?: Record<string, any>;
  costEstimate?: {
    monthly: number;
    breakdown: string;
    currency?: string;
  };
  metrics?: {
    cpu?: number;
    memory?: number;
    networkIn?: number;  // bytes
    networkOut?: number;  // bytes
    diskReadOps?: number;
    diskWriteOps?: number;
    requests?: number;
    errors?: number;
    latency?: number;  // milliseconds
    errorRate?: number;  // percentage
  };
  labels?: Record<string, string>;
  connections?: string[];  // IDs of connected resources
  healthStatus?: 'healthy' | 'warning' | 'critical' | 'unknown';
  selfLink?: string;  // GCP selfLink for console navigation
  createdAt?: string;
  lastUpdated?: string;
}

export interface GCPConnection {
  id: string;
  from: string;  // Resource ID
  to: string;    // Resource ID
  type: 'network' | 'storage' | 'data' | 'api' | 'trigger';
  protocol?: string;
  port?: number;
  description?: string;
  direction?: 'inbound' | 'outbound' | 'bidirectional';
}

export interface GCPApplicationStack {
  id: string;
  name: string;
  description: string;
  services: GCPService[];
  primaryService?: string;  // Main service ID
  labels: Record<string, string>;
  totalCost: number;
  healthStatus: 'healthy' | 'warning' | 'critical';
  vpc?: string;  // VPC network name
  subnets?: string[];  // Subnetwork names
  region?: string;
  zones?: string[];
}

export interface GCPArchitecture {
  project: string;
  lastRefresh: string;
  regions: string[];
  zones: Record<string, GCPService[]>;  // Zone name -> resources
  resources: GCPService[];
  connections: GCPConnection[];
  totalCost: number;
  costBreakdown: Record<string, number>;  // Stack name -> cost
  applicationStacks: GCPApplicationStack[];
  hasGCPAccess: boolean;
}
```

### 2. Component Structure

Create `components/GCPArchitectureDashboard.tsx`:

**Main Component Structure:**
```typescript
export const GCPArchitectureDashboard: React.FC<GCPArchitectureDashboardProps> = ({
  architecture,
  onRefresh,
  onResourceSelect,
  onResourceAction
}) => {
  // State management
  // Resource grouping by zone/region
  // Network topology rendering
  // Inspector panel
  // Cost summary
  // Health indicators
}
```

### 3. UI/UX Specifications

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Header Bar                                                   │
│ - Project selector                                           │
│ - Region/Zone filter                                          │
│ - Refresh button                                              │
│ - Cost summary (total monthly)                               │
│ - Last refresh timestamp                                      │
└─────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────┬───────────────────────┐
│ Main Canvas Area                     │ Inspector Panel       │
│                                      │ (when resource        │
│ ┌────────────────────────────────┐  │  selected)            │
│ │ Zone/Region Groups             │  │                       │
│ │ ┌──────────┐ ┌──────────┐     │  │ - Resource Details    │
│ │ │ Zone A   │ │ Zone B   │     │  │ - Configuration       │
│ │ │          │ │          │     │  │ - Metrics            │
│ │ │ [Cards]  │ │ [Cards]  │     │  │ - Cost               │
│ │ │          │ │          │     │  │ - Security           │
│ │ └──────────┘ └──────────┘     │  │ - Actions            │
│ │                                │  │                       │
│ │ Network Topology View          │  │                       │
│ │ (optional toggle)               │  │                       │
│ └────────────────────────────────┘  │                       │
│                                      │                       │
│ Application Stacks                   │                       │
│ ┌────────────────────────────────┐  │                       │
│ │ Stack 1: Production            │  │                       │
│ │ [Service cards grid]           │  │                       │
│ └────────────────────────────────┘  │                       │
└──────────────────────────────────────┴───────────────────────┘
```

#### Resource Card Design

Each resource card should display:

**Card Header:**
- Service icon (GCP-specific)
- Resource name (truncated if long)
- Health status indicator (colored dot)
- Status badge (running/stopped/etc.)

**Card Body:**
- Resource type label
- Zone/Region badge
- Key metrics (CPU, Memory, Requests - depending on type)
- Cost estimate ($X.XX/month)
- Connection count indicator

**Card Footer:**
- Status indicator (colored dot + text)
- Quick actions (hover menu)

**Card States:**
- Default: Normal border, subtle shadow
- Hover: Elevated shadow, slight scale (1.02x)
- Selected: Blue ring (ring-2 ring-blue-500), darker shadow
- Multi-selected: Blue ring with opacity
- Error state: Red border-left accent

#### Color Scheme (GCP Brand Colors)

**Primary Colors:**
- Google Blue: `#4285F4` (primary actions, selected states)
- Google Green: `#34A853` (success, healthy status)
- Google Yellow: `#FBBC04` (warnings, caution)
- Google Red: `#EA4335` (errors, critical status)
- Google Gray: `#5F6368` (neutral, secondary)

**Resource Type Colors:**
- Compute Engine: Blue (`bg-blue-50`, `text-blue-700`, `border-blue-200`)
- Cloud Storage: Green (`bg-green-50`, `text-green-700`, `border-green-200`)
- GKE: Blue with Kubernetes accent (`bg-blue-50`, `text-blue-700`)
- Cloud Functions: Purple (`bg-purple-50`, `text-purple-700`, `border-purple-200`)
- Cloud SQL: Blue (`bg-blue-50`, `text-blue-700`)
- VPC/Networking: Gray (`bg-gray-50`, `text-gray-700`, `border-gray-200`)
- Firewall: Orange (`bg-orange-50`, `text-orange-700`, `border-orange-200`)
- Load Balancer: Yellow (`bg-yellow-50`, `text-yellow-700`, `border-yellow-200`)
- Pub/Sub: Blue (`bg-blue-50`, `text-blue-700`)
- BigQuery: Blue (`bg-blue-50`, `text-blue-700`)

**Health Status Colors:**
- Healthy: Green border-left (`border-l-4 border-l-green-500`)
- Warning: Yellow border-left (`border-l-4 border-l-yellow-500`)
- Critical: Red border-left (`border-l-4 border-l-red-500`)
- Unknown: Gray border-left (`border-l-4 border-l-gray-300`)

### 4. Icons and Visual Elements

**Icon Library:**
Use `lucide-react` icons with GCP-specific mappings:

```typescript
const getGCPIcon = (resourceType: string) => {
  const iconMap: Record<string, React.ComponentType> = {
    'google_compute_instance': Server,  // or Cpu icon
    'google_storage_bucket': Database,  // or HardDrive
    'google_container_cluster': Layers,  // or Container icon
    'google_compute_network': Network,   // or Globe
    'google_compute_firewall': Shield,
    'google_cloud_functions_function': Zap,
    'google_sql_database_instance': Database,
    'google_compute_disk': HardDrive,
    'google_compute_address': MapPin,
    'google_compute_forwarding_rule': Activity,
    'google_pubsub_topic': MessageSquare,
    'google_pubsub_subscription': MessageCircle,
    'google_bigquery_dataset': BarChart3,
    'google_cloud_run_service': Container,
    'google_app_engine_application': Cloud,
  };
  return iconMap[resourceType] || Cloud;
};
```

**Visual Indicators:**
- Health status: Colored dot (green/yellow/red/gray)
- Status: Badge with text (Running, Stopped, etc.)
- Connections: Small icon with count badge
- Cost: Dollar sign icon + amount
- Zone: Location pin icon + zone name

### 5. Zone/Region Grouping

**Grouping Strategy:**

1. **Primary Grouping: By Region**
   - Group resources by region first
   - Show region as collapsible section header
   - Region header shows: name, resource count, total cost

2. **Secondary Grouping: By Zone (within region)**
   - For zonal resources, group by zone
   - Show zone as sub-header within region
   - Zone header shows: zone name, resource count

3. **Global Resources**
   - Resources without zone (global) shown at top
   - Labeled as "Global Resources"

**UI Implementation:**
```typescript
// Group resources
const groupedResources = useMemo(() => {
  const groups: Record<string, Record<string, GCPService[]>> = {};
  
  architecture.resources.forEach(resource => {
    const region = resource.region || 'global';
    const zone = resource.zone || 'global';
    
    if (!groups[region]) groups[region] = {};
    if (!groups[region][zone]) groups[region][zone] = [];
    
    groups[region][zone].push(resource);
  });
  
  return groups;
}, [architecture.resources]);
```

**Zone/Region Headers:**
- Collapsible (click to expand/collapse)
- Show resource count badge
- Show total cost for zone/region
- Color-coded by health status (if any resources unhealthy)

### 6. Network Topology Visualization

**Topology View Features:**

1. **Graph Layout:**
   - Use a force-directed graph or hierarchical layout
   - Nodes = Resources
   - Edges = Connections
   - Group by network/VPC

2. **Visual Elements:**
   - Network boundaries (VPCs) as containers/backgrounds
   - Resource nodes with icons
   - Connection lines with arrows showing direction
   - Connection type indicators (different line styles/colors)

3. **Interaction:**
   - Click node to select resource
   - Hover to highlight connections
   - Zoom and pan
   - Toggle connection types (network/storage/data)

4. **Toggle:**
   - Button to switch between "Grid View" and "Topology View"
   - Topology view shows relationships visually
   - Grid view shows organized cards

**Implementation Libraries:**
- Consider `react-flow` or `vis-network` for graph visualization
- Or custom SVG-based rendering

### 7. Inspector Panel

**Panel Tabs:**

1. **Details Tab:**
   - Resource name and type
   - Project, Region, Zone
   - Self-link (clickable to GCP Console)
   - Description
   - Configuration (key-value pairs, formatted)
   - Labels (as badges)
   - Created/Updated timestamps

2. **Metrics Tab:**
   - Real-time metrics display
   - Charts/graphs for CPU, Memory, Network
   - Time range selector (1h, 6h, 24h, 7d)
   - Metric cards with current values
   - Trend indicators (up/down arrows)

3. **Cost Tab:**
   - Monthly cost estimate
   - Cost breakdown by component
   - Cost trend chart (if historical data)
   - Optimization recommendations
   - Link to GCP Billing Console

4. **Security Tab:**
   - IAM permissions summary
   - Firewall rules affecting resource
   - Encryption status
   - Security recommendations
   - Compliance status

5. **Connections Tab:**
   - List of connected resources
   - Connection types and protocols
   - Visual connection diagram
   - Click to navigate to connected resource

**Panel Actions:**
- "View in GCP Console" button (opens resource in new tab)
- "Export Configuration" button (downloads Terraform config)
- "Refresh Metrics" button
- Close button (X)

### 8. Application Stacks

**Stack Detection:**
- Group resources by labels (e.g., `app`, `environment`, `team`)
- Or by network/VPC
- Or by user-defined grouping

**Stack Display:**
- Stack header with name, description
- Health status indicator
- Total cost for stack
- Resource count
- Tags/labels as badges
- Collapsible stack (show/hide resources)

**Stack Card:**
```typescript
interface StackCardProps {
  stack: GCPApplicationStack;
  onStackClick: (stack: GCPApplicationStack) => void;
  onServiceClick: (service: GCPService) => void;
}
```

### 9. Error Handling

**Error States:**

1. **No GCP Access:**
   - Show empty state with message
   - "Connect to GCP" button
   - Instructions for authentication

2. **Discovery Errors:**
   - Show error banner at top
   - List failed resource types
   - Retry button
   - Partial data display (show what was discovered)

3. **API Errors:**
   - Show error for specific resource
   - Fallback to cached data if available
   - Error icon on affected resources

4. **Network Errors:**
   - Show offline indicator
   - Disable refresh button
   - Show last known state

**Error UI Components:**
```typescript
// Error Banner
<div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
  <div className="flex items-center">
    <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
    <div>
      <p className="font-medium text-red-800">Discovery Error</p>
      <p className="text-sm text-red-700">{errorMessage}</p>
    </div>
    <button onClick={retry} className="ml-auto">Retry</button>
  </div>
</div>
```

### 10. Data Access Patterns

**API Integration:**

```typescript
// API Service
class GCPArchitectureAPI {
  async getArchitecture(
    project: string,
    regions?: string[]
  ): Promise<GCPArchitecture> {
    const params = new URLSearchParams({
      project,
      ...(regions && { regions: regions.join(',') })
    });
    
    const response = await fetch(`/api/gcp/architecture?${params}`);
    if (!response.ok) throw new Error('Failed to fetch architecture');
    return response.json();
  }
  
  async refreshArchitecture(
    project: string
  ): Promise<GCPArchitecture> {
    const response = await fetch(`/api/gcp/architecture/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project })
    });
    return response.json();
  }
  
  async getResourceMetrics(
    resourceId: string,
    timeRange: string
  ): Promise<ResourceMetrics> {
    // Fetch metrics for specific resource
  }
}
```

**Data Fetching Hook:**

```typescript
function useGCPArchitecture(project: string, regions?: string[]) {
  const [architecture, setArchitecture] = useState<GCPArchitecture | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    // Fetch architecture data
  }, [project, regions]);
  
  const refresh = async () => {
    // Refresh data
  };
  
  return { architecture, loading, error, refresh };
}
```

### 11. GCP Console Integration

**Console Links:**

For each resource, generate GCP Console URL:

```typescript
function getGCPConsoleLink(resource: GCPService): string {
  const baseUrl = 'https://console.cloud.google.com';
  const project = resource.project;
  
  const linkMap: Record<string, (r: GCPService) => string> = {
    'google_compute_instance': (r) => 
      `${baseUrl}/compute/instancesDetail/zones/${r.zone}/instances/${r.name}?project=${project}`,
    'google_storage_bucket': (r) =>
      `${baseUrl}/storage/browser/${r.name}?project=${project}`,
    'google_container_cluster': (r) =>
      `${baseUrl}/kubernetes/clusters/details/${r.zone || r.region}/${r.name}?project=${project}`,
    'google_compute_network': (r) =>
      `${baseUrl}/networking/networks/details/${r.name}?project=${project}`,
    'google_cloud_functions_function': (r) =>
      `${baseUrl}/functions/details/${r.region}/${r.name}?project=${project}`,
    // ... more mappings
  };
  
  const linkBuilder = linkMap[resource.type];
  return linkBuilder ? linkBuilder(resource) : `${baseUrl}/home/dashboard?project=${project}`;
}
```

**Console Actions:**
- "View in GCP Console" button in inspector panel
- Right-click context menu on resource cards
- Link icon on resource cards (hover to show)

### 12. Performance Optimizations

**Optimization Strategies:**

1. **Virtual Scrolling:**
   - Use `react-window` or `react-virtualized` for large resource lists
   - Only render visible resource cards

2. **Lazy Loading:**
   - Load metrics on-demand (when tab opened)
   - Load connection details on hover/click

3. **Memoization:**
   - Memoize grouped resources
   - Memoize filtered resources
   - Memoize expensive calculations

4. **Debouncing:**
   - Debounce search/filter inputs
   - Debounce refresh requests

5. **Caching:**
   - Cache architecture data
   - Cache metrics with TTL
   - Use React Query or SWR for data fetching

### 13. Responsive Design

**Breakpoints:**
- Mobile (< 640px): Single column, stacked layout
- Tablet (640px - 1024px): 2 columns for resource grid
- Desktop (> 1024px): Full layout with inspector panel

**Mobile Adaptations:**
- Collapsible inspector panel (bottom sheet)
- Simplified resource cards
- Stacked zone/region groups
- Touch-friendly interactions

### 14. Accessibility

**Accessibility Features:**
- ARIA labels for all interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader announcements for state changes
- Color contrast compliance (WCAG AA)
- Alt text for icons

### 15. Testing Requirements

**Test Coverage:**
- Unit tests for data transformation functions
- Component tests for UI components
- Integration tests for API calls
- E2E tests for user workflows

**Test Scenarios:**
- Resource discovery and display
- Zone/region grouping
- Network topology rendering
- Inspector panel interactions
- Error handling
- Console link generation
- Cost calculations

## Implementation Checklist

### Backend
- [ ] Create `gcp_discovery_service.py`
- [ ] Implement VivifyRT integration
- [ ] Add GCP API clients (Monitoring, Billing, Compute)
- [ ] Implement relationship detection
- [ ] Create API endpoint `/api/gcp/architecture`
- [ ] Add error handling and logging
- [ ] Add caching layer
- [ ] Add authentication/authorization

### Frontend
- [ ] Create `types/gcp.ts` with all interfaces
- [ ] Create `GCPArchitectureDashboard.tsx` component
- [ ] Implement resource card component
- [ ] Implement zone/region grouping
- [ ] Implement network topology view
- [ ] Implement inspector panel with all tabs
- [ ] Implement GCP Console link generation
- [ ] Add error handling UI
- [ ] Add loading states
- [ ] Add responsive design
- [ ] Add accessibility features
- [ ] Add unit tests
- [ ] Add integration tests

### Integration
- [ ] Connect backend API to frontend
- [ ] Test end-to-end flow
- [ ] Performance testing
- [ ] Security review
- [ ] Documentation

## Example Data Structure

```json
{
  "project": "my-gcp-project",
  "lastRefresh": "2025-01-27T10:30:00Z",
  "hasGCPAccess": true,
  "regions": ["us-central1", "us-east1"],
  "zones": {
    "us-central1-a": [
      {
        "id": "instance-1",
        "name": "web-server-1",
        "type": "google_compute_instance",
        "status": "running",
        "region": "us-central1",
        "zone": "us-central1-a",
        "project": "my-gcp-project",
        "healthStatus": "healthy",
        "selfLink": "https://www.googleapis.com/compute/v1/projects/my-gcp-project/zones/us-central1-a/instances/web-server-1",
        "costEstimate": {
          "monthly": 67.32,
          "breakdown": "n1-standard-2 on-demand pricing"
        },
        "metrics": {
          "cpu": 23,
          "memory": 45,
          "networkIn": 1250000,
          "networkOut": 2100000
        },
        "configuration": {
          "machineType": "n1-standard-2",
          "bootDisk": "projects/my-gcp-project/zones/us-central1-a/disks/web-server-1",
          "networkInterfaces": [
            {
              "network": "projects/my-gcp-project/global/networks/default",
              "subnetwork": "projects/my-gcp-project/regions/us-central1/subnetworks/default"
            }
          ]
        },
        "labels": {
          "app": "web",
          "environment": "production"
        },
        "connections": ["network-default", "disk-web-server-1"]
      }
    ]
  },
  "resources": [...],
  "connections": [
    {
      "id": "instance-to-network",
      "from": "instance-1",
      "to": "network-default",
      "type": "network",
      "description": "Instance connected to VPC network"
    }
  ],
  "applicationStacks": [
    {
      "id": "web-production",
      "name": "Web Production Stack",
      "description": "Production web application infrastructure",
      "services": [...],
      "totalCost": 234.50,
      "healthStatus": "healthy",
      "labels": {
        "app": "web",
        "environment": "production"
      }
    }
  ],
  "totalCost": 1234.56
}
```

## Additional Features (Future Enhancements)

1. **Resource Filtering:**
   - Filter by type, status, health, zone, labels
   - Search by name
   - Cost range filter

2. **Bulk Actions:**
   - Select multiple resources
   - Bulk operations (stop, start, delete)
   - Export selected resources as Terraform

3. **Cost Analysis:**
   - Cost trends over time
   - Cost by service type
   - Cost optimization recommendations
   - Budget alerts

4. **Monitoring Integration:**
   - Real-time metrics dashboard
   - Alert configuration
   - Custom metric queries

5. **Export/Import:**
   - Export architecture as JSON
   - Export as Terraform configuration
   - Import from existing Terraform state

6. **Collaboration:**
   - Share architecture views
   - Comments on resources
   - Change history

## Notes

- Use GCP brand colors consistently
- Follow GCP Console UI patterns where applicable
- Ensure all GCP Console links are accurate and functional
- Handle GCP-specific concepts (zones, regions, projects, labels)
- Support both zonal and regional resources
- Handle global resources appropriately
- Consider GCP quotas and limits in UI
- Show GCP service status if available
- Integrate with GCP IAM for permission checks

