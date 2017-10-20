#!/bin/bash

WD=/workspace
mkdir $WD
chmod 777 $WD # so docker containers can read/write in this dir

# First pull all our data files, etc.
# To do that, we request metadata parameters from the VM:

# a file (Excel, tsv, csv) that has the library definition, namely sequences:
LIBRARY_FILE_GS=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/library-file)

# a space-delimited string containing the locations of fastq files to process:
ALL_FASTQ_FILES_STR=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/fastq-files)
ALL_FASTQ_FILES_GS=( $ALL_FASTQ_FILES_STR ) # make into array


gsutil cp $LIBRARY_FILE_GS $WD/

for f in "${ALL_FASTQ_FILES_GS[@]}" do;
	gsutil cp $f $WD/
done;

# Now that we have the files, we use a python script to turn that into a fasta file.
# We pull the docker image for that environment locally:
docker pull continuumio/anaconda

LIBRARY_FASTA=library.fa
docker run -v $WD:/workspace continuumio/anaconda python process_library.py /workspace/$LIBRARY_FILE_GS /workspace/$LIBRARY_FASTA

# We now have a fasta file giving the library definition.  Make a bowtie2 index:
docker pull biocontainers/bowtie2
docker pull biocontainers/samtools:1.3

IDX_DIR=bowtie_idx
mkdir $WD/$IDX_DIR
chmod 777 $WD/$IDX_DIR

# build the index
LIBRARY_IDX=library
docker run -v $WD:/workspace biocontainers/bowtie2 bowtie2-build /workspace/$LIBRARY_FASTA /workspace/$IDX_DIR/$LIBRARY_IDX

for (FASTQ); do

	SORTED_BAM=<NAME>

	# do the alignments, change to BAM, sort BAM:
	docker run -v $WD:/workspace <bowtie2 container> bowtie2 \
		--trim3 5 -D 20 -R 3 -N 1 -L 20 -i S,1,0.50 
		-x /workspace/$IDX_DIR/<index_name> 
		-U /workspace/test.fastq.gz | \
	docker run -i -v $WD:/workspace <samtools docker> samtools view -bS - | \
	docker run -i -v $WD:/workspace <samtools docker> samtools sort -o /workspace/$SORTED_BAM -O BAM -


	# index the bam and use idxstats to count the reads aligning to each target:
	docker run -v $WD:/workspace <samtools docker> samtools index /workspace/$SORTED_BAM
	docker run -v $WD:/workspace <samtools docker> samtools idxstats /workspace/$SORTED_BAM

done
