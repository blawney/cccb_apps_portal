#!/bin/bash
set -v

apt-get update && \
     apt-get install -y \
         apt-transport-https \
         ca-certificates \
         curl \
         software-properties-common \
         python-pip

curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | apt-key add -
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(lsb_release -cs) stable"

apt-get update && \
    apt-get install -y docker-ce

# install some python libraries for communicating back:
pip install pycrypto
pip install google-api-python-client

# a directory for scripts:
SCRIPTS_DIR=/scripts
mkdir $SCRIPTS_DIR
chmod 775 $SCRIPTS_DIR

# a folder in a bucket that holds the scripts necessary:
SCRIPTS_DIR_GS=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/scripts-directory)
gsutil cp $SCRIPTS_DIR_GS/* $SCRIPTS_DIR/


# pull the data files and other metadata for running the job:
GENOME=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/reference_genome)
R1_FASTQ=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/r1_fastq)
R2_FASTQ=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/r2_fastq)
RESULT_BUCKET=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/result_bucket)
DATASET_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/dataset_name)
READ_LENGTH_SCRIPT=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/read_length_script)
READ_SAMPLES=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/read_samples)
KNIFE_RESOURCE_BUCKET=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/knife_resource_bucket)

# pull credentials which are needed in the docker container
CREDENTIAL_JSON_CLOUD=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/service_account_credentials)
CREDENTIAL_JSON_BASENAME=$(basename $CREDENTIAL_JSON_CLOUD)
CREDENTIAL_DIR="/credentials"
mkdir $CREDENTIAL_DIR
gsutil cp $CREDENTIAL_JSON_CLOUD $CREDENTIAL_DIR


# pull the container from the google container registry:
DOCKER_IMAGE=$(curl -H "Metadata-Flavor: Google" http://metadata/computeMetadata/v1/instance/attributes/docker_image)
docker pull $DOCKER_IMAGE && \
	docker run \
		-v $CREDENTIAL_DIR:/creds \
		$DOCKER_IMAGE \
		$GENOME \
		$R1_FASTQ \
		$R2_FASTQ \
		$RESULT_BUCKET \
		/creds/$CREDENTIAL_JSON_BASENAME \
		$READ_LENGTH_SCRIPT \
		$READ_SAMPLES \
		$KNIFE_RESOURCE_BUCKET
		/fastq_files \
		complete \
		/knife_output \
		$DATASET_NAME

if [ $? != 0 ]; then
	# Failed
	python $SCRIPTS_DIR/communicate.py 1
	
	# email CCCB:
else
	# was OK
	python $SCRIPTS_DIR/communicate.py
fi

