#!/bin/bash

# This script runs the KNIFE analysis and copies results back to a bucket
# The first 4 arguments are specific to the script, while the remaining args
# are passed directly to the KNIFE process.

# need to know genome, which files to work with:

# mm10, hg19, or the other KNIFE indices
genome=$1

# path to a bucket: e.g. gs://foo/bar/baz.fastq.gz (include the gs:// prefix!)
# Need at least a single R1 fastq:
fq1_path=$2

# if single-end (no R2 read), just make this '-'
fq2_path=$3

# Another path to a bucket, including the gs:// prefix.
output_bucket=$4

# Path to a google cloud credential file.  The container has access to this file via a mount to the host system
# Thus, this arg should be using the path to the credential file IN THE CONTAINER, and not the path on the host VM
export CRED_FILE_PATH=$5
# get gsutil up and running.  We first authenciate with gcloud which allows us to use gcloud
$GCLOUD auth activate-service-account --key-file=$CRED_FILE_PATH
SERVICE_ACCOUNT=$(python /srv/software/get_account_name.py $CRED_FILE_PATH)
export BOTO_PATH=/root/.config/gcloud/legacy_credentials/$SERVICE_ACCOUNT/.boto

# shift the pointer; the remainder of the args get passed directly to the knife shell script.
shift
shift
shift
shift
shift

# create a directory for the fastq, change there, and pull the files from a bucket:
fastq_dir=$1
mkdir -p $fastq_dir && \
gsutil cp $fq1_path $fastq_dir/ && \
if [ "$fq2_path" != "-" ]
  then
    gsutil cp $fq2_path $fastq_dir/
fi

# create the necessary index directories and pull the index
# for the particular gene from a bucket:
cd /srv/software/knife/circularRNApipeline_Standalone && \
mkdir index && \
cd index

gsutil cp gs://cccb-knife-resources/$genome/$genome_*bt2 .
gsutil cp gs://cccb-knife-resources/$genome/$genome_*bt2l .
gsutil cp gs://cccb-knife-resources/$genome/$genome_*fa .

cd /srv/software/knife/circularRNApipeline_Standalone/denovo_scripts && \
mkdir index && \
cd index

gsutil cp gs://cccb-knife-resources/$genome/$genome_*ebwt .
gsutil cp gs://cccb-knife-resources/$genome/$genome_*gtf .


# now change to the main script directory and run:
cd /srv/software/knife/circularRNApipeline_Standalone

# To run the script, there are 5 required parameters, 10 total.  They are described
# here: https://github.com/lindaszabo/KNIFE
# In short:
# 1: path to read directory (absolute)
# 2: read_id_style: complete|appended.  Usually complete
# 3: alignment_parent_dir: output path (absolute).  Must already exist
# 4: dataset name
# 5: junction overlap.  8 for PE (<70), 13 for longer PE, 10 for SE (<70), 15 for longer SE
# others...see github

# need to make the output directory.  We have already shifted the arg pointer  
# so this directory is $3

mkdir -p $3
sh completeRun.sh "$@" 2>&1 | tee out.log

# Once that is complete, move the files back to a result bucket
gsutil cp -R $3 $output_bucket
