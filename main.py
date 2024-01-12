import os
import numpy as np
import pandas as pd
import struct

DATA_MAGIC = b"#!"

class ScanDirection:
    UNKNOWN = 0
    FORWARD = 1
    BACKWARD = -1

class NIDRange:
    def __init__(self):
        self.name = None
        self.unit = None
        self.min = 0.0
        self.range = 0.0

class NIDSection:
    def __init__(self):
        self.name = None
        self.meta = {}
        self.direction = ScanDirection.UNKNOWN
        self.group = 0
        self.channel = 0
        self.xres, self.yres = 0, 0
        self.xrange, self.yrange, self.zrange = NIDRange(), NIDRange(), NIDRange()
        self.bitdepth, self.byteorder, self.sign = 0, 0, False
        self.data = None

def find_data_offsets(buffer, ezdfile):
    dataset = ezdfile[0]
    ngroups = int(dataset.meta.get("GroupCount", 0))
    required_size = 0
    ndata = 0

    for i in range(ngroups):
        grkey = f"Gr{i}-Count"
        nchannels = int(dataset.meta.get(grkey, 0))

        for j in range(nchannels):
            grkey = f"Gr{i}-Ch{j}"
            section = next((s for s in ezdfile[1:] if s.name == dataset.meta.get(grkey, None)), None)

            if section:
                section.data = buffer[required_size:required_size + section.xres * section.yres * (section.bitdepth // 8)]
                required_size += len(section.data)
                section.group, section.channel = i, j
                ndata += 1

    return ndata

def nidfile_load(filename):
    with open(filename, 'rb') as file:
        buffer = file.read()

    header_size = buffer.find(DATA_MAGIC)
    if header_size == -1:
        return None

    ezdfile = []
    file_read_header(buffer[:header_size], ezdfile)

    n = find_data_offsets(buffer[header_size + len(DATA_MAGIC):], ezdfile)

    if not n:
        return None

    for section in ezdfile[1:]:
        if section.data:
            print(f"Processing data section: {section.group}-{section.channel}")

    return ezdfile

def file_read_header(buffer, ezdfile):
    section = None

    for line in buffer.split(b'\n'):
        line = line.strip()

        if not line:
            continue

        if line[0:1] == b'[' and line[-1:] == b']':
            section = NIDSection()
            ezdfile.append(section)
            section.name = line[1:-1].decode('utf-8')
            section.meta = {}
            print(f"Section <{section.name}>")
            continue

        if section:
            try:
                key, value = line.split(b'=', 1)
                section.meta[key.strip().decode('utf-8')] = value.strip().decode('utf-8')
            except UnicodeDecodeError:
                pass