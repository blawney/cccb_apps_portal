from google.cloud import storage
import googleapiclient.discovery
import os
import shutil
import glob
import json
import urllib
import urllib2
from ConfigParser import SafeConfigParser
import sys
import datetime
import re
import subprocess

import pandas as pd

sys.path.append(os.path.abspath('..'))
import email_utils
from client_setup.models import Project, Sample
from download.models import Resource

from django.conf import settings
from django.urls import reverse

import plot_methods

CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.cfg')
CALLBACK_URL = 'analysis/notify/'

DEFAULT_FILTER_LEVELS = ['sort.primary',]
RAW_COUNT_PREFIX = 'raw_counts'
DGE_FOLDER = 'dge'
STAR_LOG_SUFFIX = '.Log.final.out'
MAPPING_COMPOSITION_PLOT = 'mapping_composition.pdf'
TOTAL_READS_PLOT = 'total_reads.pdf'

def parse_config():
    with open(CONFIG_FILE) as cfg_handle:
        parser = SafeConfigParser()
        parser.readfp(cfg_handle)
        return parser.defaults()


def setup(project_pk, config_params):
    
    # note that project was already confirmed for ownership previously.  No need to check here.
    project = Project.objects.get(pk=project_pk)

    # get the reference genome
    reference_genome = project.reference_organism.reference_genome
    config_params['reference_genome'] = reference_genome

    bucket_name = project.bucket
    
    # get datasources from db:
    datasources = project.datasource_set.all()
    datasource_paths = [os.path.join(bucket_name, x.filepath) for x in datasources]
    datasource_paths = [config_params['gs_prefix'] + x for x in datasource_paths]

    # check that those datasources exist in the actual bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    all_contents = bucket.list_blobs()
    uploads = [x.name for x in all_contents if x.name.startswith(config_params['upload_folder'])]
    
    # compare-- it's ok if there were more files in the bucket
    bucket_set = set(uploads)
    datasource_set = set(datasource_paths)
    if len(datasource_set.difference(uploads)) > 0:
        # TODO raise exception
        pass

    # create the output bucket
    result_bucket_name = os.path.join(bucket_name, config_params['output_bucket'])
    #result_bucket = storage_client.create_bucket(result_bucket_name)

    # get the mapping of samples to data sources:
    sample_mapping = {}
    all_samples = project.sample_set.all()
    for s in all_samples:
        sample_mapping[(s.pk, s.name)] = []
    for ds in datasources:
        if ds.sample in all_samples:
            sample_mapping[(ds.sample.pk, ds.sample.name)].append(ds)

    # just in case, remove any empty samples:
    final_mapping = {}
    for key, vals in sample_mapping.items():
        if len(vals) > 0:
            final_mapping[key] = vals
    return project, result_bucket_name, final_mapping


def get_internal_ip():
    url = 'http://metadata/computeMetadata/v1/instance/network-interfaces/0/ip'
    request = urllib2.Request(url)
    request.add_header('X-Google-Metadata-Request', 'True')
    response = urllib2.urlopen(request)
    result = response.read()
    return result


