#!/usr/bin/env python3
# coding=utf-8
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2020 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Website at Assimilation Systems Limited
#   - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.
# If not, see http://www.gnu.org/licenses/
"""
This program downloads and validates signing keys from our cached checksums
of the signing keys we validated manually...
"""
import sys
import os
from typing import List, Tuple
import hashlib
import csv
import requests

# pylint: disable=invalid-name
HashList = List[Tuple[str, str]]


def get_signing_key_from_url(url: str) -> bytes:
    """
    Retrieve the given URL
    :param url: str: Where to go to get the signing key
    :return:bytes: The signing_key
    """
    #  It's pretty simple...
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def check_key_against_checksums(url: str, key: bytes, checksums: HashList) -> bool:
    """
    Return True if the checksum of this key matches one of our cached checksums
    :param url: str: URL to validate
    :param key: str: key to validate
    :param checksums: HashList: List of checksum tuples...
    :return: bool: True if it looks good, False otherwise...
    """
    key_hash = hashlib.sha256(key).hexdigest()
    basename = url.split("/")[-1]
    for check_hash, check_name in checksums:
        if check_hash == key_hash and check_name == basename:
            return True
    return False


def get_csv_hashes(filename: str) -> HashList:
    """
    Read the hashes from the CSV file we were asked to read
    :param filename:str: name of the CSV file
    :return:HashList: list of (hash, name) tuples
    """

    result: HashList = []
    with open(filename) as csv_file:
        for row in csv.reader(csv_file, delimiter=" "):
            if len(row) < 2:
                continue
            result.append((row[0], row[-1]))
    return result


def save_validated_key(url: str, csv_hash_file: str, directory: str = ".") -> None:
    """
    Retrieve a signing key, and save it away if we were able to validate it

    :param url:str: URL of the signing key
    :param csv_hash_file:str: filename of our validated hash values
    :param directory:str: optional directory of where to save the validated key
    :return:None
    """
    hashes = get_csv_hashes(csv_hash_file)
    url_key = get_signing_key_from_url(url)
    if not check_key_against_checksums(url, url_key, hashes):
        print(f"Key at {url} does not match any known checksum.", file=sys.stderr)
        sys.exit(1)
    #  YAY! It matched. Now save it away...
    path = os.path.join(directory, url.split("/")[-1])
    with open(path, "wb") as saved_key:
        print(f"Saving {url} as {path}: {len(url_key)} bytes.")
        saved_key.write(url_key)
    sys.exit(0)


if __name__ == "__main__":

    def main():
        """
        A few good signing keys to keep track of:
        These are a few that I know we currently might need...

        https://download.libsodium.org/jedi.gpg.asc
        https://www.tcpdump.org/release/signing-key.asc

        The following are for various Python signatures...
        https://keybase.io/nad/pgp_keys.asc?fingerprint=0d96df4d4110e5c43fbfb17f2d347ea6aa65421d
        https://keybase.io/nad/pgp_keys.asc?fingerprint=c9b104b3dd3aa72d7ccb1066fb9921286f5e1540
        https://keybase.io/ambv/pgp_keys.asc?fingerprint=e3ff2839c048b25c084debe9b26995e310250568

        """
        url = sys.argv[1]
        csv_file = sys.argv[2] if len(sys.argv) > 2 else "hashes.csv"

        save_validated_key(url, csv_file)

    main()
