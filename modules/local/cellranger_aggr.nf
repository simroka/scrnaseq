process CELLRANGER_AGGR {
    label 'process_high'

    container "nf-core/cellranger:9.0.1"

    input:
    path(molecule_info_h5)
    val normalization_mode

    output:
    path("*/outs/**")                    , emit: folder_aggr_ch
    path("*/logs/**")                        , emit: logs_ch
    path "*/versions.yml"                , emit: versions_ch

    when:
    task.ext.when == null || task.ext.when

    script:
    // Exit if running this module with -profile conda / -profile mamba
    if (workflow.profile.tokenize(',').intersect(['conda', 'mamba']).size() >= 1) {
        error "CELLRANGER_AGGR module does not support Conda. Please use Docker / Singularity / Podman instead."
    }
    args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "aggregate"
    norm_mode = normalization_mode ?: 'mapped'
    
    template "cellranger_aggr.py"

    stub:
    // Exit if running this module with -profile conda / -profile mamba
    if (workflow.profile.tokenize(',').intersect(['conda', 'mamba']).size() >= 1) {
        error "CELLRANGER_AGGR module does not support Conda. Please use Docker / Singularity / Podman instead."
    }
    def prefix = task.ext.prefix ?: "aggregate"
    """
    mkdir -p "${prefix}/outs/"
    touch ${prefix}/outs/web_summary.html
    touch ${prefix}/outs/_finalstate
    touch aggr_config.csv

    cat <<-END_VERSIONS > versions.yml   
     "${task.process}":
        cellranger: \$(echo \$( cellranger --version 2>&1) | sed 's/^.*[^0-9]\\([0-9]*\\.[0-9]*\\.[0-9]*\\).*\$/\\1/' )
    END_VERSIONS
    """
}

process CELLRANGER_PREPARE_AGGR_INPUT {
    tag "$meta.id"
    label 'process_single'


    input:
    tuple val(meta), path(count_outs)

    output:
    path("*molecule_info.h5"), emit: molecule_info

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    # Find and copy molecule_info.h5 file(s) from the count/multi output.

    
    # Standard single-sample case - look for molecule_info.h5
    if [ -f "outs/molecule_info.h5" ]; then
        cp "outs/molecule_info.h5" "${prefix}_molecule_info.h5"
    elif [ -d "outs/per_sample_outs" ]; then
        # Multi-sample demux case
        found=0
        for h5_file in outs/per_sample_outs/*/*molecule_info.h5; do
            if [ -f "\${h5_file}" ]; then
                found=1
                demux_id="\$(basename "\$(dirname "\$(dirname "\${h5_file}")")")"
                cp "\${h5_file}" "${prefix}_\${demux_id}_molecule_info.h5"
            fi
        done
        if [ "\${found}" -eq 0 ]; then
            echo "ERROR: No sample_molecule_info.h5 files found" >&2
            exit 1
        fi
    else
        echo "ERROR: molecule_info.h5 not found in count outputs" >&2
        exit 1
    fi
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch "${prefix}_molecule_info.h5"
    """
}