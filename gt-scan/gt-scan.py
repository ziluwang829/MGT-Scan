#!/usr/bin/python
import subprocess as sp
import re, time, sys,getopt,csv
import os
import ConfigParser
from os import makedirs
from os.path import dirname
import sqlite3 as db
import random

# Root path
base_path = dirname(os.path.abspath(__file__))
# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import argparse
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.Alphabet import generic_dna

#Load rule and generate regex for candidateTargets
def createCandidateTargetRegex(rule):
    targetRule = ''
    for i in rule:
        if i in 'XxNn':
            targetRule+='[ACTG]'
        elif i in 'Rr':
            targetRule+='[AG]'
        else:
            targetRule+='[{0}]'.format(i)
    return re.compile(targetRule, re.IGNORECASE)

#Returns the descriptor line from a FASTA file
def getCandidateSequenceDescriptor(faPath):
    with open(faPath) as f:
        try:
            return SeqIO.read(f,'fasta').description
        except ValueError, v:
            if v[0] == 'No records found in handle':
                return 'No FASTA header'

#Loads a FASTA file and creates a string <candidate_seq> from the sequence.
def createCandidateSequenceString(faPath):
    with open(faPath) as f:
        try:
            sequence = SeqIO.read(f,'fasta').seq.tostring()
        except ValueError, v:
            if v[0] == 'No records found in handle':
                f.seek(0)
                sequence = ''.join(line.rstrip() for line in f)
    return sequence.translate(None, '1234567890 ')

#Get the reverse complement of a DNA string
def reverseComplement(seq):
    return Seq(seq, generic_dna).reverse_complement().tostring()

#Recursivly replaces Ns with nucleotides ATCG to create potential off-target sequences
def recursiveReplace(rule, target, tmpOffTargets, tmpStr):
    if rule[len(tmpStr)] == 'N':   ##Is current position an N?
        for i in 'ACTG':
            tmpStr += i
            if len(tmpStr) == len(target):  ## tmpStr appended to tmpOffTargets
                tmpOffTargets.append(tmpStr)
                tmpStr = tmpStr[:-1]
            else:   
                recursiveReplace(rule, target, tmpOffTargets, tmpStr)
                tmpStr = tmpStr[:-1]
    elif rule[len(tmpStr)] in 'Rr':   ##Is current position an N?
        for i in 'AG':
            tmpStr += i
            if len(tmpStr) == len(target):  ## tmpStr appended to tmpOffTargets
                tmpOffTargets.append(tmpStr)
                tmpStr = tmpStr[:-1]
            else:   
                recursiveReplace(rule, target, tmpOffTargets, tmpStr)
                tmpStr = tmpStr[:-1]
    else:
        tmpStr += target[len(tmpStr)]
        #if tmpStr == target:
        #    tmpStr=tmpStr[:-1]
        if len(tmpStr) == len(target):
            tmpOffTargets.append(tmpStr)
            tmpStr = tmpStr[:-1]
        else:
            recursiveReplace(rule, target, tmpOffTargets, tmpStr)
            tmpStr = tmpStr[:-1]


# Inserts job info (the left-side column) into the sqlite DB.
def insertJobInfo(rule, filter, whereabouts, jobTitle, refGenome, mismatches, faName):
    formattedRule = makeSeq(rule,rule)
    formattedFilter = "5'-{0}-3'".format(filter)
    if whereabouts[1] != '':
        newWhere = '{0}:{1}-{2} ({3})'.format(whereabouts[1], whereabouts[2], whereabouts[3], whereabouts[0])
    else:
        newWhere = 'Could not locate candidate sequence in reference genome.'
    try:
        newLen = str(whereabouts[4])
    except IndexError:
        newLen = str(whereabouts[0])
    runTime = int(time.time() - startTime)
    h = runTime/60
    m = runTime - 60*h
    fTime = '00:{0:02d}:{1:02d}'.format(h,m)
    cur.execute("CREATE TABLE info(name TEXT, rule TEXT, filter TEXT, mismatches INT, genome TEXT, faName TEXT, location TEXT, length TEXT, time TEXT)")
    cur.execute("INSERT INTO info VALUES (?,?,?,?,?,?,?,?,?)",(jobTitle, formattedRule, formattedFilter, mismatches, refGenome, faName, newWhere, newLen, fTime))
    con.commit()


