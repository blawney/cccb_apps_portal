import os
import shutil
import subprocess
import re
import plot_methods
from google.cloud import storage
STAR_LOG_SUFFIX = '.Log.final.out'
MAPPING_COMPOSITION_PLOT = 'mapping_composition.pdf'
TOTAL_READS_PLOT = 'total_reads.pdf'

def get_log_contents(f):
    """
    Parses the star-created Log file to get the mapping stats.
    Input: filepath to Log file
    Output: dictionary mapping 'log terms' to the values
    """
    d = {}
    for line in open(f):
        try:
            key, val = line.strip().split('|')
            d[key.strip()] = val.strip()
        except ValueError as ex:
            pass
    print 'fromi %s' % f
    print d
    print '*'*50
    return d

def make_qc_report(logfile_objs, local_dir):
    """
    Make a PDF QC report with latex
    """
    # download the log files
    logfile_paths = []
    for lf in logfile_objs:
        filepath = os.path.join(local_dir, os.path.basename(lf.name))
        print 'download from %s to %s' % (lf.name, filepath)
        lf.download_to_filename(filepath)
        logfile_paths.append(filepath)
    # get the log contents and store them in a dictionary keyed by the sample name
    log_data = {}
    for log in logfile_paths:
        sample = os.path.basename(log)[:-len(STAR_LOG_SUFFIX)]
        log_data[sample] = get_log_contents(log)
    # plot the read composition (uniquely, multi-mapped, etc)
    targets =[ 'Uniquely mapped reads %', '% of reads mapped to multiple loci', '% of reads mapped to too many loci', '% of reads unmapped: too many mismatches', '% of reads unmapped: too short', '% of reads unmapped: other']
    mapping_composition_colors = ['#504244', '#84C85C', '#A663B7', '#C2504C', '#95B8B8', '#B59547']
    plot_methods.plot_read_composition(log_data, targets, os.path.join(local_dir, MAPPING_COMPOSITION_PLOT), mapping_composition_colors)
    # plot the total number of reads:

    plot_methods.plot_total_read_count(log_data, os.path.join(local_dir, TOTAL_READS_PLOT))
    # copy the teX and other files over to the local folder:
    this_dir = os.path.dirname(os.path.realpath(__file__))
    shutil.copyfile(os.path.join(this_dir, 'report_template.tex'), os.path.join(local_dir, 'report.tex'))
    shutil.copyfile(os.path.join(this_dir, 'references.bib'), os.path.join(local_dir, 'references.bib'))
    shutil.copyfile(os.path.join(this_dir, 'igv_duplicates.png'), os.path.join(local_dir, 'igv_duplicates.png'))
    shutil.copyfile(os.path.join(this_dir, 'igv_typical.png'), os.path.join(local_dir, 'igv_typical.png'))
    compile_script = os.path.join(this_dir, 'compile.sh')
    args = [compile_script, local_dir, 'report']
    cmd = ' '.join(args)
    print cmd
    p = subprocess.Popen(cmd, shell=True, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        print stderr
        raise Exception('Error running the compile script for the latex report.')
        # the compiled report is simply the project name with the '.pdf' suffix
    pdf_report_path = os.path.join(local_dir + 'report.pdf')
    return pdf_report_path

if __name__ == '__main__':
    storage_client = storage.Client()
    bucket_name = 'cccb-app-service-2-060217-132406'
    bucket = storage_client.get_bucket(bucket_name)
    all_contents = bucket.list_blobs()
    all_contents = [x for x in all_contents] # turn the original iterator into a list

    # TODO make some plots? QC?
    star_log_pattern = '.*%s$' % STAR_LOG_SUFFIX
    star_logs = [x for x in all_contents if re.match(star_log_pattern, x.name) is not None]
    print star_logs
    report_pdf_path = make_qc_report(star_logs, '/webapps/cccb_portal/temp/dummy')

