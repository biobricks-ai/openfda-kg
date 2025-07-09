#!/usr/bin/bash
biobricks init
if ! biobricks status | grep -q '^https://github.com/biobricks-ai/openfda'; then
  biobricks add openfda
fi
biobricks pull