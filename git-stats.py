#!/usr/bin/env python3
import os
import subprocess
import argparse
import re
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import yaml
import sys

def find_git_repos(root_dir):
    """Recursively find git repositories under the given root directory."""
    git_repos = []

    for root, dirs, files in os.walk(root_dir):
        if '.git' in dirs:
            git_repos.append(os.path.abspath(root))
            # Don't parse .git directories
            dirs.remove('.git')

        # And skip hidden directories...
        dirs[:] = [d for d in dirs if not d.startswith('.')]

    return git_repos

def get_git_stats(repo_path, author, exclude_patterns=None, since=None, ignore_commits=None):
    """Get git stats for a specific repository."""
    if exclude_patterns is None:
        exclude_patterns = []
    if ignore_commits is None:
        ignore_commits = []

    os.chdir(repo_path)

    # First, process the ignored commits to get a list of files and their changes to exclude
    ignored_changes = {}
    for commit_hash in ignore_commits:
        try:
            # Get the file changes for this commit
            ignored_cmd = ['git', 'show', '--numstat', '--pretty=format:', commit_hash]
            ignored_result = subprocess.run(ignored_cmd, capture_output=True, text=True)

            if ignored_result.returncode != 0:
                # Probably don't need this warning... since we try to "ignore" commits across all repos
                print(f"Warning: Could not process ignored commit {commit_hash}. It might not exist in this repository.")
                continue

            ignored_output = ignored_result.stdout.strip()

            for line in ignored_output.split('\n'):
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) != 3:
                    continue

                added, removed, file_path = parts

                # Skip binary files
                if added == "-" or removed == "-":
                    continue

                # Store these changes to subtract later
                if file_path not in ignored_changes:
                    ignored_changes[file_path] = {'added': 0, 'removed': 0}

                ignored_changes[file_path]['added'] += int(added)
                ignored_changes[file_path]['removed'] += int(removed)

        except Exception as e:
            print(f"Warning: Error processing ignored commit {commit_hash}: {e}")

    # Count the total number of commits by this author
    # Build the git log command for counting commits
    commit_count_cmd = f"git log --author=\"{author}\" --oneline"
    if since:
        commit_count_cmd += f" --since={since}"

    try:
        print(f"  Counting commits using command: {commit_count_cmd}")
        # Use shell=True to properly handle author names with special characters
        commit_count_result = subprocess.run(commit_count_cmd, shell=True, capture_output=True, text=True, check=True)
        commit_lines = commit_count_result.stdout.strip().split('\n') if commit_count_result.stdout.strip() else []
        commit_count = len(commit_lines)
        print(f"  Found {commit_count} commits by author '{author}'")
    except subprocess.CalledProcessError as e:
        commit_count = 0
        print(f"  Warning: Error counting commits in {repo_path}: {e}")

    cmd = ['git', 'log', f'--author={author}', '--numstat', '--pretty=format:"%ad"', '--date=short']

    if since:
        cmd.append(f'--since={since}')

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout

    lines = output.strip().split('\n')
    stats = {'added': 0, 'removed': 0, 'total': 0, 'commits': commit_count}
    date_stats = {}

    current_date = None
    for line in lines:
        if line.startswith('"') and line.endswith('"'):
            # This is a date line!
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

        # Subtract changes from ignored commits for this file
        if file_path in ignored_changes:
            added_count -= ignored_changes[file_path]['added']
            removed_count -= ignored_changes[file_path]['removed']

            # Ensure we don't go negative, although this shouldn't happen
            added_count = max(0, added_count)
            removed_count = max(0, removed_count)

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

