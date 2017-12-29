import sys
import gzip

if __name__ == '__main__':
	fq1 = sys.argv[1]
	fq2 = sys.argv[2]
	n = int(sys.argv[3])

	i = 0
	s = 0
	with gzip.open(fq1) as fin:
		while i < n:	
			_ = fin.readline()
			s += len(fin.readline().strip())
			_ = fin.readline()
			_ = fin.readline()
			i += 1
	avg_read_len = s/n
	
	paired = False
	if len(fq2) > 1:
		paired = True
	
	if paired:
		if avg_read_len <= 70:
			overlap = 8
		else:
			overlap = 13
	else:
		if avg_read_len <= 70:
			overlap = 10
		else:
			overlap = 15
	sys.stdout.write(str(overlap))
