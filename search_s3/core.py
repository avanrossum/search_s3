#!/usr/bin/env python3
import sys, argparse, os, csv, re

try:  # pragma: no cover - handled in tests when boto3 missing
    import boto3
    from botocore.config import Config
except ModuleNotFoundError:  # pragma: no cover
    boto3 = None
    Config = None

s3 = None
term = root_dir = raw_output = stacked_output = csv_output = csv_file = None
term_excluding = bucket_excluding = regex_mode = None

def parse_arguments():
    parser = argparse.ArgumentParser(description='Search S3 objects for a term')
    parser.add_argument('term', nargs='?', help='Search term or regex pattern (case-sensitive)')
    parser.add_argument('bucket_prefix', nargs='?', help='Bucket inclusion pattern or regex (optional, searches all if not provided)')
    parser.add_argument('-t', '--term', dest='term_flag', help='Search term or regex pattern (case-sensitive)')
    parser.add_argument('-b', '--bucket', dest='bucket_flag', help='Bucket inclusion pattern or regex (optional, searches all if not provided)')
    parser.add_argument('-te', '--term-excluding', dest='term_excluding', help='Exclude objects with keys matching this term or regex')
    parser.add_argument('-be', '--bucket-excluding', dest='bucket_excluding', help='Exclude buckets matching this term or regex')
    parser.add_argument('--regex', action='store_true', help='Treat all patterns as regex (case-sensitive)')
    parser.add_argument('--regex-ignore-case', action='store_true', help='Treat all patterns as regex (case-insensitive)')
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
    
    # Determine regex mode
    regex_mode = 'case_sensitive' if args.regex else ('case_insensitive' if args.regex_ignore_case else 'literal')
    
    return term, bucket_prefix, args.raw, args.stacked, args.csv, args.csv_file, args.term_excluding, args.bucket_excluding, regex_mode

def get_buckets():
    resp = s3.list_buckets()
    buckets = []
    
    # Compile patterns for bucket filtering
    bucket_include_pattern = compile_pattern(root_dir, regex_mode)
    bucket_exclude_pattern = compile_pattern(bucket_excluding, regex_mode)
    
    for b in resp.get("Buckets", []):
        bucket_name = b["Name"]
        
        # Apply bucket inclusion filter
        if bucket_include_pattern and not matches_pattern(bucket_name, bucket_include_pattern, regex_mode):
            continue
            
        # Apply bucket exclusion filter
        if bucket_exclude_pattern and matches_pattern(bucket_name, bucket_exclude_pattern, regex_mode):
            continue
            
        buckets.append(bucket_name)
    
    return buckets

def compile_pattern(pattern, mode):
    """Compile a pattern based on the regex mode"""
    if not pattern:
        return None
    
    if mode == 'literal':
        return pattern
    elif mode == 'case_sensitive':
        return re.compile(pattern)
    elif mode == 'case_insensitive':
        return re.compile(pattern, re.IGNORECASE)
    return pattern

def matches_pattern(text, pattern, mode):
    """Check if text matches the pattern based on regex mode"""
    if not pattern:
        return False
    
    if mode == 'literal':
        return pattern in text
    elif mode in ['case_sensitive', 'case_insensitive']:
        return pattern.search(text) is not None
    return False

def should_exclude_object(key):
    """Check if object should be excluded based on term_excluding"""
    if term_excluding:
        # Compile the exclusion pattern
        exclusion_pattern = compile_pattern(term_excluding, regex_mode)
        return matches_pattern(key, exclusion_pattern, regex_mode)
    return False

def list_hits_contains(bucket, substr):
    p = s3.get_paginator("list_objects_v2")
    
    # Compile the search pattern
    search_pattern = compile_pattern(substr, regex_mode)
    
    for page in p.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if matches_pattern(key, search_pattern, regex_mode) and not should_exclude_object(key):
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



def main():
    global term, root_dir, raw_output, stacked_output, csv_output, csv_file
    global term_excluding, bucket_excluding, regex_mode, s3
    term, root_dir, raw_output, stacked_output, csv_output, csv_file, term_excluding, bucket_excluding, regex_mode = parse_arguments()
    if boto3 is None or Config is None:
        raise ImportError("boto3 is required to run this script")
    session = boto3.Session()
    s3 = session.client("s3", config=Config(retries={"max_attempts": 10, "mode": "standard"}))

    buckets = get_buckets()

    if raw_output:
        # Raw output - stream as found
        print("Bucket	Key	Size	LastModified	StorageClass")
        for b in buckets:
            for r in list_hits_contains(b, term):
                size = format_size(r['Size'])
                print(f"{r['Bucket']}	{r['Key']}	{size}	{r['LastModified']}	{r['StorageClass']}")
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
                print()
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


if __name__ == "__main__":
    main()