def generate_chart(repo_stats, output_file=None, author=None):
    """Generate a chart of repository statistics."""
    # Filter out repos with zero contributions (stuff I might have checked out but didn't contribute to)
    repo_stats = {repo: stats for repo, stats in repo_stats.items()
                 if stats['added'] > 0 or stats['removed'] > 0}

    # If no repos with contributions remain, return early
    if not repo_stats:
        print("No repositories with contributions to display.")
        return

    repo_names = list(repo_stats.keys())
    added = [repo_stats[repo]['added'] for repo in repo_names]
    removed = [-repo_stats[repo]['removed'] for repo in repo_names]  # Negative on the chart y axis

    # Sort repositories by total changes (absolute value of added + removed)
    sorted_indices = np.argsort([abs(a + r) for a, r in zip(added, removed)])[::-1]
    repo_names = [repo_names[i] for i in sorted_indices]
    added = [added[i] for i in sorted_indices]
    removed = [removed[i] for i in sorted_indices]

    # Calculate totals
    total_added = sum(added)
    total_removed = abs(sum(removed))
    net_change = total_added + sum(removed)  # Sum is correct because removed is negative
    repo_count = len(repo_stats)
    total_commits = sum(repo_stats[repo]['commits'] for repo in repo_names)

    # Create the chart with a 1920x1080 resolution (convert pixels to inches with 100 DPI)
    fig, ax = plt.subplots(figsize=(19.2, 10.8))

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
    title = 'Git Contribution Statistics by Repository'
    if author:
        title = f'Git Contribution Statistics for {author}'
    ax.set_title(title)
    ax.set_xticks([r + bar_width/2 for r in range(len(repo_names))])
    ax.set_xticklabels(repo_names, rotation=45, ha='right')

    ax.legend()

    # Add totals as text
    plt.figtext(0.02, 0.02, f'Total Added: {total_added:,} | Total Removed: {total_removed:,} | Net Change: {net_change:,} | Repositories: {repo_count} | Commits: {total_commits:,}',
                fontsize=10, bbox=dict(facecolor='lightgray', alpha=0.5))

    plt.tight_layout()

    # Save or display the chart -- note that display will not work in a WSL2 environment
    if output_file:
        plt.savefig(output_file, dpi=100)
        print(f"Chart saved to {output_file}")
    else:
        plt.show()

