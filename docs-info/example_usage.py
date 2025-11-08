#!/usr/bin/env python3
"""
Example usage of VivifyRT - Reverse Terraform Tool

This script demonstrates how to use VivifyRT to convert existing GCP resources
to Terraform configuration.

Prerequisites:
1. Install dependencies: pip install -r requirements.txt
2. Install Terraform CLI: https://www.terraform.io/downloads
3. Authenticate with GCP (choose one):
   - Application Default Credentials: gcloud auth application-default login
   - Service Account: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
   - Explicit path: Pass credentials_path parameter
4. Ensure the resource exists in your GCP project
"""

import os
from tools import VivifyRT, GCPAPIError, TerraformProviderError, SchemaError


def example_compute_instance():
    """Example: Import a GCP Compute Instance"""
    print("=" * 60)
    print("Example 1: Importing a GCP Compute Instance")
    print("=" * 60)
    
    try:
        hcl_code = VivifyRT(
            resource_type="google_compute_instance",
            resource_id="my-instance",  # Replace with your instance name
            project="my-gcp-project",   # Replace with your project ID
            zone="us-central1-a"        # Replace with your zone
        )
        
        print("\nGenerated Terraform Configuration:")
        print("-" * 60)
        print(hcl_code)
        print("-" * 60)
        
        # Optionally save to file
        with open("generated_instance.tf", "w") as f:
            f.write(hcl_code)
        print("\n✓ Configuration saved to: generated_instance.tf")
        
    except GCPAPIError as e:
        print(f"\n✗ GCP API Error: {e}")
        print("  Make sure the resource exists and you have proper permissions.")
    except TerraformProviderError as e:
        print(f"\n✗ Terraform Provider Error: {e}")
        print("  Make sure Terraform is installed and the provider is available.")
    except SchemaError as e:
        print(f"\n✗ Schema Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")


def example_storage_bucket():
    """Example: Import a GCS Bucket"""
    print("\n" + "=" * 60)
    print("Example 2: Importing a GCS Bucket")
    print("=" * 60)
    
    try:
        hcl_code = VivifyRT(
            resource_type="google_storage_bucket",
            resource_id="my-bucket-name",  # Replace with your bucket name
            project="my-gcp-project"       # Replace with your project ID
        )
        
        print("\nGenerated Terraform Configuration:")
        print("-" * 60)
        print(hcl_code)
        print("-" * 60)
        
        # Optionally save to file
        with open("generated_bucket.tf", "w") as f:
            f.write(hcl_code)
        print("\n✓ Configuration saved to: generated_bucket.tf")
        
    except GCPAPIError as e:
        print(f"\n✗ GCP API Error: {e}")
    except TerraformProviderError as e:
        print(f"\n✗ Terraform Provider Error: {e}")
    except SchemaError as e:
        print(f"\n✗ Schema Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")


def example_gke_cluster():
    """Example: Import a GKE Cluster"""
    print("\n" + "=" * 60)
    print("Example 3: Importing a GKE Cluster")
    print("=" * 60)
    
    try:
        hcl_code = VivifyRT(
            resource_type="google_container_cluster",
            resource_id="my-gke-cluster",  # Replace with your cluster name
            project="my-gcp-project",      # Replace with your project ID
            region="us-central1"           # Replace with your region
        )
        
        print("\nGenerated Terraform Configuration:")
        print("-" * 60)
        print(hcl_code)
        print("-" * 60)
        
        # Optionally save to file
        with open("generated_gke_cluster.tf", "w") as f:
            f.write(hcl_code)
        print("\n✓ Configuration saved to: generated_gke_cluster.tf")
        
    except GCPAPIError as e:
        print(f"\n✗ GCP API Error: {e}")
    except TerraformProviderError as e:
        print(f"\n✗ Terraform Provider Error: {e}")
    except SchemaError as e:
        print(f"\n✗ Schema Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")


def example_network():
    """Example: Import a VPC Network"""
    print("\n" + "=" * 60)
    print("Example 4: Importing a VPC Network")
    print("=" * 60)
    
    try:
        hcl_code = VivifyRT(
            resource_type="google_compute_network",
            resource_id="default",      # Replace with your network name
            project="my-gcp-project"    # Replace with your project ID
        )
        
        print("\nGenerated Terraform Configuration:")
        print("-" * 60)
        print(hcl_code)
        print("-" * 60)
        
        # Optionally save to file
        with open("generated_network.tf", "w") as f:
            f.write(hcl_code)
        print("\n✓ Configuration saved to: generated_network.tf")
        
    except GCPAPIError as e:
        print(f"\n✗ GCP API Error: {e}")
    except TerraformProviderError as e:
        print(f"\n✗ Terraform Provider Error: {e}")
    except SchemaError as e:
        print(f"\n✗ Schema Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")


def example_with_explicit_credentials():
    """Example: Using explicit service account credentials"""
    print("\n" + "=" * 60)
    print("Example 5: Using Explicit Credentials")
    print("=" * 60)
    
    credentials_path = "/path/to/service-account-key.json"
    
    # Check if file exists
    if not os.path.exists(credentials_path):
        print(f"\n⚠ Credentials file not found: {credentials_path}")
        print("  Update the path or use Application Default Credentials")
        return
    
    try:
        hcl_code = VivifyRT(
            resource_type="google_compute_instance",
            resource_id="my-instance",
            project="my-gcp-project",
            zone="us-central1-a",
            credentials_path=credentials_path  # Explicit credentials
        )
        
        print("\nGenerated Terraform Configuration:")
        print("-" * 60)
        print(hcl_code)
        print("-" * 60)
        
    except GCPAPIError as e:
        print(f"\n✗ GCP API Error: {e}")
    except TerraformProviderError as e:
        print(f"\n✗ Terraform Provider Error: {e}")
    except SchemaError as e:
        print(f"\n✗ Schema Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")


def check_authentication():
    """Check which authentication method is available"""
    print("\n" + "=" * 60)
    print("Checking Authentication Methods")
    print("=" * 60)
    
    # Check ADC
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if os.path.exists(adc_path):
        print("\n✓ Application Default Credentials found")
        print(f"  Location: {adc_path}")
    else:
        print("\n✗ Application Default Credentials not found")
        print("  Run: gcloud auth application-default login")
    
    # Check GOOGLE_APPLICATION_CREDENTIALS
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        print(f"\n✓ GOOGLE_APPLICATION_CREDENTIALS set")
        print(f"  Location: {creds_path}")
        if os.path.exists(creds_path):
            print("  ✓ File exists")
        else:
            print("  ✗ File not found!")
    else:
        print("\n✗ GOOGLE_APPLICATION_CREDENTIALS not set")
    
    # Check GOOGLE_CREDENTIALS
    if "GOOGLE_CREDENTIALS" in os.environ:
        print("\n✓ GOOGLE_CREDENTIALS environment variable set")
    else:
        print("\n✗ GOOGLE_CREDENTIALS not set")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("VivifyRT - Reverse Terraform Tool Examples")
    print("=" * 60)
    print("\nNOTE: Update the resource IDs and project names in this script")
    print("      before running the examples.\n")
    
    # Check authentication first
    check_authentication()
    
    print("\n" + "=" * 60)
    print("Uncomment the examples you want to run:")
    print("=" * 60)
    
    # Uncomment the examples you want to run:
    
    # example_compute_instance()
    # example_storage_bucket()
    # example_gke_cluster()
    # example_network()
    # example_with_explicit_credentials()
    
    print("\n" + "=" * 60)
    print("Edit this script to uncomment and run examples.")
    print("=" * 60)
