#!/usr/bin/python3 -u
"""
Code search in the source code of PyPI top projects.

Usage::

    ./search_pypi_top.py --verbose PYPI_DIR/ REGEX -o output_file

Use --help command line option to get the command line usage.
"""
import argparse
import datetime
import logging
import os
import re
import sys
import tarfile
import zipfile


IGNORE_CYTHON = True
# Ignore file extensions known to be binary files to avoid the slow
# is_binary_string() check
IGNORED_FILE_EXTENSIONS = (
    # Programs and dynamic liraries
    "EXE", "SO", "PYD",
    # Python
    "PYC", "WHL",
    # Archives
    "BZ2", "CAB", "GZ", "ZIP", "RAR", "TAR", "TGZ", "XZ",
    # Pictures
    "AI", "BMP", "ICO", "JPG", "PNG", "PSD", "TGA", "TIF", "WMF", "XCF",
    # Audio
    "AAC", "AIF", "ANI", "MP3", "WAV", "WMA",
    # Video
    "AVI", "MKV", "MP4",
    # Linux packages
    "DEB", "RPM",
    # Misc
    "BIN", "PDF", "MO", "DB", "ISO", "JAR", "TTF", "XLS",
    "DS_Store",
)
IGNORED_FILE_EXTENSIONS = tuple("." + ext.lower()
                                for ext in IGNORED_FILE_EXTENSIONS)
# Check the first bytes of a file to test if it's a binary file or not
BINARY_TEST_LEN = 256

# "/* Generated by Cython 0.29.13 */"
# "/* Generated by Cython 0.20.1 on Sun Mar 16 22:58:12 2014 */"
CYTHON_REGEX = re.compile(br'^/\* Generated by Cython [0-9]+(.[0-9]+)+ ')


def output(msg):
    print(f"# {msg}", file=sys.stderr, flush=True)


def log(msg):
    print(f"# {msg}", file=sys.stderr, flush=True)


def ignore_filename(args, filename):
    if args.text:
        return False
    return filename.lower().endswith(IGNORED_FILE_EXTENSIONS)


def log_ignored_file(archive_name, filename):
    logging.info(f"ignore filename: {archive_name}: {filename}")


# If all bytes of a string are in TEXTCHARS, the string looks like text
TEXTCHARS = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})


def is_binary_string(header):
    # Treat UTF-16 as binary, but that's acceptable since Python and C source
    # files are not encoded as UTF-16
    return bool(header.translate(None, TEXTCHARS))


def decompress_tar(args, archive_filename, mode):
    with tarfile.open(archive_filename, mode) as tar:
        while True:
            member = tar.next()
            if member is None:
                break
            filename = member.name
            if ignore_filename(args, filename):
                log_ignored_file(archive_filename, filename)
                continue
            fp = tar.extractfile(member)
            if fp is None:
                continue
            with fp:
                yield (filename, fp)


def decompress_zip(args, archive_filename):
    with zipfile.ZipFile(archive_filename) as zf:
        for member in zf.filelist:
            filename = member.filename
            if ignore_filename(args, filename):
                log_ignored_file(archive_filename, filename)
                continue
            with zf.open(member) as fp:
                yield (filename, fp)


def decompress(args, filename):
    if filename.endswith((".tar.gz", ".tgz")):
        yield from decompress_tar(args, filename, "r:gz")
    elif filename.endswith(".tar.bz2"):
        yield from decompress_tar(args, filename, "r:bz2")
    elif filename.endswith(".zip"):
        yield from decompress_zip(args, filename)
    else:
        raise Exception(f"unsupported filename: {filename!r}")


def is_binary_file(args, fp):
    if args.text:
        return False
    data = fp.read(BINARY_TEST_LEN)
    fp.seek(0)
    if is_binary_string(data):
        return True
    return False

def grep(args, archive_filename, regex):
    for filename, fp in decompress(args, archive_filename):
        if is_binary_file(args, fp):
            logging.info(f"ignore binary file: {archive_filename}: {filename}")
            continue

        matchs = []
        ignore = False
        lineno = 1
        # Split at Unix newline b'\n' byte
        for line in fp:
            if lineno == 1 and IGNORE_CYTHON and CYTHON_REGEX.match(line):
                logging.info(f"ignore Cython file: {archive_filename}: {filename}")
                ignore = True
                break
            if regex.search(line):
                matchs.append((filename, line))
            lineno += 1

        if matchs and not ignore:
            yield from matchs


def search_dir(args, pypi_dir, pattern):
    regex = re.compile(pattern)
    for filename in os.listdir(pypi_dir):
        filename = os.path.join(pypi_dir, filename)
        logging.warning(f"grep {filename}")
        for name, line in grep(args, filename, regex):
            line = line.decode('utf8', 'replace').strip()
            yield (filename, name, line)


def parse_args():
    parser = argparse.ArgumentParser(description='Code search in the source code of PyPI top projects.')
    parser.add_argument('pypi_dir', metavar="PYPI_DIRECTORY",
                        help='PyPI local directory')
    parser.add_argument('pattern', metavar='REGEX',
                        help='Regex to search')
    parser.add_argument('-o', '--output', metavar='FILENAME',
                        help='Output filename')
    parser.add_argument('--text', action='store_true',
                        help='Process a binary file as if it were text')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose mode (ex: log ignored files)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help="Quiet mode (ex: don't log proceed files)")

    return parser.parse_args()


def _main():
    args = parse_args()
    output_filename = args.output
    pattern = os.fsencode(args.pattern)
    pypi_dir = args.pypi_dir

    if args.quiet:
        level = logging.ERROR
    elif args.verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(stream=sys.stderr, level=level,
                        format="# %(message)s")

    start_time = datetime.datetime.now()
    output = None
    if output_filename:
        output = open(output_filename, "w", encoding="utf8")
    try:
        lines = 0
        projects = set()
        for archive_name, filename, line in search_dir(args, pypi_dir, pattern):
            result = f"{archive_name}: {filename}: {line}"
            print(result, flush=True)
            if output is not None:
                print(result, file=output, flush=True)
            lines += 1
            projects.add(archive_name)
    finally:
        if output is not None:
            output.close()

    dt = datetime.datetime.now() - start_time
    print()
    print(f"Time: {dt}")
    print(f"Found {lines} matching lines in {len(projects)} projects")
    if output_filename:
        print(f"Output written into: {output_filename}")


def main():
    try:
        _main()
    except KeyboardInterrupt:
        print()
        print("Interrupted")
        sys.exit(1)

if __name__ == "__main__":
    main()
