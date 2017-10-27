# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery.decorators import task
import subprocess
import os
import shutil
import glob
import datetime
import re
import email_utils
import jinja2
from rnaseq.plot_methods import volcano_plot, plot_read_composition, plot_total_read_count
import rnaseq.config_parser as cp_
from google.cloud import storage
from django.conf import settings
from download.models import Resource
from client_setup.models import Project
import pandas as pd

LINK_ROOT = settings.PUBLIC_STORAGE_ROOT + '%s/%s'

@task(name='deseq_call')
def deseq_call(deseq_cmd, results_dir, cloud_dge_dir, count_matrix_filename, annotation_filename, contrast_name, bucket_name, project_pk):
	p = subprocess.Popen(deseq_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	stdout, stderr = p.communicate()
	if p.returncode != 0:
		with open(os.path.join(results_dir, 'deseq_error.log'), 'w') as fout:
			fout.write('STDOUT:\n%s\n' % stdout)
			fout.write('STDERR:\n%s' % stderr)
		#TODO send error email to CCCB
		email_list = [x.strip() for x in settings.CCCB_EMAIL_CSV.split(',')]
		email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), "There was a problem with the deseq analysis.  Check the %s directory" % results_dir, email_list, '[CCCB] Problem with DGE script')
	else:

		project = Project.objects.get(pk=project_pk)

		storage_client = storage.Client()
		bucket = storage_client.get_bucket(bucket_name)

		project_owner = project.owner.email

		# make a cls file for GSEA:
		raw_count_matrix_filepath = os.path.join(results_dir, count_matrix_filename)
		df = pd.read_table(raw_count_matrix_filepath)
		samples = df.columns.tolist()[1:] # Gene is first column

		# annotation file has two columns, first is sample name second is group
		annotations = pd.read_table(os.path.join(results_dir, annotation_filename), index_col=0)
		group_list = annotations.ix[samples].dropna() # sorts the annotation rows to match the column order of the count matrix
		unique_groups = group_list.ix[:,0].unique()
		group_list_str = '\t'.join(group_list.ix[:,0]) # only column left is the group vector, so ok to use 0.  Avoids referencing by name
		with open(os.path.join(results_dir, 'groups.cls'), 'w') as cls_outfile:
			cls_outfile.write('%d\t%d\t1\n' % (group_list.shape[0], len(unique_groups)))
			cls_outfile.write('#\t%s\t%s\n' % (unique_groups[0], unique_groups[1]))
			cls_outfile.write(group_list_str + '\n')

		# make some plots
		for f in glob.glob(os.path.join(results_dir, '*deseq.tsv')):
			output_figure_path = f.replace('deseq.tsv', 'volcano_plot_v2.pdf')
			dge_df = pd.read_table(f, sep=b'\t')
			volcano_plot(dge_df, output_figure_path)


		# zip everything up
		zipfile = os.path.join(settings.TEMP_DIR, '%s-%s.zip' % (contrast_name, datetime.datetime.now().strftime('%H%M%S')))
		zip_cmd = 'zip -rj %s %s' % (zipfile, results_dir)
		print 'zip up using command: %s' % zip_cmd
		p = subprocess.Popen(zip_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		stdout, sterr = p.communicate()
		if p.returncode != 0:
			#TODO: send email to cccb?  Shouldn't happen and not a user error.
			pass
		# the name relative to the bucket
		destination = os.path.join(cloud_dge_dir, os.path.basename(zipfile))
		zip_blob = bucket.blob(destination)
		zip_blob.upload_from_filename(zipfile)
		acl = zip_blob.acl
		entity = acl.user(project_owner)
		entity.grant_read()
		acl.save()

		# remove the file locally
		os.remove(zipfile)

		# change the metadata so the download does not append the path 
		set_meta_cmd = 'gsutil setmeta -h "Content-Disposition: attachment; filename=%s" gs://%s/%s' % (os.path.basename(zipfile), bucket.name, destination)
		process = subprocess.Popen(set_meta_cmd, shell = True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
		stdout, stderr = process.communicate()
		if process.returncode != 0:
			print 'There was an error while setting the metadata on the zipped archive with gsutil.  Check the logs.  STDERR was:%s' % stderr
			raise Exception('Error during gsutil upload module.')
		shutil.rmtree(results_dir)

		# register the zip archive with the download app
		public_link = LINK_ROOT % (bucket.name, zip_blob.name)
		r = Resource(project=project, basename = os.path.basename(zipfile), public_link = public_link, resource_type = 'Compressed results')
		r.save()

		project.status_message = 'Completed DGE analysis'
		project.in_progress = False
		project.save()

		message_html = """
		<html>
		<body>
		Your differential analysis has finished.  Log-in to download your results
		</body>
		</html>
		"""
		email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project_owner,], '[CCCB] Differential gene expression analysis completed')


