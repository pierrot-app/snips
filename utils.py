#!/usr/local/bin/python
# coding: utf-8

def read_file(file_name):
    file = open(file_name, 'r')
    file_content = file.read()
    file_content = file_content.rstrip('\n')
    return file_content

def write_to_file(file_name, content):
    file = open(file_name, 'w')
    file.write(str(content))