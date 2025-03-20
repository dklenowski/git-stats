#!/usr/bin/env python3
import os
import subprocess
import argparse
import re
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def get_git_stats(repo_path, author, exclude_patterns=None, since=None):
    """Get git stats for a specific repository."""
    if exclude_patterns is None:
        exclude_patterns = []

    # Change to the repository directory
    os.chdir(repo_path)

    # Construct the git log command
    cmd = ['git', 'log', f'--author={author}', '--numstat', '--pretty=format:"%ad"', '--date=short']

    # Add date filter if specified
    if since:
        cmd.append(f'--since={since}')

    # Execute the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout

    # Process the output
    lines = output.strip().split('\n')
    stats = {'added': 0, 'removed': 0, 'total': 0}
    date_stats = {}

    current_date = None
    for line in lines:
        if line.startswith('"') and line.endswith('"'):
            # This is a date line
            current_date = line.strip('"')
            if current_date not in date_stats:
                date_stats[current_date] = {'added': 0, 'removed': 0, 'total': 0}
            continue

        # Skip empty lines
        if not line:
            continue

        # Parse stat lines (format: <added> <removed> <file>)
        parts = line.split('\t')
        if len(parts) != 3:
            continue

        added, removed, file_path = parts

        # Skip binary files (marked with "-")
        if added == "-" or removed == "-":
            continue

        # Check if the file should be excluded
        if any(re.search(pattern, file_path) for pattern in exclude_patterns):
            continue

        added_count = int(added)
        removed_count = int(removed)

        # Update overall stats
        stats['added'] += added_count
        stats['removed'] += removed_count
        stats['total'] += added_count - removed_count

        # Update date-based stats if we have a current date
        if current_date:
            date_stats[current_date]['added'] += added_count
            date_stats[current_date]['removed'] += removed_count
            date_stats[current_date]['total'] += added_count - removed_count

    return stats, date_stats

def generate_chart(repo_stats, output_file=None):
    """Generate a chart of repository statistics."""
    repo_names = list(repo_stats.keys())
    added = [repo_stats[repo]['added'] for repo in repo_names]
    removed = [-repo_stats[repo]['removed'] for repo in repo_names]  # Negative for visualization

    # Sort repositories by total changes (absolute value of added + removed)
    sorted_indices = np.argsort([abs(a + r) for a, r in zip(added, removed)])[::-1]
    repo_names = [repo_names[i] for i in sorted_indices]
    added = [added[i] for i in sorted_indices]
    removed = [removed[i] for i in sorted_indices]

    # Calculate totals
    total_added = sum(added)
    total_removed = abs(sum(removed))
    net_change = total_added + sum(removed)  # Sum is correct because removed is negative

    # Create the chart
    fig, ax = plt.subplots(figsize=(12, 8))

    # Set the width of the bars
    bar_width = 0.35

    # Set position of bar on X axis
    r1 = np.arange(len(repo_names))
    r2 = [x + bar_width for x in r1]

    # Make the plot
    ax.bar(r1, added, color='green', width=bar_width, label='Lines Added')
    ax.bar(r2, removed, color='red', width=bar_width, label='Lines Removed')

    # Add labels and title
    ax.set_xlabel('Repository')
    ax.set_ylabel('Lines of Code')
    ax.set_title('Git Contribution Statistics by Repository')
    ax.set_xticks([r + bar_width/2 for r in range(len(repo_names))])
    ax.set_xticklabels(repo_names, rotation=45, ha='right')

    # Add a legend
    ax.legend()

    # Add totals as text
    plt.figtext(0.02, 0.02, f'Total Added: {total_added:,} | Total Removed: {total_removed:,} | Net Change: {net_change:,}',
                fontsize=10, bbox=dict(facecolor='lightgray', alpha=0.5))

    # Adjust layout
    plt.tight_layout()

    # Save or display the chart
    if output_file:
        plt.savefig(output_file)
        print(f"Chart saved to {output_file}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Calculate git contribution statistics across multiple repositories.')
    parser.add_argument('repos', nargs='+', help='List of repository directories to analyze')
    parser.add_argument('--author', required=True, help='Author name or email to filter commits')
    parser.add_argument('--exclude', nargs='+', default=['composer.lock', 'package-lock.json', '^vendor/', '^node_modules/'],
                        help='Patterns for files/directories to exclude (regex supported)')
    parser.add_argument('--since', help='Only consider commits more recent than this date (e.g., "1 month ago", "2023-01-01")')
    parser.add_argument('--output', help='Save chart to this file instead of displaying it')
    parser.add_argument('--csv', help='Export statistics to CSV file')

    args = parser.parse_args()

    # Validate repository paths
    valid_repos = []
    for repo_path in args.repos:
        abs_path = os.path.abspath(repo_path)
        if not os.path.exists(os.path.join(abs_path, '.git')):
            print(f"Warning: {repo_path} does not appear to be a git repository. Skipping.")
            continue
        valid_repos.append(abs_path)

    if not valid_repos:
        print("Error: No valid git repositories provided.")
        return

    # Process each repository
    all_repos_stats = {}
    original_dir = os.getcwd()

    for repo_path in valid_repos:
        repo_name = os.path.basename(repo_path)
        print(f"Processing {repo_name}...")

        try:
            stats, date_stats = get_git_stats(repo_path, args.author, args.exclude, args.since)
            all_repos_stats[repo_name] = stats

            # Display per-repository stats
            print(f"  Lines added: {stats['added']:,}")
            print(f"  Lines removed: {stats['removed']:,}")
            print(f"  Net change: {stats['total']:,}")
            print()

        except Exception as e:
            print(f"Error processing {repo_name}: {e}")
        finally:
            # Return to the original directory
            os.chdir(original_dir)

    # Export to CSV if requested
    if args.csv and all_repos_stats:
        try:
            with open(args.csv, 'w') as f:
                f.write("Repository,Lines Added,Lines Removed,Net Change\n")
                for repo, stats in all_repos_stats.items():
                    f.write(f"{repo},{stats['added']},{stats['removed']},{stats['total']}\n")

                # Add total row
                total_added = sum(stats['added'] for stats in all_repos_stats.values())
                total_removed = sum(stats['removed'] for stats in all_repos_stats.values())
                total_net = sum(stats['total'] for stats in all_repos_stats.values())
                f.write(f"TOTAL,{total_added},{total_removed},{total_net}\n")

            print(f"CSV export saved to {args.csv}")
        except Exception as e:
            print(f"Error exporting to CSV: {e}")

    # Generate and display/save chart
    if all_repos_stats:
        generate_chart(all_repos_stats, args.output)

        # Print overall totals
        total_added = sum(stats['added'] for stats in all_repos_stats.values())
        total_removed = sum(stats['removed'] for stats in all_repos_stats.values())
        total_net = sum(stats['total'] for stats in all_repos_stats.values())

        print("Overall Statistics:")
        print(f"Total lines added: {total_added:,}")
        print(f"Total lines removed: {total_removed:,}")
        print(f"Total net change: {total_net:,}")
    else:
        print("No statistics collected.")

if __name__ == "__main__":
    main()