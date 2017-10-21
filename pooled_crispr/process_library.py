"""
This script takes in a library spec for pooled CRISPR screens
We require at least two columns.  While not strictly necessary, we 
do not want just a list of sequences.  
1.  Some kind of identifier.  If it is not unique (e.g. genes where 
    a single gene can have multiple targets) then we will create a hybrid
    ID which includes this gene name and an additional string that will collectively
    make a unique identifier.

2.  The sequence, typically 20nt.  Should NOT include the PAM


Both of these recommendations are based on the resources available on the addgene site.
Unfortunately they do not distribute in a consistent format, so we require only a minimum
amount of information 

"""

import sys
import re
import pandas as pd

# paths to the input file and the output fasta file:
input = sys.argv[1]
output_fasta = sys.argv[2]

# the extension can (in theory) tell us what sort of file we are dealing with
suffix = input.split('.')[-1].lower()

if suffix == 'xlsx' or suffix == 'xls':
	df = pd.read_excel(input, header=True)
elif suffix == 'tsv':
	df = pd.read_table(input, sep='\t')
elif suffix == 'csv':
	df = pd.read_table(input, sep=',', header=True)
else:
	sys.stderr.write('Could not determine file format.  Please use Excel (xls, xlsx), tsv, or csv.\n')
	sys.exit(1)

if df.shape[1] < 2:
	sys.stderr.write('Need at least two columns-- some identifier and the sgRNA target itself.\n')
	sys.exit(1)

# if 3 or more columns were given, then ignore those
if df.shape[1] >= 3:
	sys.stdout.write('Warning: You have given more than two columns.  The first two will be used and the rest will be ignored.\n')
	df = df.ix[:,:2]
print df
# check for Excel-induced time stamp conversions:
pattern = '\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}' # e.g. 2016-03-04 00:00:00
if pd.np.any(map(lambda x: len(re.findall(pattern, x)) > 0, df.ix[:,0])):
	sys.stdout.write("""
			Warning: Some of the identifiers have been converted into a date stamp format.\n
			This is usually due to conversion of gene names into dates by Excel.  We cannot guess these, but
			please be aware.\n
			""")


# if the first column does not contain unique identifiers, append to make them unique:
if len(df.ix[:,0].unique()) < df.shape[0]:
	sys.stdout.write('We have detected that the first column of identifiers does not have unique values.\nWe will create a default instead.')
	extra = map(lambda x: '_sgRNA_%s' % x, df.index.values)
	df.ix[:,0] = df.ix[:,0].astype('str') + extra
	
	# confirm just to be sure:
	if len(df.ix[:,0].unique()) < df.shape[0]:
		sys.stderr.write('Still could not create a unique set of identifiers.  Stopping\n')
		sys.exit(1)

# at this point we have a two column dataframe with unique identifers in the first column and sequences in the second, although 
# those have not been checked.  Make a fasta file:
def convert_to_fasta(row):
	return '>%s\n%s' % (row[0], row[1])

fasta_series = df.apply(convert_to_fasta, axis=1)
with open(output_fasta, 'w') as fout:
	fout.write('\n'.join(fasta_series))
sys.stdout.write('Wrote fasta file.\n')

