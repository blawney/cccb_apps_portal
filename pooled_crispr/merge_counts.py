import sys
import glob
import os
import pandas as pd

working_dir = sys.argv[1]
count_suffix = sys.argv[2]
outfile_name = sys.argv[3]

os.chdir(working_dir)

countfiles = glob.glob('*%s' % count_suffix)

sample_list = []
for i,f in enumerate(countfiles):
	sample = f[:-len(count_suffix)]
	df = pd.read_table(f, names=['target','l','nc','junk'])
	df = df.ix[df.target != '*']
	if df.shape[0] == 0:
		print 'There was a problem with sample %s.' % sample
		continue
	df = df[['target','nc']]
	df.columns = ['target', sample]
	df.set_index('target', inplace=True)
	sample_list.append(sample)
	if i == 0:
		overall_df = df
	else:
		overall_df = pd.merge(overall_df, df, left_index=True, right_index=True)
		overall_df.columns = sample_list

overall_df.to_csv(outfile_name, sep='\t')
