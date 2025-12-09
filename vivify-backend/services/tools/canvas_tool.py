"""
Canvas Query Tool - Access GCP Architecture data
"""

from langchain.tools import BaseTool
from typing import Optional
import json


def get_architecture_from_cache():
    """Get architecture data from the GCP discovery cache"""
    try:
        from api.routes.gcp import architecture_cache
        # Return the first (and usually only) cached architecture
        if architecture_cache:
            # Get the most recently cached project
            project_id = list(architecture_cache.keys())[-1]
            arch = architecture_cache[project_id]
            # Convert Pydantic model to dict if needed
            if hasattr(arch, 'dict'):
                return arch.dict()
            return arch
        return None
    except Exception as e:
        print(f"Error getting architecture from cache: {e}")
        return None


class CanvasTool(BaseTool):
    name: str = "canvas_query"
    description: str = """
    Query GCP resources from the Live Architecture Canvas. This tool provides access to discovered GCP infrastructure.
    
    Operations:
    - list: List all resources (optional filter by type, region)
    - get: Get details of a specific resource by ID or name
    - cost: Get cost analysis and breakdown
    - summary: Get architecture summary (project, regions, total resources, cost)
    - types: List all resource types discovered
    
    Input should be a JSON string with 'operation' and relevant parameters.
    
    Examples:
    - List all resources: {"operation": "list"}
    - List storage buckets: {"operation": "list", "type": "google_storage_bucket"}
    - List resources in region: {"operation": "list", "region": "us-central1"}
    - Get resource details: {"operation": "get", "resource_id": "bucket-app1-vivify"}
    - Get cost analysis: {"operation": "cost"}
    - Get summary: {"operation": "summary"}
    - List resource types: {"operation": "types"}
    """
    
    def __init__(self):
        super().__init__()
        object.__setattr__(self, '_cache', {})  # Will be populated by the discovery service
    
    def set_architecture_data(self, architecture: dict):
        """Set the architecture data from GCP discovery"""
        object.__setattr__(self, '_cache', architecture)
    
    def _run(self, query: str) -> str:
        """Execute canvas query"""
        cache = getattr(self, '_cache', {})
        
        # If internal cache is empty, try to get from GCP discovery cache
        if not cache or not cache.get("resources"):
            cache = get_architecture_from_cache()
            if cache:
                # Update internal cache
                object.__setattr__(self, '_cache', cache)
                print(f"✅ Loaded architecture from GCP cache: {len(cache.get('resources', []))} resources")
        
        try:
            params = json.loads(query)
            operation = params.get("operation")
            
            # Check if we have data
            if not cache or not cache.get("resources"):
                return "No architecture data available. Please scan your GCP project first by going to the 'Live Architecture Canvas' tab and clicking 'Discover Resources'."
            
            resources = cache.get("resources", [])
            
            if operation == "list":
                resource_type = params.get("type")
                region = params.get("region")
                
                filtered = resources
                
                if resource_type:
                    filtered = [r for r in filtered if r.get("type") == resource_type]
                if region:
                    filtered = [r for r in filtered if r.get("region") == region]
                
                if not filtered:
                    filters = []
                    if resource_type:
                        filters.append(f"type={resource_type}")
                    if region:
                        filters.append(f"region={region}")
                    filter_str = " with " + ", ".join(filters) if filters else ""
                    return f"No resources found{filter_str}."
                
                result = []
                for r in filtered:
                    result.append({
                        "id": r.get("id"),
                        "name": r.get("name"),
                        "type": r.get("type"),
                        "region": r.get("region"),
                        "status": r.get("status"),
                        "cost": r.get("cost_estimate", {}).get("monthly", 0) if r.get("cost_estimate") else 0
                    })
                
                return json.dumps(result, indent=2)
            
            elif operation == "get":
                resource_id = params.get("resource_id")
                
                if not resource_id:
                    return "Error: 'resource_id' is required."
                
                # Find by ID or name
                resource = next(
                    (r for r in resources if r.get("id") == resource_id or r.get("name") == resource_id),
                    None
                )
                
                if not resource:
                    return f"Resource '{resource_id}' not found."
                
                return json.dumps(resource, indent=2)
            
            elif operation == "cost":
                total_cost = cache.get("total_cost", 0)
                cost_breakdown = cache.get("cost_breakdown", {})
                
                # Calculate cost by resource type
                type_costs = {}
                for r in resources:
                    rtype = r.get("type", "unknown")
                    cost = r.get("cost_estimate", {}).get("monthly", 0) if r.get("cost_estimate") else 0
                    type_costs[rtype] = type_costs.get(rtype, 0) + cost
                
                result = {
                    "total_monthly_cost": total_cost,
                    "cost_by_type": type_costs,
                    "cost_breakdown": cost_breakdown
                }
                
                return json.dumps(result, indent=2)
            
            elif operation == "summary":
                resource_types = {}
                for r in resources:
                    rtype = r.get("type", "unknown")
                    resource_types[rtype] = resource_types.get(rtype, 0) + 1
                
                summary = {
                    "project": cache.get("project"),
                    "total_resources": len(resources),
                    "resource_types": resource_types,
                    "regions": cache.get("regions", []),
                    "total_cost": cache.get("total_cost", 0),
                    "last_refresh": cache.get("lastRefresh")
                }
                
                return json.dumps(summary, indent=2)
            
            elif operation == "types":
                resource_types = {}
                for r in resources:
                    rtype = r.get("type", "unknown")
                    resource_types[rtype] = resource_types.get(rtype, 0) + 1
                
                result = [
                    {"type": rtype, "count": count}
                    for rtype, count in sorted(resource_types.items(), key=lambda x: x[1], reverse=True)
                ]
                
                return json.dumps(result, indent=2)
            
            else:
                return f"Unknown operation: {operation}. Valid operations: list, get, cost, summary, types"
        
        except json.JSONDecodeError:
            return "Error: Invalid JSON input. Please provide a valid JSON string."
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version"""
        return self._run(query)


# Global instance
_canvas_tool = None

def get_canvas_tool() -> CanvasTool:
    """Get or create canvas tool instance"""
    global _canvas_tool
    if _canvas_tool is None:
        _canvas_tool = CanvasTool()
    return _canvas_tool