# Insert off-targets into the sqlite DB
def insertOffTargetInfo(candidateTargets,potentialOffTargets,offTargSummary,rule,ucscVars):
    targs = [x for x in candidateTargets]
    #for precurrentId in cur.execute("SELECT strand, offset FROM targets"):
    #    targs2.append(   map(int, ', '.join(map(str, precurrentId)))   )
    for currentId in targs:
        currentCount = 0
        key = '{0},{1}'.format(currentId,currentCount)

        #Create a table for each target to store its off-targets
        cur.execute('CREATE TABLE "{0}"(sequence TEXT, total INTEGER, high INTEGER, low INTEGER, chromosome TEXT, offset INTEGER, strand TEXT, GC INTEGER, browser TEXT)'.format(currentId))
        insertquery = 'INSERT INTO "{0}" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'.format(currentId)

        #Does this for every off-target.
        while key in potentialOffTargets:
            totalMismatches = potentialOffTargets[key][4]
            highMismatches = potentialOffTargets[key][5]
            lowMismatches = totalMismatches - highMismatches
            # Filter: don't add OTs to table when > 100 OTs to save space
            if totalMismatches > 1 and offTargSummary[currentId][totalMismatches] > 100:
                currentCount += 1
                key = '{0},{1}'.format(currentId,currentCount)
            else:
                subOffTarget = potentialOffTargets[key][3]                               
                prettySeq = matching(candidateTargets[currentId][0],subOffTarget,rule)
                gc=calculateGC(subOffTarget)
                url = "<a href=\'{0}\' target=\'_blank\'><div></div></a>".format(
                    ucscVars).format(
                        potentialOffTargets[key][1], int(potentialOffTargets[key][2])+1, int(potentialOffTargets[key][2])+len(rule))

                varlist = (prettySeq, totalMismatches, highMismatches, lowMismatches, potentialOffTargets[key][1], int(potentialOffTargets[key][2])+1, potentialOffTargets[key][0], gc, url)
                cur.execute(insertquery,varlist)
                currentCount +=1
                key = '{0},{1}'.format(currentId,currentCount)	
        con.commit()


# Insert candidateTargets into the sqlite DB
def insertTargetInfo(candidateTargets, offTargSummary, rule):
    cur.execute("CREATE TABLE targets(offset INTEGER, strand TEXT, sequence TEXT, h0 INTEGER, h1 INTEGER, h2 INTEGER, h3 INTEGER)")
    for key in candidateTargets.keys():
        if offTargSummary[key][0] <= 100: # Filter out targets with > 100 exact matches
            hammings = offTargSummary[key]
            prettySeq = makeSeq(candidateTargets[key][0], rule)
            varlist = [candidateTargets[key][1], candidateTargets[key][3], prettySeq] + hammings
            cur.execute("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?, ?)", varlist)
    con.commit()


