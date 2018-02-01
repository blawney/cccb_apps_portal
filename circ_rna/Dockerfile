FROM alpine
#install deps and install gsutil
RUN apk add --update \
    python \
    py-pip \
    py-cffi \
    py-cryptography \
    bash \
    unzip \
    git \
    wget \
    curl \
  && pip install --upgrade pip \
  && apk add make cmake gcc g++ gfortran \
  && apk add libffi-dev \
    python-dev \
    linux-headers \
    musl-dev \
    openssl-dev \
    openblas-dev \
    readline-dev \
    perl \
    openjdk8-jre-base \
  && pip install gsutil \
  && rm -rf /var/cache/apk/*

RUN curl -sSL https://sdk.cloud.google.com > /tmp/gcl \
    && bash /tmp/gcl --install-dir=/root/gcloud --disable-prompts
ARG gcloud_bin=/root/gcloud/google-cloud-sdk/bin
ENV PATH "$PATH:"${gcloud_bin}
ENV GCLOUD=${gcloud_bin}/gcloud
ENV GSUTIL=${gcloud_bin}/gsutil


RUN pip install numpy
RUN pip install scipy

ENV  r_cv_libc_stack_end=no 
RUN wget --no-check-certificate https://cran.cnr.berkeley.edu/src/base/R-3/R-3.2.3.tar.gz \
    && tar -xzf R-3.2.3.tar.gz \
    && cd R-3.2.3 \
    && ./configure --prefix=/usr/local --with-x=no \
    && make \
    && make install
RUN Rscript -e "install.packages('argparse',repos='http://cran.us.r-project.org',dependencies=T)"


RUN mkdir /srv/src /srv/software
RUN apk add --update bc 
RUN mkdir /srv/src/Bowtie1 && \
        cd /srv/src/Bowtie1 && \
        wget https://sourceforge.net/projects/bowtie-bio/files/bowtie/1.1.2/bowtie-1.1.2-src.zip && \
        unzip bowtie-1.1.2-src.zip && \
        cd bowtie-1.1.2 && \
        make && \
        make install

RUN mkdir /srv/src/Bowtie2 && \
        cd /srv/src/Bowtie2 && \
        wget https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.2.8/bowtie2-2.2.8-source.zip && \
        unzip bowtie2-2.2.8-source.zip && \
        cd bowtie2-2.2.8 && \
        make && \
        make install

RUN wget https://cran.r-project.org/src/contrib/chron_2.3-51.tar.gz && \
                R CMD INSTALL chron_2.3-51.tar.gz && \
                wget https://cran.r-project.org/src/contrib/Archive/data.table/data.table_1.9.6.tar.gz && \
                R CMD INSTALL data.table_1.9.6.tar.gz

RUN mkdir /srv/src/samtools && \
        cd /srv/src/samtools && \
        wget https://github.com/samtools/samtools/releases/download/1.3/samtools-1.3.tar.bz2 && \
        tar -jxf samtools-1.3.tar.bz2 && \
        cd samtools-1.3 && \
        ./configure --without-curses && \
        make && \
        make install

RUN pip install biopython

RUN git clone https://github.com/blawney/knife_circ_rna.git /srv/software/knife

ADD container_startup.sh /srv/software/container_startup.sh
ADD get_account_name.py /srv/software/get_account_name.py

ENTRYPOINT ["/srv/software/container_startup.sh"]