def load_config(config_file):
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        if 'repos' not in config and 'root_dir' not in config:
            print("Error: Either 'repos' or 'root_dir' field is required in the config file.")
            sys.exit(1)
        if 'author' not in config:
            print("Error: 'author' field is required in the config file.")
            sys.exit(1)

        # Some defaults for optional fields :)
        if 'exclude_patterns' not in config:
            config['exclude_patterns'] = ['composer.lock', 'package-lock.json', '^vendor/', '^node_modules/']
        if 'since' not in config:
            config['since'] = None
        if 'output_file' not in config:
            config['output_file'] = None
        if 'csv_file' not in config:
            config['csv_file'] = None
        if 'ignore_commits' not in config:
            config['ignore_commits'] = []
        if 'repos' not in config:
            config['repos'] = []

        return config
    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found.")
        sys.exit(1)
    except yaml.YAMLError:
        print(f"Error: Config file '{config_file}' is not valid YAML.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Calculate git contribution statistics across multiple repositories.')
    parser.add_argument('--config', default='git-stats-config.yaml', help='Path to YAML configuration file')
    parser.add_argument('repos', nargs='*', help='List of repository directories to analyze (overrides config file)')
    parser.add_argument('--author', help='Author name or email to filter commits (overrides config file)')
    parser.add_argument('--exclude', nargs='+', help='Patterns for files/directories to exclude (overrides config file)')
    parser.add_argument('--since', help='Only consider commits more recent than this date (overrides config file)')
    parser.add_argument('--output', help='Save chart to this file instead of displaying it (overrides config file)')
    parser.add_argument('--csv', help='Export statistics to CSV file (overrides config file)')
    parser.add_argument('--ignore-commits', nargs='+', help='List of commit hashes to ignore (overrides config file)')
    parser.add_argument('--root-dir', help='Root directory to recursively search for git repositories (overrides config file)')

    args = parser.parse_args()

    config = load_config(args.config)

    # Command-line arguments override config file
    root_dir = args.root_dir if args.root_dir else config.get('root_dir')
    repos = args.repos if args.repos else config['repos']
    authorStr = args.author if args.author else config['author']
    exclude_patterns = args.exclude if args.exclude else config['exclude_patterns']
    since = args.since if args.since else config['since']
    output_file = args.output if args.output else config['output_file']
    csv_file = args.csv if args.csv else config['csv_file']
    ignore_commits = args.ignore_commits if args.ignore_commits else config['ignore_commits']


    if not csv_file:
        print(f"Error: CSV file not specified. Use --csv to specify a file.")
        return

    dirname = os.path.dirname(csv_file)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
        print(f"Created directory {dirname} for CSV file.")
    
    # If root_dir is specified, find all git repositories under it
    if root_dir:
        print(f"Finding git repositories under {root_dir}...")
        found_repos = find_git_repos(root_dir)
        print(f"Found {len(found_repos)} git repositories.")
        repos.extend(found_repos)
        # Remove duplicates while preserving order
        repos = list(dict.fromkeys(repos))

    # Validate repository paths
    valid_repos = []
    for repo_path in repos:
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

    if ',' in authorStr: 
        authors = [a.strip() for a in authorStr.split(',')]
    else:
        authors = [authorStr.strip()]

    with open(csv_file, 'w') as f:
        f.write("Author,Repository,Lines Added,Lines Removed,Net Change,Commits\n")
        for author in authors:
            for repo_path in valid_repos:
                repo_name = os.path.basename(repo_path)
                print(f"Processing {repo_name}...")

                try:
                    stats, date_stats = get_git_stats(repo_path, author, exclude_patterns, since, ignore_commits)
                    # Only add repositories with actual contributions
                    if stats['added'] > 0 or stats['removed'] > 0:
                        all_repos_stats[repo_name] = stats

                        # Display per-repository stats
                        print(f"  Lines added: {stats['added']:,}")
                        print(f"  Lines removed: {stats['removed']:,}")
                        print(f"  Net change: {stats['total']:,}")
                        print(f"  Commits: {stats['commits']:,}")
                        print()
                    else:
                        print(f"  No contributions found. Omitting from results.")
                        print()

                except Exception as e:
                    print(f"Error processing {repo_name}: {e}")
                finally:
                    os.chdir(original_dir)

            if all_repos_stats:
                for repo, stats in all_repos_stats.items():
                    f.write(f"{author},{repo},{stats['added']},{stats['removed']},{stats['total']},{stats   ['commits']}    \n")

                # Add total row
                total_added = sum(stats['added'] for stats in all_repos_stats.values())
                total_removed = sum(stats['removed'] for stats in all_repos_stats.values())
                total_net = sum(stats['total'] for stats in all_repos_stats.values())
                total_commits = sum(stats['commits'] for stats in all_repos_stats.values())
        
        total_change= total_added + total_removed
        f.write(f"TOTAL,TOTAL ADDED, TOTAL REMOVED, TOTAL NET(added-removed), TOTAL CHANGE(added+removed), TOTALL COMMITS\n")
        f.write(f"TOTAL,{total_added},{total_removed},{total_net},{total_change},{total_commits}\n")
        print(f"CSV export saved to {csv_file}")

    # Generate and display/save chart
    if all_repos_stats:
        generate_chart(all_repos_stats, output_file, author)

        # Print overall totals
        total_added = sum(stats['added'] for stats in all_repos_stats.values())
        total_removed = sum(stats['removed'] for stats in all_repos_stats.values())
        total_net = sum(stats['total'] for stats in all_repos_stats.values())
        total_commits = sum(stats['commits'] for stats in all_repos_stats.values())

        print("Overall Statistics:")
        print(f"Total lines added: {total_added:,}")
        print(f"Total lines removed: {total_removed:,}")
        print(f"Total net change: {total_net:,}")
        print(f"Total commits: {total_commits:,}")
    else:
        print("No statistics collected.")

if __name__ == "__main__":
    main()