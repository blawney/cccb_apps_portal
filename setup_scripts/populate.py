"""
This script is used for populating the database with static data.

For example, the order of operations in the UI is determined by a series of Workflow
steps, which are defined by which Service the project corresponds to.  

Thus, when we startup, we want to easily specify that a RNA-seq service has 5 steps, and define their order
"""
import sys
import os
import json

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
workflow_step.instructions = """<p>Manage your files here. Upload or remove your compressed, 
	FASTQ-format files as necessary. In the next step, you can assign the files to 
	particular samples.</p>  <p class="bolded">FastQ file upload:</p>  
	<p>For naming your files, we enforce a particular naming convention which is followed 
	by most sequencing providers. We also require files to be Gzip-compressed to save disk space; 
	files will typically end with "gz" if that is the case.</p>  <p>If your sequencing is 
	single-end protocol, we expect files named like [SAMPLE]_R1.fastq.gz, where [SAMPLE] is 
	your sample's name.</p>  <p>For paired sequencing protocols there will be two files 
	per sample, named [SAMPLE]_R1.fastq.gz and [SAMPLE]_R2.fastq.gz; note the only difference 
	is "R2" to indicate the second of a read pairing.</p>"""
extra = {}
extra['sample_source_upload'] = True
workflow_step.extra = json.dumps(extra)
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
workflow_step.instructions = """<p>Manage your files here. Upload or remove your compressed, 
	BAM-format files as necessary. 
	In the next step, you can assign the files to particular samples.</p>  
	<p class="bolded">BAM file upload:</p>  <p>To upload alignment (BAM format) files, 
	we only require that the file end with the "bam" extension, such as [SAMPLE].bam. 
	The sample name will be inferred from the name by removing the extension. 
	For example, the file KB10_Kd1.bam will create a sample with the name "KB10_Kd1".</p>"""
extra = {}
extra['sample_source_upload'] = True
workflow_step.extra = json.dumps(extra)
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
workflow_step.instructions = """<p>Manage your files here. Upload or remove your compressed, 
	FASTQ-format files as necessary. In the next step, you can assign the files to 
	particular samples.</p>  <p class="bolded">FastQ file upload:</p>  
	<p>For naming your files, we enforce a particular naming convention which is followed 
	by most sequencing providers. We also require files to be Gzip-compressed to save disk space; 
	files will typically end with "gz" if that is the case.</p>  <p>If your sequencing is 
	single-end protocol, we expect files named like [SAMPLE]_R1.fastq.gz, where [SAMPLE] is 
	your sample's name.</p>  <p>For paired sequencing protocols there will be two files 
	per sample, named [SAMPLE]_R1.fastq.gz and [SAMPLE]_R2.fastq.gz; note the only difference 
	is "R2" to indicate the second of a read pairing.</p>"""
extra = {}
extra['sample_source_upload'] = True
workflow_step.extra = json.dumps(extra)
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


svc.save()

workflow_step = Workflow.objects.get_or_create(step_order=0, service=svc)[0]
workflow_step.step_url = 'analysis_home_view'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=1, service=svc)[0]
workflow_step.step_url = 'pooled_crispr_fastq_upload'
workflow_step.instructions = """<p>Manage your files here. Upload or remove your compressed, 
	FASTQ-format files as necessary.

	<p class="bolded">FastQ file upload:</p>  
	<p>We require fastq files to be Gzip-compressed to save disk space; 
	files will typically end with "gz" if that is the case.  We will infer the sample name from the file by removing
	the "fastq.gz" suffix.  For example, if the file is named "sample_A.fastq.gz", then we will create a sample
	named "sample_A".
	</p>
	"""
extra = {}
extra['sample_source_upload'] = True
workflow_step.extra = json.dumps(extra)
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=2, service=svc)[0]
workflow_step.step_url = 'pooled_crispr_library_upload'
workflow_step.instructions = """
	<p>
	Upload your target library here.  We accept files with Excel (xls, xlsx), comma-separated (CSV), or tab-separated (TSV)
	formats.  Note that Excel will often alter gene names like MARCH4, interpreting it as a date (e.g. March 4, 2017).  This will cause the name to look like "03-04-2017 00:00:00" or 
	something similar.  We cannot anticipate these sorts of changes and cannot reliably fix these changes, so please check this before uploading.
	</p>
	<p>
	We require the files to have the following format:
	<ul>
		<li>Two columns:</li>
		<ul>
			<li>Identifier (e.g. gene symbol).  If the entries in this column are not unique, then we will create unique identifiers automatically</li>
			<li>sgRNA sequence (20bp).  This should NOT include the PAM or surrounding context which are sometimes provided with libraries from providers such as AddGene.</li>
		</ul>
		<li>They should have a header line for column names.  We do not use this, but the first row is skipped, so any data in the first row will be ignored.</li>
	</ul>
	</p>
	"""
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=3, service=svc)[0]
workflow_step.step_url = 'pooled_crispr_summary'
workflow_step.save()

###################################### End Pooled CRISPR  ##############################################################


###################################### Start circRNA ##############################################################

svc = Service.objects.get_or_create(name='circ_rna')[0]
svc.description = 'circRNA detection with KNIFE'
svc.application_url = 'https://cccb-analysis.tm4.org'
svc.save()

# add the applicable organisms/genome builds:
org = Organism.objects.get_or_create(reference_genome='hg19', service=svc)[0]
org.description = 'Human (hg19)'
org.save()

org = Organism.objects.get_or_create(reference_genome='mm10', service=svc)[0]
org.description = 'Mouse (mm10)'
org.save()

workflow_step = Workflow.objects.get_or_create(step_order=0, service=svc)[0]
workflow_step.step_url = 'analysis_home_view'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=1, service=svc)[0]
workflow_step.step_url = 'choose_genome'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=2, service=svc)[0]
workflow_step.step_url = 'generic_upload'
workflow_step.instructions = """<p>Manage your files here. Upload or remove your compressed, 
	FASTQ-format files as necessary. In the next step, you can assign the files to 
	particular samples.</p>  <p class="bolded">FastQ file upload:</p>  
	<p>For naming your files, we enforce a particular naming convention which is followed 
	by most sequencing providers. We also require files to be Gzip-compressed to save disk space; 
	files will typically end with "gz" if that is the case.</p>  <p>If your sequencing is 
	single-end protocol, we expect files named like [SAMPLE]_R1.fastq.gz, where [SAMPLE] is 
	your sample's name.</p>  <p>For paired sequencing protocols there will be two files 
	per sample, named [SAMPLE]_R1.fastq.gz and [SAMPLE]_R2.fastq.gz; note the only difference 
	is "R2" to indicate the second of a read pairing.</p>"""
extra = {}
extra['sample_source_upload'] = True
workflow_step.extra = json.dumps(extra)
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=3, service=svc)[0]
workflow_step.step_url = 'file_annotation'
workflow_step.save()

workflow_step = Workflow.objects.get_or_create(step_order=4, service=svc)[0]
workflow_step.step_url = 'pre_analysis_summary'
workflow_step.save()

###################################### End circRNA ##############################################################