# matching(seq1,seq2)
# This function compares the two input sequences and returns a HTML formatted string containing seq2.
# This allows the CSS to specify formatting (text colour in this case) of matches and mismatches.
# It's recursive to save space with a smaller output file:
#<span class=b>GG</span>       instead of:       <span class=b>G</span><span class=b>G</span>  The space saved adds up!
# Adjacent matching characters are placed in a span with class 'b'.
# Adjacent mismatch characters are placed in a span with class 'r'.
# Adjacent mismatch characters are placed in a span with class 'r'.
def matching(seq1,seq2,rule,count=0,string='',flag=''):
    if count < len(seq2):
        if count == 0:
            string = "<span>5'-"
        if rule[count].upper() in 'NR':
            if seq2[count] != seq1[count].upper():
                if flag == 'N':
                    string = string + seq2[count]
                    return matching(seq1, seq2, rule, count+1, string, 'N')
                else:
                    # Uncomment (and comment next) for mismatched Ns to be bolded.
                    # string = "{0}</span><span class='g'><b>{1}</b>".format(string, seq2[count])
                    string = "{0}</span><span class='g'>{1}".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'N')
            else:
                if flag == 'N':
                    string = string + seq2[count]
                    return matching(seq1, seq2, rule, count+1, string, 'N')
                else:
                    string = "{0}</span><span class='g'>{1}".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'N')
                
        elif rule[count] in 'XACTG':
            if seq2[count] != seq1[count].upper():
                if flag == 'X':
                    string = "{0}<b>{1}</b>".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'X')
                else:
                    string = "{0}</span><span class='y'><b>{1}</b>".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'X')
            else:
                if flag == 'X':
                    string = string + seq2[count]
                    return matching(seq1, seq2, rule, count+1, string, 'X')
                else:
                    string = "{0}</span><span class='y'>{1}".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'X')
                
        else:
            if seq2[count] != seq1[count].upper():
                if flag == 'x':
                    string = "{0}<b>{1}</b>".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'x')
                else:
                    string = "{0}</span><span class='b'><b>{1}</b>".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'x')
            else:
                if flag == 'x':
                    string = string + seq2[count]
                    return matching(seq1, seq2, rule, count+1, string, 'x')
                else:
                    string = "{0}</span><span class='b'>{1}".format(string, seq2[count])
                    return matching(seq1, seq2, rule, count+1, string, 'L')
    else:
        return string+"</span>-3'"

#makeSeq(sequence, rule)
# Makes an HTML formatted string of seq, based on rule.
# Different classes allow CSS to specify colouring of each span.
def makeSeq(seq, rule, string='', count=0, lastChar=''):
    if count < len(seq):
        if count == 0:
            string = "<span>5'-"
            
        # Sets span to colour Ns red
        if rule[count].upper() in 'NR':
            if lastChar == 'N': #This happens current char follows an N 
                string = string + seq[count]
                return makeSeq(seq, rule, string, count + 1, 'N')
            else: #This happens if previous letter was not an N
                string = "{0}</span><span class='g'>{1}".format(string, seq[count])
                return makeSeq(seq, rule, string, count + 1, 'N')

        # Sets span to colour Ls blue
        elif rule[count] in 'XACTG':
            if lastChar == 'X':
                string = string + seq[count]
                return makeSeq(seq, rule, string, count + 1, 'X')
            else:
                string = "{0}</span><span class='y'>{1}".format(string, seq[count])
                return makeSeq(seq, rule, string, count + 1, 'X')
            
        # Sets span to colour everything else (ACTG) green
        else:
            if lastChar == 'x':
                string = string + seq[count]
                return makeSeq(seq, rule, string, count + 1, 'x')
            else:
                string = "{0}</span><span class='b'>{1}".format(string, seq[count])
                return makeSeq(seq, rule, string, count + 1, 'x')

    # Closes off the string       
    else:
        return "{0}</span>-3'".format(string)


# Calculates GC-content, i.e. percentage of GgCc chars in a string to two decimal places
def calculateGC(seq):
    gcre = re.compile('[GC]', re.IGNORECASE)
    gc = filter(lambda x: gcre.match(x), seq)
    return ('%.2f') % (len(gc)*1.0/len(seq)*100)


# Creates a FASTA file with a seperate entry for every sequence in the dictionary 'sequences'.
def createFastaFile(out_path, sequences):
    with open('{0}/potentialofftargetstrings.fa'.format(out_path), 'w') as f:
        for i in sequences:
            for j in sequences[i]:
                f.write('>{0}\n{1}\n'.format(i,j))





