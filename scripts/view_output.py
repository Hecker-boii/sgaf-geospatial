#!/usr/bin/env python3
"""
View and verify JSON output files from the geospatial analysis pipeline.
Usage:
    python3 scripts/view_output.py                    # List all datasets
    python3 scripts/view_output.py <dataset-id>       # View specific manifest
    python3 scripts/view_output.py --verify <dataset-id>  # Verify correctness
"""

import boto3
import json
import sys
import argparse
from typing import Dict, Any, List, Tuple


def get_bucket_name(stack_name: str = "SgafStack") -> str:
    """Get output bucket name from CloudFormation stack."""
    cf = boto3.client('cloudformation')
    try:
        stack = cf.describe_stacks(StackName=stack_name)
        outputs = {o['OutputKey']: o['OutputValue'] 
                   for o in stack['Stacks'][0]['Outputs']}
        return outputs.get('OutputBucketName', '')
    except Exception as e:
        print(f"Error getting bucket name: {e}", file=sys.stderr)
        sys.exit(1)


def list_datasets(bucket: str) -> List[str]:
    """List all dataset IDs in the output bucket."""
    s3 = boto3.client('s3')
    try:
        objects = s3.list_objects_v2(Bucket=bucket, Delimiter='/')
        datasets = [p['Prefix'].rstrip('/') 
                   for p in objects.get('CommonPrefixes', [])]
        return sorted(datasets)
    except Exception as e:
        print(f"Error listing datasets: {e}", file=sys.stderr)
        return []


def get_manifest(bucket: str, dataset_id: str) -> Dict[str, Any]:
    """Download and parse manifest.json for a dataset."""
    s3 = boto3.client('s3')
    key = f"{dataset_id}/manifest.json"
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj['Body'].read().decode('utf-8'))
    except s3.exceptions.NoSuchKey:
        print(f"Error: Manifest not found for dataset '{dataset_id}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading manifest: {e}", file=sys.stderr)
        sys.exit(1)


def verify_manifest(manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Verify manifest structure and correctness."""
    errors = []
    warnings = []
    
    # Check required fields
    if 'tiles' not in manifest:
        errors.append("Missing 'tiles' field")
    if 'ok' not in manifest:
        errors.append("Missing 'ok' field")
    if 'total_area' not in manifest:
        errors.append("Missing 'total_area' field")
    
    if errors:
        return False, errors
    
    # Check tiles structure
    tiles = manifest['tiles']
    if not isinstance(tiles, list):
        errors.append("'tiles' must be a list")
        return False, errors
    
    if len(tiles) != 3:
        warnings.append(f"Expected 3 tiles, found {len(tiles)}")
    
    # Verify each tile
    expected_total = 0.0
    for i, tile_data in enumerate(tiles):
        if not isinstance(tile_data, dict):
            errors.append(f"Tile {i} is not an object")
            continue
        
        if 'tile' not in tile_data:
            errors.append(f"Tile {i} missing 'tile' field")
        if 'area' not in tile_data:
            errors.append(f"Tile {i} missing 'area' field")
        if 'status' not in tile_data:
            errors.append(f"Tile {i} missing 'status' field")
        
        if tile_data.get('status') != 'ok':
            errors.append(f"Tile {tile_data.get('tile', i)} has status '{tile_data.get('status')}', expected 'ok'")
        
        # Calculate expected area for verification
        tile_num = tile_data.get('tile', i)
        base = 0.001 * (tile_num + 1)
        expected_area = 0.001 * 0.001  # (base + 0.001 - base) * (base + 0.001 - base)
        actual_area = tile_data.get('area', 0)
        
        if abs(actual_area - expected_area) > 0.0000001:
            warnings.append(f"Tile {tile_num}: area {actual_area} doesn't match expected {expected_area}")
        
        expected_total += expected_area
    
    # Verify total area
    actual_total = manifest.get('total_area', 0)
    if abs(actual_total - expected_total) > 0.0000001:
        warnings.append(f"Total area {actual_total} doesn't match expected {expected_total}")
    
    # Verify ok status
    if manifest.get('ok') != all(t.get('status') == 'ok' for t in tiles):
        errors.append("'ok' field doesn't match actual tile statuses")
    
    return len(errors) == 0, errors + warnings


def print_manifest(manifest: Dict[str, Any], pretty: bool = True):
    """Print manifest in a readable format."""
    if pretty:
        print(json.dumps(manifest, indent=2))
    else:
        print(json.dumps(manifest))


def main():
    parser = argparse.ArgumentParser(
        description='View and verify JSON output files from geospatial analysis pipeline'
    )
    parser.add_argument('dataset_id', nargs='?', help='Dataset ID to view')
    parser.add_argument('--verify', action='store_true', 
                       help='Verify correctness of manifest')
    parser.add_argument('--stack', default='SgafStack',
                       help='CloudFormation stack name (default: SgafStack)')
    parser.add_argument('--compact', action='store_true',
                       help='Output compact JSON (no pretty printing)')
    
    args = parser.parse_args()
    
    bucket = get_bucket_name(args.stack)
    if not bucket:
        print("Error: Could not find output bucket", file=sys.stderr)
        sys.exit(1)
    
    if not args.dataset_id:
        # List all datasets
        datasets = list_datasets(bucket)
        if not datasets:
            print("No datasets found in output bucket")
            return
        
        print("Available datasets:")
        for ds in datasets:
            print(f"  - {ds}")
        print(f"\nUse: python3 {sys.argv[0]} <dataset-id> to view a manifest")
        return
    
    # Get manifest
    manifest = get_manifest(bucket, args.dataset_id)
    
    if args.verify:
        # Verify correctness
        is_valid, issues = verify_manifest(manifest)
        if is_valid:
            print("✓ Manifest is valid")
            print(f"  - Tiles: {len(manifest['tiles'])}")
            print(f"  - All OK: {manifest['ok']}")
            print(f"  - Total area: {manifest['total_area']}")
            if issues:
                print("\nWarnings:")
                for issue in issues:
                    print(f"  ⚠ {issue}")
        else:
            print("✗ Manifest validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
    else:
        # Just view
        print(f"Manifest for dataset: {args.dataset_id}")
        print("=" * 50)
        print_manifest(manifest, pretty=not args.compact)


if __name__ == '__main__':
    main()

