#!/bin/bash

if ! which java ; then
	echo "Could not find Java installation in your PATH"
	exit 1
fi

# some paths to resources
STAR=/apps/STAR/bin/Linux_x86_64/STAR
SAMTOOLS=/apps/bin/samtools
PICARD_JAR=/apps/picard-tools-2.9.0/picard.jar

#############################################################
#input variables (which will be "injected" from elsewhere)
#all paths should be absolute-- no assumptions about where
#alignments should be placed relative to the working directory

FASTQFILEA={{r1_fastq}}
FASTQFILEB={{r2_fastq}}
SAMPLE_NAME={{sample_name}}
{% if is_paired %}
PAIRED=1
{% else %}
PAIRED=0
{% endif %}
GTF={{gtf_filepath}}
GENOME_INDEX={{star_index_dir}}
FCID={{flowcell_id}}
LANE={{lane}}
INDEX={{barcode}}
OUTDIR={{alignment_dir}}
#############################################################

# for convenience
NUM0=0
NUM1=1

#############################################################
#Run alignments with STAR
if [ $PAIRED -eq $NUM0 ]; then
    echo "run single-end alignment for " $SAMPLE_NAME
    $STAR --genomeDir $GENOME_INDEX \
         --readFilesIn $FASTQFILEA \
         --runThreadN 16 \
         --readFilesCommand zcat \
         --genomeLoad NoSharedMemory \
         --sjdbGTFfile $GTF \
	 --outSAMstrandField intronMotif \
	 --outFilterIntronMotifs RemoveNoncanonical \
	 --outFilterType BySJout \
         --outFileNamePrefix $OUTDIR'/'$SAMPLE_NAME'.' || { echo 'Failed during single-end alignment. Exiting.  '; exit 1; }
elif [ $PAIRED -eq $NUM1 ]; then
    echo "run paired alignement for " $SAMPLE_NAME
    $STAR --genomeDir $GENOME_INDEX \
         --readFilesIn $FASTQFILEA $FASTQFILEB \
         --runThreadN 16 \
         --readFilesCommand zcat \
         --genomeLoad NoSharedMemory \
         --sjdbGTFfile $GTF \
	 --outSAMstrandField intronMotif \
	 --outFilterIntronMotifs RemoveNoncanonical \
	 --outFilterType BySJout \
         --outFileNamePrefix $OUTDIR'/'$SAMPLE_NAME'.' || { echo 'Failed during paired-end alignment. Exiting.  '; exit 1; }
else
    echo "Did not specify single- or paired-end option."
    exit 1
fi
#############################################################

#for convenience:
BASE=$OUTDIR'/'$SAMPLE_NAME
DEFAULT_SAM=$BASE'.Aligned.out.sam'  #default naming scheme by STAR
SORTED_SAM=$BASE'.sam'
UNSORTED_BAM=$BASE'.bam'
SORTED_BAM=$BASE'.sort.bam'
TMPDIR=$OUTDIR'/tmp'


#add read-group lines, sort, and convert to BAM:
java -Xmx48g -jar $PICARD_JAR AddOrReplaceReadGroups \
	  I=$DEFAULT_SAM \
	  o=$SORTED_BAM \
	  VALIDATION_STRINGENCY=LENIENT \
	  TMP_DIR=$TMPDIR \
	  SORT_ORDER=coordinate \
	  RGID= $FCID'.Lane'$LANE \
	  RGLB=$SAMPLE_NAME \
	  RGPL=ILLUMINA \
	  RGPU=$INDEX \
	  RGSM=$SAMPLE_NAME \
	  RGCN='CCCB'  || { echo 'Failed during Picard tools sort and change headers. Exiting.  '; exit 1; }


# create index on the raw, sorted bam:
$SAMTOOLS index $SORTED_BAM  || { echo 'Failed during samtools index step. Exiting.  '; exit 1; }

# make a new bam file with only primary alignments
SORTED_AND_PRIMARY_FILTERED_BAM=$BASE.sort.primary.bam
$SAMTOOLS view -b -F 0x0100 $SORTED_BAM > $SORTED_AND_PRIMARY_FILTERED_BAM  || { echo 'Failed while filtering for primary alignments. Exiting.  '; exit 1; }
$SAMTOOLS index $SORTED_AND_PRIMARY_FILTERED_BAM || { echo 'Failed while indexing primary alignment BAM file. Exiting.  '; exit 1; }

# Create a de-duped BAM file (may or may not want, but do it anyway)
DEDUPED_PRIMARY_SORTED_BAM=$BASE.sort.primary.dedup.bam
java -Xmx42g -jar $PICARD_JAR MarkDuplicates \
	INPUT=$SORTED_AND_PRIMARY_FILTERED_BAM \
	OUTPUT=$DEDUPED_PRIMARY_SORTED_BAM \
	ASSUME_SORTED=TRUE \
	TMP_DIR=$TMPDIR \
	REMOVE_DUPLICATES=TRUE \
	METRICS_FILE=$DEDUPED_PRIMARY_SORTED_BAM.metrics.out \
	VALIDATION_STRINGENCY=LENIENT  || { echo 'Failed while marking and removing duplicates. Exiting.  '; exit 1; }

$SAMTOOLS index $DEDUPED_PRIMARY_SORTED_BAM  || { echo 'Failed while indexing deduplicated BAM file. Exiting.  '; exit 1; }

#cleanup
rm $DEFAULT_SAM &
rm -r $TMPDIR

#remove the empty tmp directories that STAR did not cleanup
rm -rf $OUTDIR'/'$SAMPLE_NAME'._STARgenome'

date