# Calls Bowtie with user-specified parameters.
# Input FASTA file name is the same as createFastaFile()
def bowtieSearch(call):
    print call
    proc = sp.Popen(call, shell = True, stderr=sp.PIPE, stdout=sp.PIPE)
    stdout_value, stderr_value = proc.communicate()
    print stderr_value
    return stdout_value, stderr_value





# This parses the information from the SQLite DB as well as CSS and JS dependencies into the one HTML file.
# Only called for offline mode.
def dbToHtml(out_path):
    tf = open(os.path.join(base_path, 'templates','template.html'), 'r') # Open template HTML file
    nf = open(os.path.join(out_path, 'index.html'), 'w') # Open new empty HTML file

    # Create regex rules to scan for .css, .js references and '$:' placeholders 
    cssMatch = re.compile(r"[^\'| |\"]*\.css")
    jsMatch = re.compile(r"[^\'| |\"]*\.js")
    placeholder = re.compile('(\$:)[^\W]*')

    #Sets up DB cursor and retrieves the target side bar info
    con.text_factory = str
    cur = con.cursor()
    cur.execute("SELECT * FROM info")
    targetInfo = cur.fetchall()

    #New array to store IDs for each row as the following function progresses
    #NOTE: in the template.html file, the tables.js line MUST be before otables.js
    rowIDs = []

    # Reads the template.html file and inserts CSS, JS and other info to make one self-contained file.
    for line in tf:
        # If the line is a CSS reference, read that CSS file into the document.
        if cssMatch.search(line):
            path = cssMatch.search(line).group(0)
            nf.write('<style>\n')
            with open(os.path.join(base_path, 'static/css', path.split('/')[-1]), 'r') as stylesheet:
                for i in stylesheet:
                    nf.write(i)
            nf.write('</style>\n')
        # If the line is a JS reference:
        elif jsMatch.search(line):
            path = jsMatch.search(line).group(0)
            nf.write('<script>\n')
            # This reads JS files into the new HTML file.
            if 'tables.js' not in path:
                with open(os.path.join(base_path, 'static/js', (path.split('/')[-1])), 'r') as javascript:
                    for i in javascript:
                        nf.write(i)
            # If the line references tables.js: read the tables from the DB to the HTML file
            elif path.split('/')[-1] == 'tables.js':
                nf.write('var candidateTargetData = [\n')
                cur.execute("SELECT * FROM targets")
                rows = cur.fetchall()
                for row in rows:
                    rowIDs.append(int('{0}{1}'.format(row[1],row[0])))
                    nf.write('[{0},"{1}","{2}",{3},{4},{5},{6}],\n'.format(*row))
                nf.write(']')

            elif path.split('/')[-1] == 'otables.js':
                nf.write('var offTargetData = {\n')
                for targID in rowIDs:
                    cur.execute("SELECT * FROM \"{0}\"".format(targID))
                    rows = cur.fetchall()
                    nf.write('"{0}":['.format(targID))
                    for row in rows:
                        nf.write('  ["'+'", "'.join(map(str,row))+'"],\n')
                    nf.write('],')
                nf.write('}')
            nf.write('</script>\n')

        elif placeholder.search(line) is not None:
            if placeholder.search(line).group(0).split(':')[1] == 'jobName':
                nf.write(line.replace(placeholder.search(line).group(0), targetInfo[0][0]))
            elif placeholder.search(line).group(0).split(':')[1] == 'rule':
                nf.write(line.replace(placeholder.search(line).group(0), targetInfo[0][1]))
            elif placeholder.search(line).group(0).split(':')[1] == 'ruleLen':
                nf.write(line.replace(placeholder.search(line).group(0), str(len(targetInfo[0][2])-6)))
            elif placeholder.search(line).group(0).split(':')[1] == 'filter':
                nf.write(line.replace(placeholder.search(line).group(0), targetInfo[0][2]))
            elif placeholder.search(line).group(0).split(':')[1] == 'mismatches':
                nf.write(line.replace(placeholder.search(line).group(0), str(targetInfo[0][3])))
            elif placeholder.search(line).group(0).split(':')[1] == 'genome':
                nf.write(line.replace(placeholder.search(line).group(0),str(targetInfo[0][4])))
            elif placeholder.search(line).group(0).split(':')[1] == 'regionID':
                nf.write(line.replace(placeholder.search(line).group(0),str(targetInfo[0][5])))
            elif placeholder.search(line).group(0).split(':')[1] == 'region':
                nf.write(line.replace(placeholder.search(line).group(0),targetInfo[0][6]))
            elif placeholder.search(line).group(0).split(':')[1] == 'length':
                nf.write(line.replace(placeholder.search(line).group(0),targetInfo[0][7]))
            elif placeholder.search(line).group(0).split(':')[1] == 'time':
                nf.write(line.replace(placeholder.search(line).group(0),targetInfo[0][8]))
        else:
            nf.write(line)
    nf.close()
    