@task(name='finish_alignment_work')
def finish_alignment_work(project_pk):
    """
    This pulls together everything and gets it ready for download
    """
    config_params = cp_.parse_config()
    print 'In finish_alignment_work, config params='
    print config_params

    project = Project.objects.get(pk=project_pk)

    all_samples = project.sample_set.all()
    
    storage_client = storage.Client()
    bucket_name = project.bucket
    bucket = storage_client.get_bucket(bucket_name)
    all_contents = bucket.list_blobs()
    all_contents = [x for x in all_contents] # turn the original iterator into a list

    print 'all contents: %s' % all_contents
    # find all the BAM files (note regex below-- could expose a subset of the BAM files for ease)
    bam_objs = []
    for fl in config_params['default_filter_levels']:
        bam_pattern = '%s/.*%s.bam$' % (config_params['output_bucket'],fl)
        bam_objs.extend([x for x in all_contents if re.match(bam_pattern, x.name) is not None])

        # also add the .bai files:
        bai_pattern = '%s/.*%s.bam.bai$' % (config_params['output_bucket'],fl)
        bam_objs.extend([x for x in all_contents if re.match(bai_pattern, x.name) is not None])

    # add user's privileges to these:
    for b in bam_objs:
        print 'grant ownership on bam %s' % b
        acl = b.acl
        entity = acl.user(project.owner.email)
        entity.grant_read()
        acl.save()

        # register the BAM files with the download app
        public_link = LINK_ROOT % (bucket.name, b.name)
        r = Resource(project=project, basename = os.path.basename(b.name), public_link = public_link, resource_type = 'BAM Files')
        r.save()

        set_meta_cmd = 'gsutil setmeta -h "Content-Disposition: attachment; filename=%s" gs://%s/%s' % (os.path.basename(b.name), bucket_name, b.name)
        print 'set meta cmd: %s' % set_meta_cmd
        process = subprocess.Popen(set_meta_cmd, shell = True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
             print 'Error while setting metadata on bam %s. STDERR was:\n %s' % (b.name, stderr)
             raise Exception('Error during gsutil upload module.')


    # find all the count files
    countfile_objs = []
    for fl in config_params['default_filter_levels']:
        countfiles_pattern = '%s/.*%s.counts$' % (config_params['output_bucket'], fl)
        countfile_objs.extend([x for x in all_contents if re.match(countfiles_pattern, x.name) is not None])
    # add user's privileges to these:
    for b in countfile_objs:
        acl = b.acl
        entity = acl.user(project.owner.email)
        entity.grant_read()
        acl.save()

    # concatenate count files
    local_dir = os.path.join(settings.TEMP_DIR, bucket.name)
    try:
        os.makedirs(local_dir)
    except OSError as ex:
        if ex.errno == 17:
            pass
        else:
            print ex.message
            raise ex
    raw_count_filepaths = create_merged_counts(bucket, countfile_objs, local_dir, config_params)

    # upload count files for use when performing DGE analysis
    for rc in raw_count_filepaths:
        destination = os.path.join(config_params['output_bucket'], config_params['dge_folder'], os.path.basename(rc))
        rc_blob = bucket.blob(destination)
        rc_blob.upload_from_filename(rc)



    # make some plots/QC
    star_log_pattern = '.*%s$' % config_params['star_log_suffix']
    star_logs = [x for x in all_contents if re.match(star_log_pattern, x.name) is not None]
    report_pdf_path = make_qc_report(star_logs, local_dir, config_params)

    # grab the raw count files:
    local_files_to_zip = []
    local_files_to_zip.extend(glob.glob(os.path.join(local_dir, '%s*' % config_params['raw_count_prefix'])))
    local_files_to_zip.append(report_pdf_path)

    # zip them up:
    #zipfile = os.path.join(local_dir, bucket_name + '-results.zip') 
    timestamp = datetime.datetime.now().strftime('%m%d%y%H%M%S')
    zipfile = os.path.join(local_dir, 'alignment-results.%s.zip' % timestamp) 
    
    zip_cmd = 'zip -j %s %s' % (zipfile, ' '.join(local_files_to_zip))
    print 'zip up using command: %s' % zip_cmd
    p = subprocess.Popen(zip_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, sterr = p.communicate()
    if p.returncode != 0:
        #TODO: send email to cccb?  Shouldn't happen and not a user error.
        pass

    # upload the archive and give it permissions:
    destination = os.path.join(config_params['output_bucket'], os.path.basename(zipfile))
    zip_blob = bucket.blob(destination)
    zip_blob.upload_from_filename(zipfile)
    acl = zip_blob.acl
    entity = acl.user(project.owner.email)
    entity.grant_read()
    acl.save()

    # change the metadata so the download does not append the path 
    set_meta_cmd = 'gsutil setmeta -h "Content-Disposition: attachment; filename=%s" gs://%s/%s' % (os.path.basename(zipfile), bucket_name, destination)
    process = subprocess.Popen(set_meta_cmd, shell = True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print 'There was an error while setting the metadata on the zipped archive with gsutil.  Check the logs.  STDERR was:%s' % stderr
        raise Exception('Error during gsutil upload module.')

    shutil.rmtree(local_dir)

    # register the zip archive with the download app
    public_link = LINK_ROOT % (bucket.name, zip_blob.name)
    r = Resource(project=project, basename = os.path.basename(zipfile), public_link = public_link, resource_type = 'Compressed results')
    r.save()

    # notify the client
    # the second arg is supposedd to be a list of emails
    print 'send notification email'
    message_html = write_completion_message(project)
    email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project.owner.email,], '[CCCB] Your RNA-Seq analysis has completed')


def write_completion_message(project):
    message_html = """\
    <html>
      <head></head>
      <body>
          <p>
            Your RNA-Seq analysis (%s) is complete!  Log-in to the CCCB application site to view and download your results.
          </p>
      </body>
    </html>
    """ % project.name
    return message_html


def create_merged_counts(bucket, countfile_objs, local_dir, config_params):
    """
    Downloads and concatenates the count files into a raw count matrix
    """

    # download the files
    countfile_paths = []
    for cf in countfile_objs:
        filepath = os.path.join(local_dir, os.path.basename(cf.name))
        print 'download from %s to %s' % (cf.name, filepath)
        cf.download_to_filename(filepath)
        countfile_paths.append(filepath)

    # concatenate the different 'levels' of count file
    styles = ['.'.join(x.split('.')[1:-1]) for x in countfile_paths]
    df = pd.DataFrame({'files':countfile_paths, 'filetype':styles})
    d = {}
    for grouping, f in df.groupby('filetype'):
        d[grouping] = sorted(f.files.tolist())

    # subset the count 'levels' so we don't confuse the users with too many files.  Just pick the ones corresponding to DEFAULT_FILTER_LEVELS
    d2 = {}
    for level in config_params['default_filter_levels']:
        d2[level] = d[level]

    raw_count_files = []
    for k,files in d2.items():
        overall = pd.DataFrame()
        outfile = os.path.join(local_dir, '%s.%s.tsv' % (config_params['raw_count_prefix'], k))
        cols = []
        for f in files:
            cols.append(os.path.basename(f).split('.')[0])
            df = pd.read_table(f, skiprows=1, index_col=0)
            df = df.ix[:,-1]
            overall = pd.concat([overall, df], axis=1)
        overall.columns = cols
        overall.to_csv(outfile, sep=b'\t', index_label='Gene')
        raw_count_files.append(outfile)
    return raw_count_files

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
    return d

def make_qc_report(logfile_objs, local_dir, config_params):
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
        sample = os.path.basename(log)[:-len(config_params['star_log_suffix'])]
        log_data[sample] = get_log_contents(log)

    # plot the read composition (uniquely, multi-mapped, etc)
    targets =[ 'Uniquely mapped reads %', '% of reads mapped to multiple loci', '% of reads mapped to too many loci', '% of reads unmapped: too many mismatches', '% of reads unmapped: too short', '% of reads unmapped: other']
    mapping_composition_colors = ['#504244', '#84C85C', '#A663B7', '#C2504C', '#95B8B8', '#B59547']
    plot_read_composition(log_data, targets, os.path.join(local_dir, config_params['mapping_composition_plot']), mapping_composition_colors)

    # plot the total number of reads:
    plot_total_read_count(log_data, os.path.join(local_dir, config_params['total_reads_plot']))

    # copy the teX and other files over to the local folder:
    this_dir = os.path.dirname(os.path.realpath(__file__))
    #shutil.copyfile(os.path.join(this_dir, 'report_template.tex'), os.path.join(local_dir, 'report.tex'))
    shutil.copyfile(os.path.join(this_dir, 'references.bib'), os.path.join(local_dir, 'references.bib'))
    shutil.copyfile(os.path.join(this_dir, 'igv_duplicates.png'), os.path.join(local_dir, 'igv_duplicates.png'))
    shutil.copyfile(os.path.join(this_dir, 'igv_typical.png'), os.path.join(local_dir, 'igv_typical.png'))

    # fill in the template tex file:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(this_dir))
    template = env.get_template('report_template.tex')
    context={'mapping_composition': config_params['mapping_composition_plot'], 'total_reads': config_params['total_reads_plot']}
    with open(os.path.join(local_dir, 'report.tex'), 'w') as outfile:
        outfile.write(template.render(context))

    compile_script = os.path.join(this_dir, 'compile.sh')
    args = [compile_script, local_dir, 'report']
    p = subprocess.Popen(args, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    print 'STDOUT from latex compile script: %s' % stdout
    print 'STDERR from latex compile script: %s' % stderr
    if p.returncode != 0:
        print 'Error running the compile script for the latex report.'
        raise Exception('Error running the compile script for the latex report.')
        # the compiled report is simply the project name with the '.pdf' suffix
    pdf_report_path = os.path.join(local_dir, 'report.pdf')
    return pdf_report_path
