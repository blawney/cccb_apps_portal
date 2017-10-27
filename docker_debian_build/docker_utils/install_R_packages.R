# This script should be used to install packages into the R installation

install.packages('gplots', repos='http://cran.us.r-project.org')
install.packages('calibrate', repos='http://cran.us.r-project.org')

source("http://bioconductor.org/biocLite.R")
biocLite("DESeq2")