# This parses the information from the SQLite DB as well as CSS and JS dependencies into the one HTML file.
# Only called for offline mode.
def dbToCsv(out_path):
    with open(os.path.join(out_path, 'offtargets.csv'), 'w') as nf:

        #Sets up DB cursor
        con.text_factory = str
        cur=con.cursor()

        #New array to store IDs for each row as the following function progresses
        rowIDs = []

        # If the line references tables.js: read the tables from the DB to the HTML file
        cur.execute("SELECT * FROM targets")

        for row in cur.fetchall():
            rowIDs.append(int('{0}{1}'.format(row[1], row[0])))
            nf.write('{0},"{1}","{2}",{3},{4},{5}\n'.format(*row))

        for targID in rowIDs:
            targStrand = '+' if targID > 0 else '-'
            cur.execute("SELECT * FROM \"{0}\"".format(targID))
            rows = cur.fetchall()
            for row in rows:
                nf.write('{0},{1},{3},{6},{7},{8}'.format(targStrand, targID, *row) + '\n')


def insertIntoDB(candidateTargets, potentialOffTargets, offTargSummary, rule, filter, mismatches, whereabouts, jobTitle, refGenome, faName, ucscVars=['']):
    print('Creating files...\n')
    insertTargetInfo(candidateTargets, offTargSummary, rule)
    insertOffTargetInfo(candidateTargets, potentialOffTargets, offTargSummary, rule, ucscVars)
    insertJobInfo(rule, filter, whereabouts, jobTitle, refGenome, mismatches, faName)