def launch_workers(compute, project, result_bucket_name, sample_mapping, config_params):
    """
    sample_mapping is a dict with a (int,str) tuple (sample PK, sample name) as the key, pointing at a list of DataSource objects
    """
    # first, check that they list of DataSource objects are all the same length:
    length_list = []
    for sample_tuple, ds_list in sample_mapping.items():
        length_list.append(len(ds_list))
    lengthset = set(length_list)
    if len(lengthset) != 1:
        # TODO not all paired or single- raise error
        pass

    input_bucket_name = project.bucket
    for sample_tuple, ds_list in sample_mapping.items():
        file_list = sorted([config_params['gs_prefix'] + os.path.join(input_bucket_name, ds.filepath) for ds in ds_list])
        kwargs = {}
        kwargs['r1_fastq'] = file_list[0]
        kwargs['r2_fastq'] = ''
        # if paired
        if len(file_list) == 2:
            kwargs['r2_fastq'] = file_list[1]
        elif len(file_list) > 2:
            #TODO: something weird happened
            pass
        # now add the other params to the dictionary:
        kwargs['result_bucket_name'] = config_params['gs_prefix'] + result_bucket_name
        kwargs['reference_genome'] = config_params['reference_genome']
        kwargs['email_utils'] = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['email_utils'])
        kwargs['email_credentials'] = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['email_credentials'])
        kwargs['sample_name'] = sample_tuple[1] 
        kwargs['genome_config_path'] = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['genome_config_file'])
        kwargs['align_script_template'] = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['align_script_template'])
        kwargs['project_pk'] = project.pk
        kwargs['sample_pk'] = sample_tuple[0]
        kwargs['callback_url'] = '%s/%s' % (settings.HOST, CALLBACK_URL)
        kwargs['startup_script'] = config_params['gs_prefix'] + os.path.join(config_params['startup_bucket'], config_params['startup_script'])
        kwargs['notification_email_addresses'] = config_params['notification_email_addresses']
        kwargs['token'] = settings.TOKEN
        kwargs['enc_key'] = settings.ENCRYPTION_KEY
        instance_name = 'worker-%s-%s' % (sample_tuple[1].lower().replace('_','-'), datetime.datetime.now().strftime('%m%d%y%H%M%S'))
        launch_custom_instance(compute, config_params['google_project'], config_params['default_zone'], instance_name, kwargs, config_params)


def launch_custom_instance(compute, google_project, zone, instance_name, kwargs, config_params):

    result_bucket_name = kwargs['result_bucket_name']
    sample_name = kwargs['sample_name']
    r1_fastq = kwargs['r1_fastq']
    r2_fastq = kwargs['r2_fastq']
    reference_genome = kwargs['reference_genome']
    genome_config_path = kwargs['genome_config_path']
    align_script_template = kwargs['align_script_template']
    startup_script_url = kwargs['startup_script']
    cccb_project_pk = kwargs['project_pk']
    sample_pk = kwargs['sample_pk']
    callback_url = kwargs['callback_url']
    email_utils = kwargs['email_utils']
    email_credentials = kwargs['email_credentials']
    notification_email_addresses = kwargs['notification_email_addresses']
    token = kwargs['token']
    enc_key = kwargs['enc_key']
    source_disk_image = 'projects/%s/global/images/%s' % (config_params['google_project'], config_params['image_name'])

    machine_type = "zones/%s/machineTypes/%s" % (zone, config_params['machine_type']) 

    config = {
        'name': instance_name,
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/compute',
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write'
            ]
        }],
 
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script-url',
                'value': startup_script_url
            },
            {
              'key':'result_bucket_name',
              'value': result_bucket_name
            },
            {
              'key':'sample_name',
              'value': sample_name
            },
            {
              'key':'r1_fastq',
              'value': r1_fastq
            },
            {
              'key':'r2_fastq',
              'value': r2_fastq
            },
            {
              'key':'reference_genome',
              'value': reference_genome
            },
            {
              'key':'genome_config_path',
              'value': genome_config_path
            },
            {
              'key':'align_script_template',
              'value': align_script_template
            },
            {
              'key':'google_project',
              'value': config_params['google_project']
            },
            {
              'key':'google_zone',
              'value': config_params['default_zone']
            },
            {
              'key':'project_pk',
              'value': cccb_project_pk
            },
            {
              'key':'sample_pk',
              'value': sample_pk
            },
            {
                'key':'callback_url',
                'value': callback_url
            },
	    {
              'key':'email_utils',
              'value': email_utils
            },
	    {
              'key':'email_credentials',
              'value': email_credentials
            },
            {
              'key':'notification_email_addresses',
              'value':notification_email_addresses
            },
            {
              'key':'token',
              'value':token
            },            {
              'key':'enc_key',
              'value':enc_key
            }

          ]
        }
    }

    return compute.instances().insert(
        project=google_project,
        zone=zone,
        body=config).execute()


