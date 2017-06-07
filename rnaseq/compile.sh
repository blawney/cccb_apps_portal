#!/bin/bash

d=$1
f=$2

cd $d

pdflatex $f
bibtex $f
pdflatex $f
pdflatex $f