# Creates a FASTA file of potential off-targets, calls Bowtie with this file as an input and processes Bowtie's output.
# Returns summary, a summary of potential off-targets at each H for each candidate target and
# potentialOffTargets, a dictionary of every potential off-target.
# This function removes the potential off-target if it is the same as the input.
def filterPotentialOffTargets(out_path, potentialOffTargetStrings, refGenome, H, rule, filter, mismatches, whereabouts):
    print('Locating off-targets...\n')
    createFastaFile(out_path, potentialOffTargetStrings)
    bowtieSearch('{0} {1} -f {2}/potentialofftargetstrings.fa -k 200 -v 3 {3}/output.out'.format(bowtiePath, refGenome, out_path, out_path))
    ht = {0:0, 1:0, 2:0, 3:0}
    prevLine = 1
    potentialOffTargets = {}
    summary = {}
    i = 0

    with open('{0}/output.out'.format(out_path)) as tsv:
        for line in csv.reader(tsv, dialect='excel-tab'):
            currentID = (line[0])
            currentHamming = (len(line[7])+1)/6
            isTrueOffTarget = 1
            highSpecificityMismatchCount = 0
            subOffTarget = line[4]
            #Does this only when processing the first potential off-target for each candidate target.
            if prevLine != currentID:
                summary[prevLine] = [ht[0], ht[1], ht[2], ht[3]] # Commits the final scores for the previous target
                i, ht[0], ht[1], ht[2], ht[3] = 0, 0, 0, 0, 0 # Instantializes new scores to be used for current target

            #Removes false potential off-targets, i.e. if potential off-target is the candidate target or mismatch is in N position
            
            # Does the following if H = 0
            if currentHamming == 0:
                if line[2] == whereabouts[1]: # if in same chromosome
                    if whereabouts[2] <= int(line[3])+1 <= whereabouts[3]: #If in candidate region
                        isTrueOffTarget = 0

            # Does the following if H > 0   
            else:
                #Creates the off-target sequence, from original sequence and mismatch positions       
                for sub in line[7].split(','):
                    if line[1] == '-':
                        mod = len(subOffTarget) - int(sub.split(':')[0]) - 1
                    else:
                        mod = int(sub.split(':')[0])
                    subOffTarget = subOffTarget[0:mod] + sub.split(':')[1][ 0 ] + subOffTarget[(mod + 1):] 

                for m in re.finditer('[NnRr]', rule): #For each N position in rule
                    for o in line[7].split(','): #For each mismatch in off-target from BOWTIE
                        if m.end()-1 == int(o.split(':')[0]): #remove if they match because we substitute N positions, so these are double ups.
                            isTrueOffTarget = 0

                #We've removed the off-targets with mismatches on Ns, or were actually 'targets'. Now
                #we shall filter for off-targets above the rule threshold.
                if isTrueOffTarget == 1: #Don't bother doing if off-target has already been set as dodgy.
                    for j in range(0,len(rule)):
                        for p in line[7].split(','):
                            if rule[j] in 'ACTGX' and j == int(p.split(':')[0]):
                                highSpecificityMismatchCount += 1
                    if highSpecificityMismatchCount > mismatches:
                        isTrueOffTarget = 0

            #Get reverse-complement for -ve strand off-target        
            if line[1] == '-':
                subOffTarget = reverseComplement(subOffTarget) 

            #Final filter: Remove anything not matching the off-target filter regex        
            if filter.match(subOffTarget) == None:
                isTrueOffTarget = 0

            if isTrueOffTarget == 1: #Add off-target
                potentialOffTargets['{0},{1}'.format(currentID,i)] = line[1:4]+[subOffTarget]+[currentHamming]+[highSpecificityMismatchCount]+[line[0]]
                ht[currentHamming] += 1
                i += 1
            prevLine = currentID
        summary[prevLine] = [ht[0], ht[1], ht[2], ht[3]] # does this for last line in the file.
    # Checks that every one is in summary, (in case Bowtie doesn't find off-target...
    for i in potentialOffTargetStrings:
        if i not in summary:
            summary[i] = [0, 0, 0, 0]
    return summary, potentialOffTargets


# Generate potential off-targets with different nucleotides at N positions
def createPotentialOffTargetStrings(rule, candidateTargets):
    potentialOffTargetStrings = {}    ## Dictionary of off-targets, for every target.
    for target in candidateTargets:
        tmpStr = ''     ## Appended to tmpOffTargets when length equal to rule length
        tmpOffTargets = []  ## Holds off-targets for current target, appended to potentialOffTargetStrings
        recursiveReplace(rule,candidateTargets[target][0],tmpOffTargets,tmpStr)
        potentialOffTargetStrings[target] = tmpOffTargets
    return potentialOffTargetStrings


