"""
VivifyRT - Reverse Terraform Tool
Converts GCP resources to Terraform configuration using provider schemas

Dependencies:
    pip install python-terraform
"""

import json
import tempfile
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    from python_terraform import Terraform, IsFlagged
except ImportError:
    raise ImportError(
        "python-terraform library is required. Install it with: pip install python-terraform"
    )


class TerraformProviderError(Exception):
    """Custom exception for Terraform provider related errors"""
    pass


class GCPAPIError(Exception):
    """Custom exception for GCP API related errors"""
    pass


class SchemaError(Exception):
    """Custom exception for schema-related errors"""
    pass


def fetch_resource_state_via_terraform(resource_type: str, resource_id: str, 
                                       project: str, zone: Optional[str] = None,
                                       region: Optional[str] = None,
                                       credentials_path: Optional[str] = None) -> Dict[str, str]:
    """
    Use Terraform to fetch resource state from GCP and return flat attributes
    
    Args:
        resource_type: Terraform resource type (e.g., 'google_compute_instance')
        resource_id: Resource identifier/name
        project: GCP project ID
        zone: GCP zone (optional, for zonal resources)
        region: GCP region (optional, for regional resources)
        credentials_path: Path to service account JSON key file (optional)
                         If not provided, uses Application Default Credentials
    
    Returns:
        Flat key-value map of resource attributes
    
    Raises:
        GCPAPIError: If resource cannot be fetched from GCP
        TerraformProviderError: If Terraform operations fail
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="vivifyrt_")
        
        # Create Terraform configuration for import
        tf_config = _generate_import_config(resource_type, resource_id, project, zone, region, credentials_path)
        config_path = Path(temp_dir) / "main.tf"
        config_path.write_text(tf_config)
        
        # Initialize Terraform using python-terraform
        tf = Terraform(working_dir=temp_dir)
        
        # Run terraform init
        return_code, stdout, stderr = tf.init()
        if return_code != 0:
            raise TerraformProviderError(f"Terraform init failed: {stderr}")
        
        # Import resource into state
        resource_address = f"{resource_type}.imported"
        import_id = _build_import_id(resource_type, resource_id, project, zone, region)
        
        return_code, stdout, stderr = tf.import_cmd(
            resource_address,
            import_id,
            capture_output=True
        )
        
        if return_code != 0:
            raise GCPAPIError(f"Failed to import resource from GCP: {stderr}")
        
        # Read state file to get flat attributes
        state_path = Path(temp_dir) / "terraform.tfstate"
        if not state_path.exists():
            raise TerraformProviderError("State file not created after import")
        
        state_data = json.loads(state_path.read_text())
        flat_attributes = _extract_attributes_from_state(state_data, resource_type)
        
        return flat_attributes
    
    except json.JSONDecodeError as e:
        raise TerraformProviderError(f"Failed to parse Terraform state: {str(e)}")
    except (GCPAPIError, TerraformProviderError):
        raise
    except Exception as e:
        raise TerraformProviderError(f"Unexpected error during resource fetch: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def _generate_import_config(resource_type: str, resource_id: str, project: str,
                            zone: Optional[str], region: Optional[str], 
                            credentials_path: Optional[str] = None) -> str:
    """Generate minimal Terraform configuration for import"""
    config = f'''terraform {{
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

provider "google" {{
  project = "{project}"
'''
    if credentials_path:
        config += f'  credentials = "{credentials_path}"\n'
    if region:
        config += f'  region  = "{region}"\n'
    if zone:
        config += f'  zone    = "{zone}"\n'
    
    config += '}\n\n'
    config += f'resource "{resource_type}" "imported" {{\n}}\n'
    
    return config


def _build_import_id(resource_type: str, resource_id: str, project: str,
                     zone: Optional[str], region: Optional[str]) -> str:
    """Build the import ID based on resource type"""
    if resource_type == "google_compute_instance":
        if not zone:
            raise ValueError("Zone is required for google_compute_instance")
        return f"projects/{project}/zones/{zone}/instances/{resource_id}"
    elif resource_type == "google_compute_network":
        return f"projects/{project}/global/networks/{resource_id}"
    elif resource_type == "google_storage_bucket":
        return resource_id
    elif resource_type == "google_container_cluster":
        location = zone or region or "us-central1"
        return f"projects/{project}/locations/{location}/clusters/{resource_id}"
    else:
        return resource_id





def _extract_attributes_from_state(state_data: Dict[str, Any], resource_type: str) -> Dict[str, str]:
    """Extract flat attributes from Terraform state file"""
    resources = state_data.get("resources", [])
    for resource in resources:
        if resource.get("type") == resource_type:
            instances = resource.get("instances", [])
            if instances:
                attributes = instances[0].get("attributes", {})
                return _flatten_attributes(attributes)
    
    raise TerraformProviderError(f"Resource {resource_type} not found in state")


def _flatten_attributes(obj: Any, parent_key: str = "") -> Dict[str, str]:
    """
    Flatten nested dictionary/list structure into dot-notation keys
    
    Args:
        obj: Object to flatten (dict, list, or primitive)
        parent_key: Parent key prefix
    
    Returns:
        Flat dictionary with dot-notation keys
    """
    items = {}
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                items.update(_flatten_attributes(value, new_key))
            elif value is not None:
                items[new_key] = str(value)
    
    elif isinstance(obj, list):
        items[f"{parent_key}.#"] = str(len(obj))
        for idx, item in enumerate(obj):
            new_key = f"{parent_key}.{idx}"
            if isinstance(item, (dict, list)):
                items.update(_flatten_attributes(item, new_key))
            elif item is not None:
                items[new_key] = str(item)
    
    else:
        if obj is not None:
            items[parent_key] = str(obj)
    
    return items


def get_provider_schema(resource_type: str) -> Dict[str, Any]:
    """
    Get Terraform provider schema for a resource type
    
    Args:
        resource_type: Terraform resource type
    
    Returns:
        Schema definition dictionary
    
    Raises:
        SchemaError: If schema cannot be retrieved
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="vivifyrt_schema_")
        
        # Create minimal config to initialize provider
        config = '''terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {}
'''
        config_path = Path(temp_dir) / "main.tf"
        config_path.write_text(config)
        
        # Initialize Terraform using python-terraform
        tf = Terraform(working_dir=temp_dir)
        
        return_code, stdout, stderr = tf.init()
        if return_code != 0:
            raise SchemaError(f"Terraform init failed: {stderr}")
        
        # Get provider schema using cmd method
        return_code, stdout, stderr = tf.cmd(
            "providers",
            "schema",
            "-json",
            capture_output=True
        )
        
        if return_code != 0:
            raise SchemaError(f"Failed to retrieve provider schema: {stderr}")
        
        schema_data = json.loads(stdout)
        
        # Extract schema for specific resource type
        provider_schemas = schema_data.get("provider_schemas", {})
        for provider_name, provider_data in provider_schemas.items():
            if "google" in provider_name:
                resource_schemas = provider_data.get("resource_schemas", {})
                if resource_type in resource_schemas:
                    return resource_schemas[resource_type]
        
        raise SchemaError(f"Schema not found for resource type: {resource_type}")
    
    except json.JSONDecodeError as e:
        raise SchemaError(f"Failed to parse schema JSON: {str(e)}")
    except SchemaError:
        raise
    except Exception as e:
        raise SchemaError(f"Unexpected error retrieving schema: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def unflatten_attributes(flat_attrs: Dict[str, str], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert flat dot-notation attributes to nested structure using schema
    
    Args:
        flat_attrs: Flat attribute dictionary
        schema: Provider schema for the resource
    
    Returns:
        Nested attribute dictionary
    """
    result = {}
    
    # Group attributes by top-level key
    grouped = {}
    for key, value in flat_attrs.items():
        parts = key.split(".")
        top_key = parts[0]
        if top_key not in grouped:
            grouped[top_key] = {}
        grouped[top_key][key] = value
    
    # Process each top-level attribute
    block_schema = schema.get("block", {})
    attributes_schema = block_schema.get("attributes", {})
    block_types_schema = block_schema.get("block_types", {})
    
    for top_key, attrs in grouped.items():
        if top_key in attributes_schema:
            # Simple attribute
            attr_schema = attributes_schema[top_key]
            result[top_key] = _reconstruct_attribute(attrs, top_key, attr_schema)
        elif top_key in block_types_schema:
            # Block type (nested structure)
            block_schema_def = block_types_schema[top_key]
            result[top_key] = _reconstruct_block(attrs, top_key, block_schema_def)
        else:
            # Unknown attribute, keep as-is
            if top_key in flat_attrs:
                result[top_key] = flat_attrs[top_key]
    
    return result


def _reconstruct_attribute(attrs: Dict[str, str], prefix: str, attr_schema: Dict[str, Any]) -> Any:
    """Reconstruct a single attribute based on its schema"""
    attr_type = attr_schema.get("type")
    
    if isinstance(attr_type, str):
        if attr_type == "string":
            return attrs.get(prefix, "")
        elif attr_type == "number":
            value = attrs.get(prefix, "0")
            return float(value) if "." in value else int(value)
        elif attr_type == "bool":
            return attrs.get(prefix, "false").lower() == "true"
    
    elif isinstance(attr_type, list):
        type_def = attr_type[0]
        if type_def == "list":
            return _reconstruct_list(attrs, prefix, attr_type)
        elif type_def == "map":
            return _reconstruct_map(attrs, prefix)
        elif type_def == "set":
            return _reconstruct_list(attrs, prefix, attr_type)
    
    return attrs.get(prefix)


def _reconstruct_list(attrs: Dict[str, str], prefix: str, type_def: List) -> List[Any]:
    """Reconstruct a list from flat attributes"""
    count_key = f"{prefix}.#"
    count = int(attrs.get(count_key, 0))
    
    result = []
    for i in range(count):
        item_prefix = f"{prefix}.{i}"
        
        # Check if list contains objects or primitives
        if len(type_def) > 1 and isinstance(type_def[1], list) and type_def[1][0] == "object":
            # List of objects
            item = _reconstruct_object(attrs, item_prefix, type_def[1][1])
            result.append(item)
        else:
            # List of primitives
            if item_prefix in attrs:
                result.append(attrs[item_prefix])
    
    return result


def _reconstruct_map(attrs: Dict[str, str], prefix: str) -> Dict[str, Any]:
    """Reconstruct a map from flat attributes"""
    result = {}
    prefix_with_dot = f"{prefix}."
    
    for key, value in attrs.items():
        if key.startswith(prefix_with_dot) and key != f"{prefix}.%":
            map_key = key[len(prefix_with_dot):]
            if "." not in map_key:  # Only direct children
                result[map_key] = value
    
    return result


def _reconstruct_object(attrs: Dict[str, str], prefix: str, obj_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Reconstruct an object from flat attributes"""
    result = {}
    
    for field_name, field_type in obj_schema.items():
        field_key = f"{prefix}.{field_name}"
        
        if isinstance(field_type, str):
            if field_key in attrs:
                result[field_name] = attrs[field_key]
        elif isinstance(field_type, list):
            if field_type[0] == "list":
                result[field_name] = _reconstruct_list(attrs, field_key, field_type)
            elif field_type[0] == "map":
                result[field_name] = _reconstruct_map(attrs, field_key)
    
    return result


def _reconstruct_block(attrs: Dict[str, str], prefix: str, block_schema: Dict[str, Any]) -> Any:
    """Reconstruct a block (nested structure) from flat attributes"""
    nesting_mode = block_schema.get("nesting_mode", "single")
    block_def = block_schema.get("block", {})
    
    if nesting_mode == "list" or nesting_mode == "set":
        count_key = f"{prefix}.#"
        count = int(attrs.get(count_key, 0))
        
        result = []
        for i in range(count):
            item_prefix = f"{prefix}.{i}"
            item = _reconstruct_block_item(attrs, item_prefix, block_def)
            if item:
                result.append(item)
        return result
    
    elif nesting_mode == "single":
        return _reconstruct_block_item(attrs, prefix, block_def)
    
    elif nesting_mode == "map":
        return _reconstruct_map(attrs, prefix)
    
    return {}


def _reconstruct_block_item(attrs: Dict[str, str], prefix: str, block_def: Dict[str, Any]) -> Dict[str, Any]:
    """Reconstruct a single block item"""
    result = {}
    
    # Process attributes
    attributes = block_def.get("attributes", {})
    for attr_name, attr_schema in attributes.items():
        attr_key = f"{prefix}.{attr_name}"
        value = _reconstruct_attribute({attr_key: attrs.get(attr_key, "")}, attr_key, attr_schema)
        if value or value == 0 or value is False:
            result[attr_name] = value
    
    # Process nested blocks
    block_types = block_def.get("block_types", {})
    for block_name, nested_block_schema in block_types.items():
        block_key = f"{prefix}.{block_name}"
        nested_value = _reconstruct_block(attrs, block_key, nested_block_schema)
        if nested_value:
            result[block_name] = nested_value
    
    return result


def generate_hcl(resource_type: str, resource_name: str, attributes: Dict[str, Any]) -> str:
    """
    Generate HCL code from nested attributes
    
    Args:
        resource_type: Terraform resource type
        resource_name: Resource name for the configuration
        attributes: Nested attribute dictionary
    
    Returns:
        HCL formatted string
    """
    sanitized_name = _sanitize_resource_name(resource_name)
    
    hcl_lines = [f'resource "{resource_type}" "{sanitized_name}" {{']
    hcl_lines.extend(_generate_hcl_body(attributes, indent=1))
    hcl_lines.append('}')
    
    return '\n'.join(hcl_lines)


def _sanitize_resource_name(name: str) -> str:
    """Sanitize resource name for Terraform (alphanumeric, dash, underscore only)"""
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', lambda m: f'-{ord(m.group(0)):04X}-', name)
    return f"tfer--{sanitized}"


def _generate_hcl_body(obj: Any, indent: int = 0) -> List[str]:
    """Generate HCL body lines from nested structure"""
    lines = []
    indent_str = "  " * indent
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                # Nested block
                lines.append(f"{indent_str}{key} {{")
                lines.extend(_generate_hcl_body(value, indent + 1))
                lines.append(f"{indent_str}}}")
            elif isinstance(value, list):
                # List of blocks or values
                if value and isinstance(value[0], dict):
                    # List of blocks
                    for item in value:
                        lines.append(f"{indent_str}{key} {{")
                        lines.extend(_generate_hcl_body(item, indent + 1))
                        lines.append(f"{indent_str}}}")
                else:
                    # List of primitives
                    formatted_list = json.dumps(value)
                    lines.append(f"{indent_str}{key} = {formatted_list}")
            else:
                # Simple attribute
                formatted_value = _format_hcl_value(value)
                lines.append(f"{indent_str}{key} = {formatted_value}")
    
    return lines


def _format_hcl_value(value: Any) -> str:
    """Format a value for HCL output"""
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Escape quotes and newlines
        escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    elif value is None:
        return "null"
    else:
        return json.dumps(value)


def VivifyRT(resource_type: str, resource_id: str, project: str,
             zone: Optional[str] = None, region: Optional[str] = None,
             credentials_path: Optional[str] = None) -> str:
    """
    Main function: Convert GCP resource to Terraform HCL configuration
    
    This function:
    1. Fetches resource from GCP via Terraform provider
    2. Gets flat key-value attributes
    3. Retrieves provider schema
    4. Converts flat attributes to nested structure
    5. Generates HCL code
    
    Args:
        resource_type: Terraform resource type (e.g., 'google_compute_instance')
        resource_id: Resource identifier/name in GCP
        project: GCP project ID
        zone: GCP zone (optional, for zonal resources)
        region: GCP region (optional, for regional resources)
        credentials_path: Path to service account JSON key file (optional)
                         If not provided, uses Application Default Credentials
    
    Returns:
        HCL formatted Terraform configuration
    
    Raises:
        GCPAPIError: If resource cannot be fetched from GCP
        TerraformProviderError: If Terraform operations fail
        SchemaError: If provider schema cannot be retrieved
    
    Authentication:
        Credentials are passed to the Terraform Google Cloud Provider, which supports:
        1. Application Default Credentials (gcloud auth application-default login)
        2. Service Account Key File (via credentials_path parameter)
        3. GOOGLE_APPLICATION_CREDENTIALS environment variable
        4. GOOGLE_CREDENTIALS environment variable
        5. Compute Engine metadata server (when running on GCP)
    
    Example:
        >>> # Using Application Default Credentials (most common)
        >>> hcl = VivifyRT(
        ...     resource_type="google_compute_instance",
        ...     resource_id="my-instance",
        ...     project="my-project",
        ...     zone="us-central1-a"
        ... )
        >>> print(hcl)
        
        >>> # Using explicit service account key
        >>> hcl = VivifyRT(
        ...     resource_type="google_compute_instance",
        ...     resource_id="my-instance",
        ...     project="my-project",
        ...     zone="us-central1-a",
        ...     credentials_path="/path/to/service-account-key.json"
        ... )
        >>> print(hcl)
    """
    try:
        # Step 1: Fetch resource state from GCP (flat format)
        flat_attributes = fetch_resource_state_via_terraform(
            resource_type=resource_type,
            resource_id=resource_id,
            project=project,
            zone=zone,
            region=region,
            credentials_path=credentials_path
        )
        
        if not flat_attributes:
            raise GCPAPIError(f"No attributes returned for resource {resource_id}")
        
        # Step 2: Get provider schema
        schema = get_provider_schema(resource_type)
        
        if not schema:
            raise SchemaError(f"Could not retrieve schema for {resource_type}")
        
        # Step 3: Convert flat attributes to nested structure
        nested_attributes = unflatten_attributes(flat_attributes, schema)
        
        if not nested_attributes:
            raise TerraformProviderError("Failed to convert attributes to nested structure")
        
        # Step 4: Generate HCL code
        hcl_code = generate_hcl(resource_type, resource_id, nested_attributes)
        
        return hcl_code
    
    except (GCPAPIError, TerraformProviderError, SchemaError) as e:
        # Re-raise known exceptions
        raise
    except Exception as e:
        # Wrap unexpected exceptions
        raise TerraformProviderError(f"Unexpected error in VivifyRT: {str(e)}")
