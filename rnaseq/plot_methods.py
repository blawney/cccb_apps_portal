import logging
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
import os
import glob
rcParams['font.size'] = 12.0


def get_vals(log_data, t, f):
	"""
	Gets a list of samples and the name of a 'target'.  The target is some information that is contained in the STAR log file (e.g. % Uniquely mapped reads)
	The final argument is a callable-- to process a string and return a value as appropriate
	"""
	vals = []
	for s in log_data.keys():
		vals.append(f(log_data[s][t]))
	return vals


def plot_read_composition(log_data, targets, filename, colors):
	"""
	Plots the relative abundance of alignments for each sample
	Receives a dict of dicts (sample names each mapping to a dictionary of log data about that sample), 
	the 'targets' (which is a list of strings to select data from the dictionary), and the output filepath (full path!)
	"""
	logging.info('Start plot_read_composition(...)')
	samples = log_data.keys()
	N = len(samples)
	width = 10.0
	height = 0.8 * N
	fig = plt.figure(figsize=(width, height))
	ax = fig.add_subplot(111)
	y_pos = np.arange(N)
	prior = np.zeros(N)

	# a method for parsing the data from the logfile to coerce for plotting- strip off the percent sign and cast to a float
	f = lambda x: float(x.strip('%'))

	bar_groups = []
	for i,t in enumerate(targets):
		vals = get_vals(log_data, t, f)
		bar_groups.append(ax.barh(y_pos, vals, align='center', alpha=0.6, left=prior, color=colors[i]))
		prior += vals
    
	ax.legend(bar_groups, targets, loc=9,  bbox_to_anchor=(0.5, -0.5))
	ax.yaxis.set_ticks(y_pos)
	ax.yaxis.set_ticklabels(samples)
	ax.yaxis.set_tick_params(pad=10)
	ax.set_ylim([-0.75, N-0.25])
	ax.set_xlim([0,100])
	ax.set_xlabel('% of total reads')
	font={'family': 'serif', 'size':16}
	plt.rc("font", **font)
	ax.set_title("Read Composition")
	fig.savefig(filename, bbox_inches='tight')
	logging.info('Saved read composition plot to %s' % filename)



def plot_total_read_count(log_data, filename):
	"""
	Plots the total reads for each sample
	Receives a dict of dicts (sample names each mapping to a dictionary of log data about that sample) 
	and the output filepath (full path!)
	"""
	samples = log_data.keys()
	N = len(samples)
	width = 10.0
	height = 0.8 * N
	fig = plt.figure(figsize=(width, height))
	ax = fig.add_subplot(111)
	y_pos = np.arange(N)

	# a method to coerce the data to plot (integers) from the string representation
	f = lambda x: int(x.strip())

	vals = get_vals(log_data, 'Number of input reads', f)
	ax.barh(y_pos, vals, align='center', alpha=0.6)
	    
	ax.yaxis.set_ticks(y_pos)
	ax.yaxis.set_ticklabels(samples)
	ax.yaxis.set_tick_params(pad=10)
	ax.set_ylim([-0.75, N-0.25])
	ax.set_xlabel('Total reads')
	font={'family': 'serif', 'size':16}
	plt.rc("font", **font)
	ax.set_title('Total Input Reads')
	fig.savefig(filename, bbox_inches='tight')