# Find target sites and add to dictionary, 'candidateTargets'.
def findCandidateTargets(rule,faPath):
    print('Locating candidate targets...\n')
    targetRe = createCandidateTargetRegex(rule)
    candidateSequence = createCandidateSequenceString(faPath)
    rcCandidateSequence = reverseComplement(candidateSequence)
    windowSize = len(rule)
    candidateTargets = {}
    negFix = len(candidateSequence) - len(rule)


    # Scans string for candidate targets
    for i in range(0, len(candidateSequence)-windowSize+1):               ## Sliding window of len(rule)
        if targetRe.match(candidateSequence[i:i+windowSize]) != None:    ## If there IS match with regex 
            GC = calculateGC(candidateSequence[i:i+windowSize])            ## Also calculate GC content
            candidateTargets[str(i+1)] = (targetRe.match(candidateSequence[i:i+windowSize]).group(), i+1, GC, '+')

    # Scans reverse complement string for candidate targets
    for i in range(0, len(rcCandidateSequence)-windowSize+1):               ## Sliding window of len(rule)
        if targetRe.match(rcCandidateSequence[i:i+windowSize]) != None:    ## If there IS match with regex 
            GC = calculateGC(rcCandidateSequence[i:i+windowSize])            ## Also calculate GC content
            candidateTargets[str(i-1-negFix)] = (targetRe.match(rcCandidateSequence[i:i+windowSize]).group(), negFix-i+1, GC, '-')
    return candidateTargets

#Runs a Bowtie search to locate the candidate sequence within the reference genome
def findCandidateSequenceInfo(faPath, refGenome):
    candidateSequence = createCandidateSequenceString(faPath)
    candidateSequenceLength = len(candidateSequence)
    if candidateSequenceLength < 200:
        call = '{0} {1} -c {2}'.format(bowtiePath, refGenome, candidateSequence)
        l1 = 1
        l2 = candidateSequenceLength
    else:
        call = '{0} {1} -c {2}'.format(bowtiePath, refGenome, candidateSequence[0:100])
        l1 = -candidateSequenceLength + 101
        l2 = 100
    stdout_value, stderr_value = bowtieSearch(call)
    zeroBasePosition = stdout_value.split('	')[1:4] # Results in array like ['+', '21', '33031934']
    try:
    	if zeroBasePosition[0] == '+':
        	candidateSequenceLocation = [zeroBasePosition[0], zeroBasePosition[1], int(zeroBasePosition[2]) + 1, int(zeroBasePosition[2]) + candidateSequenceLength ,candidateSequenceLength]
        else:
        	candidateSequenceLocation = [zeroBasePosition[0], zeroBasePosition[1], int(zeroBasePosition[2]) + l1, int(zeroBasePosition[2]) + l2, candidateSequenceLength]      
        print "Located candidate sequence genomic position: {0[1]}:{0[2]}-{0[3]} with a length of: {0[4]}".format(candidateSequenceLocation)
    except IndexError:
        candidateSequenceLocation = ['','','',candidateSequenceLength]
        print "Failed to locate candidate sequence in reference genome"
    return candidateSequenceLocation


