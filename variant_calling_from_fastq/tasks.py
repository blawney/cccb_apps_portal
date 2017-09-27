# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery.decorators import task
import time
import subprocess
import os
import shutil
import glob
import datetime
import email_utils
from rnaseq.plot_methods import volcano_plot
from google.cloud import storage
from django.conf import settings
from download.models import Resource
from client_setup.models import Project
import pandas as pd
import yaml

LINK_ROOT = 'https://storage.cloud.google.com/%s/%s'
#TODO put this in settings.py?  can a non-app access?

@task(name='check_completion')
def check_completion(project_pk, code_serialized, bucket_name):
    '''

    params
    project_pk: 
    code_map:
    bucket_name: bucket name
    '''
    gcloud = "/srv/gcloud/google-cloud-sdk/bin/gcloud"
    print "DEBUG project_pk:", project_pk
    print "DEBUG SERIALIZED:", code_serialized
    print "DEBUG bucket_name:", bucket_name
    code_map = [c.split('`') for c in code_serialized.split('|')]
    while code_map:
        indices_to_del = []
        for i, code_info_map in enumerate(code_map):
            code, samplename, bamfilename, vcffilename, cloud_dge_dir = code_info_map
            script = ' '.join([settings.GCLOUD_PATH,
                               "alpha genomics operations describe",
                               code,
                               "--format='yaml(done, error, metadata.events)'"])
            proc = subprocess.Popen(script, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            stdout, _ = proc.communicate()
            print "DEBUG status stdout: %s" % stdout
            out_map = yaml.safe_load(stdout)
            print "DEBUG status yaml:", out_map
            done_status = out_map["done"]
            #errors[code] = out_map["error"]
            # setting up file locations
            if done_status == True:
                # data format may be altered:
                #samplename = code_info_map["samplename"]
                #vcffilename = code_info_map["vcffilename"]
                #cloud_dge_dir = code_info_map["bucket_path"]
                #samplename, vcffilename, cloud_dge_dir = code_info_map # fix this!!!
                project = Project.objects.get(pk=project_pk)
                storage_client = storage.Client()
                bucket = storage_client.get_bucket(bucket_name)
                # ToDo fix the path to file (must be sent to app)
                vcf_destination = os.path.join(cloud_dge_dir,
                                               os.path.basename(vcffilename))
                vcf_blob = bucket.blob(vcf_destination)
                bam_destination = os.path.join(cloud_dge_dir,
                                               os.path.basename(bamfilename))
                bam_blob = bucket.blob(bam_destination)
                print "DEBUG bucket.name: ", bucket.name
                print "DEBUG vcf_blob.name: ", vcf_blob.name
                print "DEBUG LINK_ROOT: ", LINK_ROOT
                vcf_public_link = LINK_ROOT % (bucket.name,
                                               '/'.join(["GATK_HaplotypeCaller", vcf_blob.name]))
                bam_public_link = LINK_ROOT % (bucket.name,
                                               '/'.join(["GATK_HaplotypeCaller", bam_blob.name]))
                print "DEBUG public_link: ", vcf_public_link, bam_public_link
                r = Resource(project=project,
                             basename=samplename,
                             public_link=vcf_public_link,
                             resource_type='VCF files')
                r.save()
                r = Resource(project=project,
                             basename=samplename,
                             public_link=bam_public_link,
                             resource_type='BAM files')
                r.save()
                indices_to_del.append(i)
        code_map = [j for i, j in enumerate(code_map) if i not in indices_to_del]
        time.sleep(600)
    project.completed = True
    project.in_progress = False
    project.has_downloads = True
    project.status_message = "Completed variant calling"
    project.save()
    message_html = """
    <html>
    <body>
    Your variant calling analysis has finished. Log-in to download your results.
    </body>
    </html>
    """
    email_utils.send_email(os.path.join(settings.BASE_DIR, settings.GMAIL_CREDENTIALS), message_html, [project.owner.email,], \
                           '[CCCB] Variant calling analysis completed')