def start_analysis(project_pk):
    config_params = parse_config()
    project, result_bucket_name, sample_mapping = setup(project_pk, config_params)
    compute = googleapiclient.discovery.build('compute', 'v1')
    launch_workers(compute, project, result_bucket_name, sample_mapping, config_params)


def create_merged_counts(bucket, countfile_objs, local_dir):
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
    for level in DEFAULT_FILTER_LEVELS:
        d2[level] = d[level]

    raw_count_files = []
    for k,files in d2.items():
        overall = pd.DataFrame()
        outfile = os.path.join(local_dir, '%s.%s.tsv' % (RAW_COUNT_PREFIX, k))
        cols = []
        for f in files:
            cols.append(os.path.basename(f).split('.')[0])
            df = pd.read_table(f, skiprows=1, index_col=0)
            df = df.ix[:,-1]
            overall = pd.concat([overall, df], axis=1)
        overall.columns = cols
        overall.to_csv(outfile, sep='\t', index_label='Gene')
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

def finish(project):
    """
    This pulls together everything and gets it ready for download
    """
    config_params = parse_config()

    LINK_ROOT = 'https://storage.cloud.google.com/%s/%s' #TODO put this in settings.py?  can a non-app access?

    all_samples = project.sample_set.all()
    
    storage_client = storage.Client()
    bucket_name = project.bucket
    bucket = storage_client.get_bucket(bucket_name)
    all_contents = bucket.list_blobs()
    all_contents = [x for x in all_contents] # turn the original iterator into a list

    print 'all contents: %s' % all_contents
    # find all the BAM files (note regex below-- could expose a subset of the BAM files for ease)
    bam_objs = []
    for fl in DEFAULT_FILTER_LEVELS:
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
    for fl in DEFAULT_FILTER_LEVELS:
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
        os.mkdir(local_dir)
    except OSError as ex:
        if ex.errno == 17:
            pass
        else:
            print ex.message
            raise ex
    raw_count_filepaths = create_merged_counts(bucket, countfile_objs, local_dir)

    # upload count files for use when performing DGE analysis
    for rc in raw_count_filepaths:
        destination = os.path.join(config_params['output_bucket'], DGE_FOLDER, os.path.basename(rc))
        rc_blob = bucket.blob(destination)
        rc_blob.upload_from_filename(rc)



    # make some plots/QC
    star_log_pattern = '.*%s$' % STAR_LOG_SUFFIX
    star_logs = [x for x in all_contents if re.match(star_log_pattern, x.name) is not None]
    report_pdf_path = make_qc_report(star_logs, local_dir)

    # grab the raw count files:
    local_files_to_zip = []
    local_files_to_zip.extend(glob.glob(os.path.join(local_dir, '%s*' % RAW_COUNT_PREFIX)))
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


def handle(project, request):
    """
    This is not called by any urls, but rather the request object is forwarded on from a central "distributor" method
    project is a Project object/model
    """
    print 'handling project %s' % project
    sample_pk = int(request.POST.get('samplePK', '')) #exceptions can be caught in caller
    print 'sample_pk=%s' % sample_pk
    sample = Sample.objects.get(pk = sample_pk)
    print 'here?'*10
    sample.processed = True
    sample.save()

    print 'saved'
    # now check to see if everyone is done
    all_samples = project.sample_set.all()
    if all([s.processed for s in all_samples]):
        print 'All samples have completed!'
        project.in_progress = False
        project.paused_for_user_input = True
        project.completed = True
        project.status_message = 'Completed alignments'
	project.next_action_text = 'Perform differential expression'
	project.next_action_url = reverse('dge', kwargs={'project_pk':project.pk})
	project.has_downloads = True
        project.save()
        finish(project)