def main(args):
    refGenomeDir = config.get('important','ref_genome_dir')
    global bowtiePath
    bowtiePath = config.get('important','bowtie_bin')
    #Defaults values
    faPath = 'input.fa'
    refGenome = 'GRCh37'
    mismatches = 2;
    rule =  'xxxxxxxxxxxxXXXXXNGG'
    filter = 'NNNNNNNNNNNNNNNNNNRG'
    iupacdict = {
    'M':'[AC]',
    'R':'[AG]',
    'W':'[AT]',
    'S':'[CG]',
    'Y':'[CT]',
    'K':'[GT]',
    'V':'[ACG]',
    'H':'[ACT]',
    'D':'[AGT]',
    'B':'[CGT]',
    'N':'[ACGT]',
    'G':'G',
    'A':'A',
    'T':'T',
    'C':'C',
    }

    #Argument parser
    parser = argparse.ArgumentParser(
        description="Searches a candidate gene for potential targets and generates a list of likely off-targets for each target.")

    #Positional arguments
    parser.add_argument('-f','--faPath',default=faPath,help="Relative path of a text file containing \
            DNA sequence, the candidate genomic region. The file must contain only standard DNA characters\
            (ACTG) and only one sequence, optionally with a FASTA description line. (default: {0})".format(faPath))
    parser.add_argument('-g','--refGenome',default=refGenome,help="The name of a Bowtie indexed reference genome. (default: {0})".format(refGenome))

    #Optional arguments
    parser.add_argument('-n','--name',default='command-line job',help="A job description. This will be present on the output file.")
    parser.add_argument('-r', '--rule', default = rule,
                        help='The rule defines the sequences that GT-Scan will consider as candidate targets, and subsequently,\
                        potential off-targets. Allowed characters are AaCcGgTtXxN.\
                        A string from the candidate sequence is required to match the rule at AaCcGgTt positions, to be considered a candidate target.\
                        A string from the reference genome will be considered a potential off-target if it matches a candidate target at AaCcGgTtXx positions. \
                        A match between these two strings at N positions is not required. \
                        (default: {0})'.format(rule))
    parser.add_argument('-o', '--offtargetfilter', default = filter,
                        help='The off-target filter removes anything that does not match the iUPAC string.\
                        	(default: {0})'.format(filter))
    parser.add_argument('-m', '--mismatches', type=int, choices=xrange(4), default=mismatches,
                        help='This value specifies the maximum number of mismatches allowed in H positions, \
                            for that potential off-target to be be present in the results. \
                            (default: {0})'.format(mismatches))
    args = parser.parse_args()


    # Format the user's inputs
    args.offtargetfilter = args.offtargetfilter.upper()
    filterRegexString = ""
    for n in args.offtargetfilter:
        filterRegexString += iupacdict[n]
    filterRegex = re.compile(filterRegexString)

    # This is to parse the genome list from config.ini to work with Ensembl
    try:
        refGenomeInfo = config.get('ref_genomes',args.refGenome)
        ucscVars = refGenomeInfo.split('|')[1]
    except:
        ucscVars = args.refGenome

    #important functions that do stuff
    whereabouts = findCandidateSequenceInfo(args.faPath, os.path.join(refGenomeDir, args.refGenome))
    descriptor = getCandidateSequenceDescriptor(args.faPath)
    candidateTargets = findCandidateTargets(args.rule, args.faPath)
    potentialOffTargetStrings = createPotentialOffTargetStrings(args.rule, candidateTargets)
    offTargSummary, potentialOffTargets = filterPotentialOffTargets(
        os.path.dirname(args.faPath), potentialOffTargetStrings, os.path.join(refGenomeDir,args.refGenome), args.mismatches, args.rule, filterRegex, args.mismatches, whereabouts)
    insertIntoDB(
        candidateTargets, potentialOffTargets, offTargSummary, args.rule, args.offtargetfilter, int(args.mismatches), whereabouts, args.name, args.refGenome, descriptor, ucscVars)
    out_path = os.path.dirname(args.faPath)
    if offline == True: # Create a single HTML file if the online flag in config.ini is set to false
        dbToHtml(out_path)
        dbToCsv(out_path)
    con.close() #Close the database connection
    print 'DONE'


#Set startTime as a global var
startTime = time.time()

if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser() # New config object, 'config'
    config.readfp(open(os.path.join(base_path, 'config.ini'))) #Parse config.ini
    #Set a few things for online/offline mode
    if config.get('important','online_mode') != '0':
        con = db.connect('crispr.db') #Front-end requires this file to be called crispr.db
        offline = False
    else:
        con = db.connect('/tmp/gtscan.db/gtscan{0}{1}.db'.format(int(time.time()), float(random.random())))
        offline = True

    cur = con.cursor()
    cur.execute("PRAGMA synchronous = OFF")
    #Creates tmp dir if it doesn't exist
    if not os.path.isdir('tmp'):
        os.makedirs('tmp')
    #Launch Main def
    main(sys.argv)
