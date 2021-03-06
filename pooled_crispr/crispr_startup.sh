#!/bin/bash
set -v

apt-get update && \
     apt-get install -y \
         apt-transport-https \
         ca-certificates \
         curl \
         software-properties-common \
         python-pip

curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | apt-key add -
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(lsb_release -cs) stable"

apt-get update && \
    apt-get install -y docker-ce

# install some python libraries for communicating back:
pip install pycrypto
pip install google-api-python-client

# Define the docker containers that drive this:
SAMTOOLS=biocontainers/samtools:1.3
BOWTIE2=biocontainers/bowtie2
PYTHON=continuumio/anaconda

docker pull $SAMTOOLS \
  && docker pull $BOWTIE2 \
  && docker pull $PYTHON

# a directory for scripts:
SCRIPTS_DIR=/scripts
mkdir $SCRIPTS_DIR
chmod 775 $SCRIPTS_DIR

WD=/workspace
mkdir $WD
chmod 777 $WD # so docker containers can read/write in this dir
cd $WD

# First pull all our data files, scripts, etc.
# To do that, we request metadata parameters from the VM:

# a folder in a bucket that holds the scripts necessary:
SCRIPTS_DIR_GS=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/scripts-directory)
gsutil cp $SCRIPTS_DIR_GS/* $SCRIPTS_DIR/

# a file (Excel, tsv, csv) that has the library definition, namely sequences:
LIBRARY_FILE_GS=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/library-file)

# a space-delimited string containing the locations of fastq files to process:
ALL_FASTQ_FILES_STR=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/fastq-files)
echo "Fastq files: "$ALL_FASTQ_FILES_STR
ALL_FASTQ_FILES_GS=( $ALL_FASTQ_FILES_STR ) # make into array

gsutil cp $LIBRARY_FILE_GS .
LIBRARY_FILE_LOCAL=$(basename $LIBRARY_FILE_GS)

FQ_FILES=""
for f in "${ALL_FASTQ_FILES_GS[@]}"; do
	echo "Copy "$f
	gsutil cp $f .
	FQ_FILES+=" "$(basename $f)
done;

# cast into array for use later:
FQ_FILES=( $FQ_FILES )

LIBRARY_FASTA=library.fa
echo "docker run -v $WD:/workspace -v $SCRIPTS_DIR:/scripts $PYTHON python /scripts/process_library.py /workspace/$LIBRARY_FILE_LOCAL /workspace/$LIBRARY_FASTA"
docker run -v $WD:/workspace -v $SCRIPTS_DIR:/scripts $PYTHON python /scripts/process_library.py /workspace/$LIBRARY_FILE_LOCAL /workspace/$LIBRARY_FASTA

IDX_DIR=bowtie_idx
mkdir $WD/$IDX_DIR
chmod 777 $WD/$IDX_DIR

# build the index
LIBRARY_IDX=library
docker run -v $WD:/workspace $BOWTIE2 bowtie2-build /workspace/$LIBRARY_FASTA /workspace/$IDX_DIR/$LIBRARY_IDX

COUNT_SUFFIX=".counts"
SORT_BAM_SUFFIX="sorted.bam"
SAMPLE_LIST_STR=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/sample-names)
SAMPLE_NAMES=( $SAMPLE_LIST_STR )
for k in "${!FQ_FILES[@]}"; do
	FQ="${FQ_FILES[$k]}"
	SAMPLE="${SAMPLE_NAMES[$k]}"
	SORTED_BAM=$SAMPLE"."$SORT_BAM_SUFFIX

	# do the alignments, change to BAM, sort BAM:
	docker run -v $WD:/workspace $BOWTIE2 bowtie2 \
		--trim3 5 -D 20 -R 3 -N 1 -L 20 -i S,1,0.50 \
		-x /workspace/$IDX_DIR/$LIBRARY_IDX \
		-U /workspace/$FQ | \
	docker run -i -v $WD:/workspace $SAMTOOLS samtools view -bS - | \
	docker run -i -v $WD:/workspace $SAMTOOLS samtools sort -o /workspace/$SORTED_BAM -O BAM -


	# index the bam and use idxstats to count the reads aligning to each target:
	docker run -v $WD:/workspace $SAMTOOLS samtools index /workspace/$SORTED_BAM
	docker run -v $WD:/workspace $SAMTOOLS samtools idxstats /workspace/$SORTED_BAM >$SAMPLE$COUNT_SUFFIX
done

# merge the count files:
OUTFILE=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/merged-counts-file)
docker run -v $WD:/workspace -v $SCRIPTS_DIR:/scripts $PYTHON python /scripts/merge_counts.py /workspace $COUNT_SUFFIX $OUTFILE

# Copy everything back to the cloud storage:
RESULT_BUCKET=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/result_bucket)
gsutil cp $OUTFILE $RESULT_BUCKET/$OUTFILE
gsutil cp *$SORT_BAM_SUFFIX $RESULT_BUCKET/
gsutil cp *$SORT_BAM_SUFFIX".bai" $RESULT_BUCKET/
gsutil cp $LIBRARY_FASTA $RESULT_BUCKET/

python $SCRIPTS_DIR/communicate.py
