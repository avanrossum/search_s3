#!/usr/bin/env python3
import boto3, sys, argparse, os, csv
from botocore.config import Config

def parse_arguments():
    parser = argparse.ArgumentParser(description='Search S3 objects for a term')
    parser.add_argument('term', nargs='?', help='Substring to match (case-sensitive)')
    parser.add_argument('bucket_prefix', nargs='?', help='Bucket prefix to filter buckets (optional, searches all if not provided)')
    parser.add_argument('-t', '--term', dest='term_flag', help='Substring to match (case-sensitive)')
    parser.add_argument('-b', '--bucket', dest='bucket_flag', help='Bucket prefix to filter buckets (optional, searches all if not provided)')
    parser.add_argument('--raw', action='store_true', help='Output raw data (full bucket names and keys) for copy-paste')
    parser.add_argument('--stacked', action='store_true', help='Output in stacked format (one object per section)')
    parser.add_argument('--csv', action='store_true', help='Output in CSV format')
    parser.add_argument('--csv-file', dest='csv_file', help='Output CSV to specified file (use with --csv)')
    
    args = parser.parse_args()
    
    # Determine the search term (positional or flag)
    term = args.term_flag or args.term
    if not term:
        parser.error("Search term is required. Use positional argument or --term/-t flag.")
    
    # Determine the bucket prefix (positional or flag)
    bucket_prefix = args.bucket_flag or args.bucket_prefix
    
    return term, bucket_prefix, args.raw, args.stacked, args.csv, args.csv_file

term, root_dir, raw_output, stacked_output, csv_output, csv_file = parse_arguments()
session = boto3.Session()
s3 = session.client("s3", config=Config(retries={"max_attempts": 10, "mode": "standard"}))

def get_buckets():
    resp = s3.list_buckets()
    if root_dir:
        # Filter buckets by contains if provided
        return [b["Name"] for b in resp.get("Buckets", []) if root_dir in b["Name"]]
    else:
        # Return all buckets if no prefix provided
        return [b["Name"] for b in resp.get("Buckets", [])]

def list_hits_contains(bucket, substr):
    p = s3.get_paginator("list_objects_v2")
    for page in p.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if substr in key:
                yield {
                    "Bucket": bucket,
                    "Key": key,
                    "Size": obj["Size"],
                    "LastModified": obj["LastModified"].isoformat(),
                    "StorageClass": obj.get("StorageClass", "STANDARD"),
                }

def list_hits_prefix(bucket, prefix):
    p = s3.get_paginator("list_objects_v2")
    for page in p.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            yield {
                "Bucket": bucket,
                "Key": obj["Key"],
                "Size": obj["Size"],
                "LastModified": obj["LastModified"].isoformat(),
                "StorageClass": obj.get("StorageClass", "STANDARD"),
            }

def list_versions(bucket, key_prefix):
    # If versioning was enabled, this finds older/deleted object versions under the prefix
    p = s3.get_paginator("list_object_versions")
    try:
        for page in p.paginate(Bucket=bucket, Prefix=key_prefix):
            for v in page.get("Versions", []) + page.get("DeleteMarkers", []):
                yield v
    except s3.exceptions.NoSuchBucket:
        return

def format_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}PB"

def truncate_text(text, max_length):
    """Truncate text and add ellipsis if too long"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def get_terminal_width():
    """Get terminal width, default to 120 if can't determine"""
    try:
        return os.get_terminal_size().columns
    except:
        return 120

def display_results(results, raw_output=False, stacked_output=False):
    """Display results in a flexible, readable format"""
    if not results:
        print("No results found.")
        return
    
    if raw_output:
        # Raw output for copy-paste - tab separated with full data
        print("Bucket\tKey\tSize\tLastModified\tStorageClass")
        for r in results:
            size = format_size(r['Size'])
            print(f"{r['Bucket']}\t{r['Key']}\t{size}\t{r['LastModified']}\t{r['StorageClass']}")
        return
    
    if stacked_output:
        # Stacked output - one object per section with clear formatting
        for i, r in enumerate(results, 1):
            print(f"=== Object {i} ===")
            print(f"Bucket:     {r['Bucket']}")
            print(f"Key:        {r['Key']}")
            print(f"Size:       {format_size(r['Size'])}")
            print(f"Modified:   {r['LastModified']}")
            print(f"Class:      {r['StorageClass']}")
            print()  # Empty line between objects
        return
    
    # Table format (default) - no truncation, full data
    # Get terminal width and calculate column widths
    term_width = get_terminal_width()
    
    # Calculate dynamic column widths based on content and terminal width
    bucket_width = min(50, max(20, min(len(max([r['Bucket'] for r in results], key=len)), 50)))
    key_width = min(term_width - bucket_width - 35, max(30, min(len(max([r['Key'] for r in results], key=len)), term_width - bucket_width - 35)))
    
    # Print header
    print(f"{'Bucket':<{bucket_width}} {'Key':<{key_width}} {'Size':<10} {'Modified':<25} {'Class':<15}")
    print("-" * term_width)
    
    # Print results - no truncation
    for r in results:
        size = format_size(r['Size'])
        modified = r['LastModified'][:25]  # Keep some timezone info but limit length
        print(f"{r['Bucket']:<{bucket_width}} {r['Key']:<{key_width}} {size:<10} {modified:<25} {r['StorageClass']:<15}")

buckets = get_buckets()

if raw_output:
    # Raw output - stream as found
    print("Bucket\tKey\tSize\tLastModified\tStorageClass")
    for b in buckets:
        for r in list_hits_contains(b, term):
            size = format_size(r['Size'])
            print(f"{r['Bucket']}\t{r['Key']}\t{size}\t{r['LastModified']}\t{r['StorageClass']}")

elif stacked_output:
    # Stacked output - stream as found
    object_count = 0
    for b in buckets:
        for r in list_hits_contains(b, term):
            object_count += 1
            print(f"=== Object {object_count} ===")
            print(f"Bucket:     {r['Bucket']}")
            print(f"Key:        {r['Key']}")
            print(f"Size:       {format_size(r['Size'])}")
            print(f"Modified:   {r['LastModified']}")
            print(f"Class:      {r['StorageClass']}")
            print()  # Empty line between objects

elif csv_output:
    # CSV output - stream as found
    if csv_file:
        # Write to specified file
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Bucket', 'Key', 'Size', 'LastModified', 'StorageClass'])
            for b in buckets:
                for r in list_hits_contains(b, term):
                    size = format_size(r['Size'])
                    writer.writerow([r['Bucket'], r['Key'], size, r['LastModified'], r['StorageClass']])
        print(f"Results saved to {csv_file}")
    else:
        # Write to stdout
        writer = csv.writer(sys.stdout)
        writer.writerow(['Bucket', 'Key', 'Size', 'LastModified', 'StorageClass'])
        for b in buckets:
            for r in list_hits_contains(b, term):
                size = format_size(r['Size'])
                writer.writerow([r['Bucket'], r['Key'], size, r['LastModified'], r['StorageClass']])

else:
    # Table format (default) - collect all results first for proper column sizing
    all_results = []
    for b in buckets:
        for r in list_hits_contains(b, term):
            all_results.append(r)

    # Display results
    display_results(all_results, raw_output, stacked_output)