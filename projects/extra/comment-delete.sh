#!/bin/bash
# 使い方: ./strip.sh input.txt > output.hack
sed 's/ *\/\/.*$//' "$1" | grep -v '^$'
