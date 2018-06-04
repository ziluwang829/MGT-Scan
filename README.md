Modified GT-Scan
==============



This program is a slightly modified version of the **GT-Scan**. In this version, multiple sequences in a single
fa file can be searched simultaneously, depending on the number of cores. The original version can be
found [Here](https://gt-scan.csiro.au/)

#1. First, download and add [bowtie](http://bowtie-bio.sourceforge.net/tutorial.shtml) to your PATH variable in **.bashrc**. 
```
export $PATH=$PATH:/your/bowtie/path
```

#2. Clone the repository from this page by using the following command. 
```
git clone https://github.com/thepikabone/MGT-Scan
```

#3. Head back to the bowtie website and download the pre-built indexes for H. sapiens, UCSC hg19
from the right sidebar into the **genome** directory, and unzip the file. Remember this is your genome path. 

#4. Enter **MGT-Scan** directory and enter **gt-scan** directory. 
```
cd MGT-Scan
cd gt-scan
````

#5. Edit **config.ini** and specify the path (**ref_genome_dir**) to the your **genome** path from step 3.
```
ref_genome_dir=/your/genome/path
```

#6. Set permission of **gt-scan.py** in the **gt-scan** directory to **700**.
```
chmod 700 gt-scan.py
```

#7. Make a directory called **gtscan.db** in **/tmp**. This is where all the temporary files are stored.
Delete all files in this directory periodically.
```
cd /tmp
mkdir gtscan.db
```

#8. Export **gt-scan** directory to environment variable in **$HOME/.bashrc**.
```
export PATH=/your/gt-scan/path:$PATH
```

#9. In the console, type **R --args** , followed by the following args:

  a. **Directory**: Directory that contains the .fa file.
  
  b. **FileName**: Name of the .fa file.
  
  c. **n**: Numbers of pairs of target candidates per sequence.
  
  d. **dis**: The minimum distance between individual target candidate in a pair.
  
  e. **Cores**: Number of CPU cores this program can use.
  
Separate each arg with a space, then hit enter when you’re finished.

For example:
```
Example: R --args /home/zw355/ModifiedGT-Scan test.fa 3 80 4
```

#10. Run GTScan.R by **source(“GTScan.R”)** and wait for results. The results should be a tab file with the same name as
the .fa file.
```
source("GTScan.R")
```


#11. Clear db files in /tmp/gtscan.db.

The result, shown as a .tab file, may look like this:

chr1 714299 714318 - CGCCCGGCGCCGAAGACCGG chr1 714026 714045 + CCAACGGCCCACCTCTATGG

chr1 714299 714318 - CGCCCGGCGCCGAAGACCGG chr1 714026 714045 + CCAACGGCCCACCTCTATGG

Each line represents a pair of candidate sequences with their chromosome numbers, locations,
and directions. The distance between each two should be greater than the given minimum distance.
These target candidates are likely to have few to no mismatches. A reminder that a sequence in the fa
file may produce a maximum of n pairs, but it’s possible to have no output.
