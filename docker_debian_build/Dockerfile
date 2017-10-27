# This dockerfile sets up the container for the CCCB web app portal
FROM debian:stretch
RUN apt-get update \
    && apt-get install -y \
    build-essential \
    python-dev \
    python-pip \
    python-cffi \
    python-cryptography \
    curl \
    wget \
    gfortran \
    openssl \
    libffi-dev \
    libxml2-dev \
    libcairo2-dev \
    libblas-dev \
    libreadline-dev \
    libmariadb-dev \
    libmariadbclient-dev \
    libfreetype6-dev \
    libpng-dev \
    libpcre3-dev \
    liblzma-dev \
    libbz2-dev \
    zlib1g-dev \
    default-jre \
    default-jdk \
    libcurl4-openssl-dev \
    supervisor \
    texlive-base \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-pictures \
    texlive-latex-extra \
    git \
  && pip install --upgrade pip

SHELL ["/bin/bash", "-c"]

# download and install R 3.4:
RUN wget https://cran.r-project.org/src/base/R-3/R-3.4.0.tar.gz \
  && tar -xzf R-3.4.0.tar.gz \
  && cd R-3.4.0 \
  && ./configure --with-cairo \
  && make \
  && make install

# install some google cloud utilities:
RUN pip install gsutil
RUN curl -sSL https://sdk.cloud.google.com > /tmp/gcl \
    && bash /tmp/gcl --install-dir=/root/gcloud --disable-prompts
ARG gcloud_bin=/root/gcloud/google-cloud-sdk/bin
ENV PATH "$PATH:"${gcloud_bin}
ENV GCLOUD=${gcloud_bin}/gcloud

# celery/redis related items
RUN curl -o /tmp/redis-stable.tar.gz http://download.redis.io/redis-stable.tar.gz \
  && cd /tmp \
  && tar -zxf redis-stable.tar.gz \
  && cd redis-stable \
  && make \
  && make install \
  && cp redis.conf /etc/redis.conf

# setup app directory which contains everything:
ARG appdir=/webapp
RUN mkdir ${appdir}
WORKDIR ${appdir}

# pull the app code:
ENV PATH="${gcloud}:${PATH}"
RUN git clone -b generalization https://github.com/blawney/cccb_apps_portal.git "${appdir}"
#RUN "${gcloud_bin}"/gcloud source repos clone cccb_apps "${appdir}"

# a directory to hold the credentials for dropbox, drive, etc.
ARG credentials_dir=${appdir}/credentials
RUN mkdir ${credentials_dir}

# install virtualenv, create a virtual environment for django, and install the necessary libraries:
ARG django_venv=/django_venv
RUN pip install virtualenv \
  && virtualenv ${django_venv} \
  && source ${django_venv}/bin/activate \
  && pip install --no-cache-dir -r "${appdir}"/requirements.txt
ENV DJANGO_VENV=${django_venv}

# download the db connector:
ARG cloud_sql_dir=/cloudsql
ARG cloud_sql_proxy=${appdir}/cloud_sql_proxy
RUN curl -o ${cloud_sql_proxy}  https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 \
  && chmod +x ${cloud_sql_proxy} \
  && mkdir ${cloud_sql_dir} \
  && chmod 777 ${cloud_sql_dir}
ENV CLOUD_SQL_MOUNT=${cloud_sql_dir}
ENV CLOUD_SQL_PROXY=${cloud_sql_proxy}

# a directory to hold startup scripts, etc.
RUN mkdir /startup
ADD docker_utils /startup

# install the dependencies for R
RUN Rscript /startup/install_R_packages.R \
  && R CMD INSTALL r_packages/cccbDGEpipeline_0.1.0.tar.gz

ENV APP_ROOT=${appdir}

# expose port
EXPOSE 8080

# run the startup script which injects some parameters and starts the app server:
ENTRYPOINT ["/startup/startup.sh"]
