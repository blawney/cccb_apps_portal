if(!require("DESeq2", character.only=T)) stop("Please install the DESeq2 package first.")

# args from command line:
args<-commandArgs(TRUE)
RAW_COUNT_MATRIX<-args[1]
SAMPLE_ANNOTATION_FILE<-args[2]
CONDITION_A<-args[3]
CONDITION_B<-args[4]
OUTPUT_DESEQ_FILE <- args[5] #full path
OUTPUT_NORMALIZED_COUNTS_FILE <- args[6] # full path

# read the raw count matrix, genes as row names:
count_data <- read.table(RAW_COUNT_MATRIX, sep='\t', header = T, row.names = 1, stringsAsFactors = F)

# read the annotations
annotations <- read.table(SAMPLE_ANNOTATION_FILE, sep='\t', header = F, col.names = c('sample','condition'), stringsAsFactors = F)

# Keep only the rows that concern our contrast of interest
# Could keep it all together, but this is more explicit
selected_groups<-c(CONDITION_A, CONDITION_B)
annotations<-annotations[annotations$condition %in% selected_groups,]

# subset to only keep samples corresponding to the current groups in the count_data dataframe
count_data <- count_data[,annotations$sample]

# DESeq2 expects that the rownames of the annotation data frame are the sample names.  Set the rownames and drop that col
rownames(annotations) <- annotations$sample
annotations <- annotations[-1]

# Need to set the condition as a factor since it's going to be used as a design matrix
annotations$condition <- as.factor(annotations$condition)


dds <- DESeqDataSetFromMatrix(countData = count_data,
							  colData = annotations,
							  design = ~condition)

dds <- DESeq(dds)
res <- results(dds, cooksCutoff=F)
original_colnames = colnames(res)
n = length(original_colnames)
baseMeanA = rowMeans(counts(dds,normalized=TRUE)[,dds$condition == CONDITION_A]) 
baseMeanB = rowMeans(counts(dds,normalized=TRUE)[,dds$condition == CONDITION_B]) 
res = cbind(rownames(res), res[,1],baseMeanA, baseMeanB, as.data.frame(res[,2:n])) 
colnames(res) = c('Gene', 'overall_mean', CONDITION_A, CONDITION_B, original_colnames[2:n])
resOrdered <- res[order(res$padj),]
write.table(resOrdered, OUTPUT_DESEQ_FILE, sep='\t', quote=F, row.names=F)

#normalized counts:
dds <- estimateSizeFactors(dds)
nc <- counts(dds, normalized=TRUE)
#nc$gene <- rownames(nc)
nc <- cbind(gene=rownames(nc), nc)
#write.table(nc, OUTPUT_NORMALIZED_COUNTS_FILE, sep='\t', quote=F, col.names=NA)
write.table(nc, OUTPUT_NORMALIZED_COUNTS_FILE, sep='\t', quote=F, row.names=F)
