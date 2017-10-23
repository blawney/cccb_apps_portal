"""
This script is used for populating the database with static data.

For example, the order of operations in the UI is determined by a series of Workflow
steps, which are defined by which Service the project corresponds to.  

Thus, when we startup, we want to easily specify that a RNA-seq service has 5 steps, and define their order
"""
import sys
import os

app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(app_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cccb_portal.settings')

import django
django.setup()

# import the models:
from client_setup.models import Service, Workflow, Organism

###################################### Start variant calling from fastq ##############################################################
svc = Service.objects.get_or_create(name='variant_calling_from_fastq')[0]
svc.description = 'Variant calling starting from FastQ files'
svc.application_url = 'https://cccb-analysis.tm4.org'
svc.upload_instructions = """<p>Manage your files here. Upload or remove your compressed, 
	FASTQ-format files as necessary. In the next step, you can assign the files to 
	particular samples.</p>  <p class="bolded">FastQ file upload:</p>  
	<p>For naming your files, we enforce a particular naming convention which is followed 
	by most sequencing providers. We also require files to be Gzip-compressed to save disk space; 
	files will typically end with "gz" if that is the case.</p>  <p>If your sequencing is 
	single-end protocol, we expect files named like [SAMPLE]_R1.fastq.gz, where [SAMPLE] is 
	your sample's name.</p>  <p>For paired sequencing protocols there will be two files 
	per sample, named [SAMPLE]_R1.fastq.gz and [SAMPLE]_R2.fastq.gz; note the only difference 
	is "R2" to indicate the second of a read pairing.</p>"""
svc.save()

# add the applicable organisms/genome builds:
org = Organism.objects.get_or_create(reference_genome='hg19', service=svc)[0]
org.description = 'Human (hg19) for exome variant calling'
org.save()

workflow_step = Workflow.objects.get_or_create(step_order=0, service=svc)[0]
workflow_step.step_url = 'analysis_home_view'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=1, service=svc)[0]
workflow_step.step_url = 'choose_genome'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=2, service=svc)[0]
workflow_step.step_url = 'generic_upload'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=3, service=svc)[0]
workflow_step.step_url = 'file_annotation'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=4, service=svc)[0]
workflow_step.step_url = 'pre_analysis_summary'
workflow_step.save()

###################################### End variant calling from fastq ##############################################################


###################################### Start variant calling from BAM ##############################################################


svc = Service.objects.get_or_create(name='variant_calling_from_bam')[0]
svc.description = 'GATK Variant-calling, starting from BAM files'
svc.application_url = 'https://cccb-analysis.tm4.org'
svc.upload_instructions = """<p>Manage your files here. Upload or remove your compressed, 
	BAM-format files as necessary. 
	In the next step, you can assign the files to particular samples.</p>  
	<p class="bolded">BAM file upload:</p>  <p>To upload alignment (BAM format) files, 
	we only require that the file end with the "bam" extension, such as [SAMPLE].bam. 
	The sample name will be inferred from the name by removing the extension. 
	For example, the file KB10_Kd1.bam will create a sample with the name "KB10_Kd1".</p>"""
svc.save()

# add the applicable organisms/genome builds:
org = Organism.objects.get_or_create(reference_genome='hg19', service=svc)[0]
org.description = 'Human (hg19) for exome variant calling'
org.save()

workflow_step = Workflow.objects.get_or_create(step_order=0, service=svc)[0]
workflow_step.step_url = 'analysis_home_view'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=1, service=svc)[0]
workflow_step.step_url = 'choose_genome'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=2, service=svc)[0]
workflow_step.step_url = 'generic_upload'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=3, service=svc)[0]
workflow_step.step_url = 'file_annotation'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=4, service=svc)[0]
workflow_step.step_url = 'pre_analysis_summary'
workflow_step.save()

###################################### End variant calling from BAM ##############################################################

###################################### Start RNA-seq ##############################################################

