#Necessary for mclapply function.
library(parallel)

#Removes unnecessary characters from output, only leaving the nucleotide.
cleanUp <- function(x){
  x <- gsub("<span>5'-</span><span class='b'>","",x)
  x <- gsub("</span><span class='y'>","",x)
  x <- gsub("</span><span class='y'>","",x)
  x <- gsub("</span><span class='g'>","",x)
  x <- gsub("</span>-3'","",x)
  x <- toString(x)
  return(x)
}

#The main function of this program.
gtscan <- function(x){
  #Creates a temp folder which stores temp file.
  tmpFolder <- tempfile()
  dir.create(tmpFolder,recursive=TRUE)
  tempFile <- tempfile("temp", tmpdir=tmpFolder, fileext=".fa")
  writeLines(unlist(x), con=tempFile)
  cat(tempFile)
  #Running the actual python code.
  system(paste("gt-scan.py -f ", tempFile, " -g hg19", sep=""))
  
  if(file.info(file=paste(tmpFolder, "/offtargets.csv", sep=""))$size!= 0){
    ctable <- read.csv(file=paste(tmpFolder, "/offtargets.csv", sep=""), header=F,  stringsAsFactors = F)
    system(paste("rm -rf ", tmpFolder))
    
    #Checks for number of outputs.
    g <- 0
    options(warn=-1)
    while(!is.na(as.numeric(ctable[g+1,1])))
    {
      g <- g+1
    }
    options(warn=0)

    
    l <- nchar(cleanUp(ctable[1,3]))
    
    f <- c()
    for(z in 1:g){
      f[z] <- (as.numeric(ctable[z,1]))
    }

    firstLine <- strsplit(x$chr, ":")
    firstLine[[1]][2] <- strsplit(firstLine[[1]][2], "-")
    firstLine[[1]][[1]] <- substring(firstLine[[1]][[1]],2)  
    chro <- firstLine[[1]][[1]]
    start <- as.numeric(firstLine[[1]][[2]][1])
    
    cregion <- list()
    r <- 0
    
    #Picks n pair of sequence with fewest mismatches.
    while(r<n && length(f)!=0 && length(f)!=1){
      for(d in 2:length(f)){
        if(abs(f[1]-f[d])>=(dis+l+1)){
          cregion[[r+1]] <- data.frame(chr1=chro, start1=(start+f[1]), end1=(start+f[1]-1+l),strand1=ctable[1,2], seq1=cleanUp(ctable[1,3]), 
          				chr2=chro, start2=(start+f[d]), end2=(start+f[d]-1+l),strand2=ctable[d,2], seq2=cleanUp(ctable[d,3]))
          ctable <- ctable[-c(1,d),]
          f <- f[-c(1,d)]
          r <- r+1
          break()
        }else if(length(f)==2){
          r <- n
          break()
        }else if(d == length(f)){
          f <- f[-1]
          ctable <- ctable[-1,]
          break()
        }
        if(length(f)==2){
          r <- n
        }
      } 
    }
    
    cregionpaste <- data.frame()
    for(e in cregion){
      cregionpaste <- rbind(cregionpaste, e)
    }
    
    return(cregionpaste)
  } else {
  return(NULL)
  }
}

#Turns fa file into a properly formatted list.
separateFa <- function(x){
  t <- c()
  for(i in 1:length(x)){
    if(substring(x[i],1,1)==">"){
      t <- c(t, i)
    }else if(i == length(x)){
      t <- c(t, i+1)
    }
  }
  faList <- list()
  for(i in 1:(length(t)-1)){
    a <- list(chr=x[t[i]], seq=x[(t[i]+1):(t[i+1]-1)])
    faList[[i]] <- a
  }
  return(faList)
}


	
args <- commandArgs(trailingOnly=TRUE)
#Directory is the directory in which contains the fa file. 
Directory  <- args[1]
cat("Directory: ",Directory, "\n")

#FileName is the name of the file.
FileName <- args[2]
cat("fa file name: ",FileName, "\n")

#n is number of pairs per sequence
n <- as.numeric(args[3])
cat("Number of pairs per sequence: ",n, "\n")

#dis is the minimum distance between the two sequence in a pair. 
dis <- as.numeric(args[4])
cat("Minimum distance between individual target candidate in a pair: ",dis, "\n")

#Cores is the numbers of core running this program.
Cores <- as.numeric(args[5])
cat("Number of cores running: ",Cores, "\n")

#Below is an example of possible inputs.
#Directory <- "/home/zw355/ModifiedGT-Scan"
#FileName <- "dnaseq.fa"
#n <- 3
#dis <- 80
#Cores <- 4

#Sets directory
setwd(Directory)
fileName <- gsub(".fa", "", FileName)
system(paste("cp", FileName, paste(fileName,".txt", sep=""), sep=" "))

#Reads the txt file.
fileNameTxt <- readLines(paste(fileName,".txt", sep=""))
seqlist <- separateFa(fileNameTxt)

#Begin using GT-Scan
ret <- mclapply(seqlist, gtscan, mc.cores= Cores)

#Writes the outputs
df <- do.call("rbind",ret)
write.table(df, file=paste(fileName, ".tab", sep=""), quote=FALSE, row.names=FALSE, col.names=FALSE, sep="\t")
