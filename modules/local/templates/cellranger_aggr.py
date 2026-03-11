#!/usr/bin/env python3

import os
import csv
import subprocess
import sys
import shutil


def create_aggr_config():
    """
    Create the aggregation CSV config file for cellranger aggr.
    The config requires: sample_id, molecule_h5
    """

    config_file = "aggr_config.csv"

    # Get list of molecule_info.h5 files
    molecule_h5_files = [f for f in os.listdir('.') if f.endswith('molecule_info.h5')]

    if not molecule_h5_files:
        print(
            "ERROR: No molecule_info.h5 files found in current directory", file=sys.stderr)
        sys.exit(1)

    # Create CSV config
    with open(config_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['sample_id', 'molecule_h5'])

        # Write each sample
        for h5_file in sorted(molecule_h5_files):
            # Extract sample name from filename
            # Assuming format: sample_name_molecule_info.h5 or just use the filename without extension
            sample_name = h5_file.replace('_molecule_info.h5', '').replace('.h5', '')
            writer.writerow([sample_name, os.path.abspath(h5_file)])

    print(f"Created aggregation config: {config_file}")
    return config_file


def copy_logs_to_prefix(prefix):
    """
    Copy files in {prefix}/ starting with _ to {prefix}/logs/ if any exist.
    Equivalent to: cp {prefix}/_* {prefix}/logs/
    """
    logs_dir = os.path.join(prefix, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    files_copied = []
    prefix_dir = prefix
    for fname in os.listdir(prefix_dir):
        if fname.startswith("_"):
            fpath = os.path.join(prefix_dir, fname)
            if os.path.isfile(fpath):
                dest = os.path.join(logs_dir, fname)
                shutil.copy2(fpath, dest)
                files_copied.append(dest)
    print(f"Copied log files to {logs_dir}: {files_copied}")


def copy_versions_yml_to_prefix(prefix):
    """
    Copy versions.yml to {prefix}/.
    Equivalent to: cp versions.yml {prefix}/
    """
    os.makedirs(prefix, exist_ok=True)
    shutil.copy2("versions.yml", os.path.join(prefix, "versions.yml"))
    print(f"Copied versions.yml to {prefix}/versions.yml")


def run_cellranger_aggr():
    """
    Execute cellranger aggr with the generated config
    """

    # Get template variables (set by Nextflow)
    prefix = "${prefix}"
    norm_mode = "${norm_mode}"
    args_str = "${args}"
    
    # Create the config file
    config_file = create_aggr_config()

    # Build cellranger aggr command
    cmd = [
        'cellranger', 'aggr',
        f'--id={prefix}',
        f'--csv={config_file}',
        f'--normalize={norm_mode}'
    ]

    # Add any additional arguments
    if args_str and args_str.strip():
        args_list = args_str.strip().split()
        cmd.extend(args_list)

    print(f"Running command: {' '.join(cmd)}")

    # Execute command
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(
            f"ERROR: cellranger aggr failed with exit code {e.returncode}", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    # Copy {prefix}_* files to {prefix}/logs/, if any exist
    copy_logs_to_prefix(prefix)


def generate_versions():
    """
    Generate versions.yml file
    """
    try:
        result = subprocess.run(['cellranger', '--version'],
                                capture_output=True, text=True, check=True)
        version_output = result.stdout + result.stderr

        # Extract version number
        import re
        version_match = re.search(
            'cellranger[^0-9]*([0-9]+\\.[0-9]+\\.[0-9]+)', version_output)
        version = version_match.group(1) if version_match else "unknown"

        with open('versions.yml', 'w') as f:
            f.write(f'"${{task.process}}":\\n')
            f.write(f'    cellranger: {version}\\n')

    except Exception as e:
        print(
            f"WARNING: Could not generate versions file: {e}", file=sys.stderr)


if __name__ == "__main__":
    run_cellranger_aggr()
    generate_versions()
    # Copy versions.yml into prefix/ after generating
    prefix = "${prefix}"
    copy_versions_yml_to_prefix(prefix)