svc = Service.objects.get_or_create(name='rnaseq')[0]
svc.description = 'RNA-Seq alignment and differential gene expression'
svc.application_url = 'https://cccb-analysis.tm4.org'
svc.upload_instructions = """<p>Manage your files here. Upload or remove your compressed, 
	FASTQ-format files as necessary. In the next step, you can assign the files to 
	particular samples.</p>  <p class="bolded">FastQ file upload:</p>  
	<p>For naming your files, we enforce a particular naming convention which is followed 
	by most sequencing providers. We also require files to be Gzip-compressed to save disk space; 
	files will typically end with "gz" if that is the case.</p>  <p>If your sequencing is 
	single-end protocol, we expect files named like [SAMPLE]_R1.fastq.gz, where [SAMPLE] is 
	your sample's name.</p>  <p>For paired sequencing protocols there will be two files 
	per sample, named [SAMPLE]_R1.fastq.gz and [SAMPLE]_R2.fastq.gz; note the only difference 
	is "R2" to indicate the second of a read pairing.</p>"""
svc.save()

# add the applicable organisms/genome builds:
org = Organism.objects.get_or_create(reference_genome='grch38', service=svc)[0]
org.description = 'Human (Homo Sapiens Ensembl GRCh38)'
org.save()

org = Organism.objects.get_or_create(reference_genome='grcm38', service=svc)[0]
org.description = 'Mouse (Mus Musculus Ensembl GRCm38)'
org.save()

workflow_step = Workflow.objects.get_or_create(step_order=0, service=svc)[0]
workflow_step.step_url = 'analysis_home_view'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=1, service=svc)[0]
workflow_step.step_url = 'choose_genome'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=2, service=svc)[0]
workflow_step.step_url = 'generic_upload'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=3, service=svc)[0]
workflow_step.step_url = 'file_annotation'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=4, service=svc)[0]
workflow_step.step_url = 'pre_analysis_summary'
workflow_step.save()

###################################### End RNA-seq ##############################################################

###################################### Start Pooled CRISPR  ##############################################################

svc = Service.objects.get_or_create(name='pooled_crispr')[0]
svc.description = 'Pooled CRISPR screen quantification'
svc.application_url = 'https://cccb-analysis.tm4.org'
svc.upload_instructions = """<p>Manage your files here.  For CRISPR screens there are two types of files to upload:</p>
	<p><strong>1. A library file:</strong> This file defines the CRISPR targets to which we will align the sequences.  We accept Excel (xls, xlsx), tab-delimited (tsv), or
	comma-separated (csv) formats.  Regardless of the file format, two columns are required (in the following order):
	<ul>
		<li>Target ID:  This identifies the target, often a gene name.  If the entries in this column are not unique, we will automatically create unique names for each target.</li>
		<li>sgRNA sequence:  This is the 20bp guide RNA sequence, <i>without</i> the PAM or flanking context.  Non-unique sequences (e.g. the same sequence in different genes) will be collapsed and 
		    given an alternate name to reflect the merge.
		</li>
	</ul>
	The columns should be named although we do not use the name.  If they are not, the first line will be ignored.
	 </p>
	<p> <strong>2. FastQ-format file(s):</strong>.  One or more fastQ-format sequence files, one per sample.  
	We require files to be Gzip-compressed to save disk space; files will typically end with "gz" if that is the case.  
	Most sequencing providers will send sequence data in this format.
	
	Sample names will be inferred from the names of the files by removing the "fastq.gz" ending.  For example, a file
	with name "sample_A.fastq.gz" will be assigned to a sample with name "sample_A"

	</p>"""
svc.save()

workflow_step = Workflow.objects.get_or_create(step_order=0, service=svc)[0]
workflow_step.step_url = 'analysis_home_view'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=1, service=svc)[0]
workflow_step.step_url = 'pooled_crispr_upload'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=2, service=svc)[0]
workflow_step.step_url = 'pooled_crispr_summary'
workflow_step.save()

###################################### End Pooled CRISPR  ##############################################################
