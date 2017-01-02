# -*- coding: utf-8 -*-

# Copyright (C) 2017  Boris Pruessmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""Read and write DSF audio stream information and tags."""

from mutagen import StreamInfo, FileType
from mutagen.id3 import ID3
from mutagen.id3._util import ID3NoHeaderError, error as ID3Error
from mutagen._util import cdata, MutagenError, loadfile, convert_error

__all__ = ["DSF", "Open"]

class error(MutagenError):
    pass


class DSFInfo(StreamInfo):
    """DSFInfo()

    DSFInfo audio stream information.

    Attributes:
        length (`int`): audio length, in seconds
        sample_rate (`int`): audio sample rate, in Hz
    """

    @convert_error(IOError, error)
    def __init__(self, fileobj):
        """Raises error"""
        dsd_header = fileobj.read(28)
        if len(dsd_header) != 28 or not dsd_header.startswith("DSD "):
            raise DSFHeaderError("DSF dsd header not found")
        self.file_size = cdata.ulonglong_le(dsd_header[12:20])
        self.id3_location = cdata.ulonglong_le(dsd_header[20:28])
        fmt_header = fileobj.read(52)
        if len(fmt_header) != 52 or not fmt_header.startswith("fmt "):
            raise DSFHeaderError("DSF fmt header not found")
        self.format_version = cdata.uint_le(fmt_header[12:16])
        self.format_id = cdata.uint_le(fmt_header[16:20])
        self.channel_type = cdata.uint_le(fmt_header[20:24])
        self.channel_num = cdata.uint_le(fmt_header[24:28])
        self.sample_rate = cdata.uint_le(fmt_header[28:32])
        self.bits_per_sample = cdata.uint_le(fmt_header[32:36])
        samples = cdata.ulonglong_le(fmt_header[36:44])
        self.length = float(samples) / self.sample_rate

    def pprint(self):
        return u"DSF, %.2f seconds, %d Hz." % (
            self.length, self.sample_rate)


class _DSFID3(ID3):
    """A DSF file with ID3v2 tags"""

    def _pre_load_header(self, fileobj):
        # DSF stores the ID3 at the end of the filename
        dsd_header = fileobj.read(28)

        id3_location = cdata.ulonglong_le(dsd_header[20:28])
        if id3_location == 0:
            raise ID3NoHeaderError("File has no existing ID3 tag")

        try:
            fileobj.seek(id3_location)
        except EnvironmentError:
            raise err, None, stack


    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething, v2_version=4, v23_sep='/', padding=None):
        """Save ID3v2 data to the AIFF file"""

        fileobj = filething.fileobj

        try:
            # DSF stores the ID3 at the end of the filename
            dsd_header = fileobj.read(28)
            id3_location = cdata.ulonglong_le(dsd_header[20:28])
            if id3_location == 0: # we can make a new entry at the end of the file
                fileobj.seek(0,2) # go to the end of the file
                id3_location = fileobj.tell() # this is where we are going to put the id3
                fileobj.seek(20) # this is where we will store the pointer
                fileobj.write(struct.pack('Q',id3_location)) # write the location

            try:
                fileobj.seek(id3_location)
            except EnvironmentError:
                raise err, None, stack

            try:
                data = self._prepare_data(
                    fileobj, id3_location, self.size, v2_version,
                    v23_sep, padding)
            except ID3Error as e:
                reraise(error, e, sys.exc_info()[2])

            try:
                fileobj.seek(id3_location)
            except EnvironmentError:
                raise err, None, stack

            fileobj.write(data)
            fileobj.truncate()

        finally:
            fileobj.close()


class DSF(FileType):
    """DSF(filething)

    An DSF audio file.

    Arguments:
        filething (filething)

    Attributes:
        tags (`mutagen.id3.ID3`)
        info (`DSFInfo`)
    """

    _mimes = ["audio/dsf"]

    def add_tags(self):
        """Add a DSF tag block to the file."""

        if self.tags is None:
            self.tags = _DSFID3()
        else:
            raise error("an ID3 tag already exists")


    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething, **kwargs):
        """Load stream and tag information from a file."""

        fileobj = filething.fileobj

        try:
            self.tags = _DSFID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e)
        else:
            self.tags.filename = self.filename

        fileobj.seek(0, 0)
        self.info = DSFInfo(fileobj)

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith("DSD ") * 2 + filename.endswith(".dsf"))

Open = DSF
