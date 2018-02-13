library(cccbDGEpipeline)
#library(ggplot2)
#library(calibrate)

# args from command line:
args<-commandArgs(TRUE)

OUTPUTDIR <- args[1]

# all paths below are relative to OUTPUTDIR
RAW_COUNT_MATRIX<-args[2] 
SAMPLE_ANNOTATION_FILE<-args[3]
OUTPUT_DESEQ_FILE <- args[4] 
OUTPUT_NORMALIZED_COUNTS_FILE <- args[5] # full path
LOG2FC_THRESHOLD <- as.numeric(args[6])
PVAL_THRESHOLD <- as.numeric(args[7])
setwd(OUTPUTDIR)

# START INPUTS: count matrix, annotation file
count_data=read.table(RAW_COUNT_MATRIX, header=T, sep="\t")
rownames(count_data)=count_data$Gene
count_data=count_data[-1]
annotations=read.table(SAMPLE_ANNOTATION_FILE, header=T, sep="\t", stringsAsFactors=F)
annotations$Sample_ID = make.names(annotations$Sample_ID)
write.table(annotations, SAMPLE_ANNOTATION_FILE, sep='\t', quote=F, row.names=F)
threshold=list(pvalue=PVAL_THRESHOLD, log2fc=LOG2FC_THRESHOLD)
# END INPUTS


# Define a contrast formula
FORMULA="~Group"

# Perform deseq2: return an object with dge result (dge) and normalized matrix (norm.mtx)
dge_result=cccbDGEpipeline::runDESeq2(count_data=count_data,
                               annotations=annotations,
                               FORMULA="~Group")

comparison = dge_result$comparisons[1]
print(comparison)
print(names(dge_result))
print(names(dge_result$dge))
print(head(dge_result$dge[[comparison]]))
#write.table(dge_result$dge$control_treatment, file=OUTPUT_DESEQ_FILE, quote=F, sep="\t", row.names=F)
write.table(dge_result$dge[[comparison]], file=OUTPUT_DESEQ_FILE, quote=F, sep="\t", row.names=F)
write.table(dge_result$norm.mtx, file=OUTPUT_NORMALIZED_COUNTS_FILE, quote=F, sep="\t")
print('Done with deseq')

# Make PCA with PC1 vs PC2 on normalized count
cccbDGEpipeline::Draw.PCA(dge_result=dge_result,
                            outfile="pca_plot.pdf",
                            res=600,
                            width=12,
                            height=8)

### Make heatmap
# Perform filtering based off pvalue
Sig.Gene=c(as.character(subset(dge_result$dge[[comparison]],
                pvalue<threshold$pvalue &
                log2FoldChange>threshold$log2fc,
                feature)$feature),
           as.character(subset(dge_result$dge[[comparison]],
                  (pvalue<threshold$pvalue) &
                    (log2FoldChange< -1*threshold$log2fc),
                  feature)$feature))
sig.nData=as.data.frame(dge_result$norm.mtx[Sig.Gene,])

# Add 1 to all values before log transformation
sig.nData=log(sig.nData+1)
sig.nData<-as.matrix(sig.nData)
# Draw Heatmap
cccbDGEpipeline::Draw.Heatmap(sig.nData,
                                col.panel=c("blue", "white", "red"),
                                scale="none",
                                outfile="heatmap.png")
# END DRAW HEATMAP

# DRAW VOLCANO PLOT
curr_dge=na.omit(dge_result$dge[[comparison]])
cccbDGEpipeline::Draw.dge.Volcano(dge_result=curr_dge,
                           pvalue.thresh=threshold$pvalue,
                           log2fc.thresh=threshold$log2fc,
                           outfile="volcano.png",
                           res=150,
                           width=1200,
                           height=1200)
# END DRAW VOLCANO


