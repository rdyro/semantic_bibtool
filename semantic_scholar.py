#!/usr/bin/env python3

################################################################################
from __future__ import annotations

import sys
import argparse
import json
from pathlib import Path
import random
import re
import string
import time
import traceback
from multiprocessing import Manager, Pool, Process, TimeoutError
from pathlib import Path
from pprint import pprint
from typing import Optional, Union

import requests
from tqdm import tqdm

################################################################################

################################################################################
API_KEY = ""  # insert your API key here
API_CALL_LIMIT = 0.1  # in seconds


def author_to_bibformat(author: str) -> str:
    pieces = author.split(" ")
    name = pieces[0]
    lastname = " ".join(pieces[1:])
    return f"{lastname}, {name}"


def preserve_uppercase(title: str) -> str:
    return "".join(c if c not in string.ascii_uppercase else ("{" + c + "}") for c in title)


def filter_ascii(word: str) -> str:
    return "".join([c for c in word if c in string.ascii_letters])


def filter_printable(word: str) -> str:
    return "".join([c for c in word if c in string.printable])


def filter_ascii_replace_with_space(word: str) -> str:
    return "".join([c if c in string.ascii_letters else " " for c in word])


################################################################################

################################################################################
def _lookup(title: str, **options) -> dict:
    global API_KEY
    url = "http://api.semanticscholar.org/graph/v1/paper/search"
    fields = [
        "title",
        "abstract",
        "venue",
        "year",
        "citationCount",
        "publicationTypes",
        "publicationDate",
        "journal",
        "authors",
    ]
    if options.get("add_url", False):
        fields.append(url)
    fields = ",".join(fields)
    ret = requests.get(
        url,
        params=[("query", title), ("fields", fields)],
        headers={"x-api-key": API_KEY},
        timeout=10.0,
    )
    assert ret.ok
    return json.loads(ret.text)["data"]


def format_bib(paper: dict) -> str:
    key = "".join(
        [
            author_to_bibformat(paper["authors"][0]["name"])
            .split(", ")[0]
            .replace(" ", "")
            .lower(),
            str(paper["year"]),
            filter_ascii(paper["title"].split(" ")[0].lower()),
        ]
    )
    pub_types = paper.get("publicationTypes", None)
    if pub_types is not None and "Conference" in pub_types:
        preamble = "@inproceedings{"
        journal_key = "booktitle"
    elif pub_types is not None and "JournalArticle" in pub_types:
        preamble = "@article{"
        journal_key = "journal"
    else:
        preamble = "@misc{"
        journal_key = "booktitle"
    body = {
        "author": " and ".join(
            [author_to_bibformat(author["name"]) for author in paper["authors"]]
        ),
        "title": preserve_uppercase(paper["title"]),
        journal_key: preserve_uppercase(paper["venue"]),
        "year": str(paper["year"]),
    }
    if options["add_url"]:
        body["url"] = paper["url"]
    return "\n".join(
        [f"{preamble}{key},"] + [f"  {k} = {{{v}}}," for (k, v) in body.items()] + ["}"]
    )


def f_lookup_title_author(args):
    title, authors, rate_queue, options = args
    rate_queue.get()
    if isinstance(title, str) and isinstance(authors, str):
        first_author_lastname = authors.split("; ")[0].split(", ")[0]
        try:
            ret = _lookup(filter_ascii_replace_with_space(title), **options)
            for entr in ret:
                if len(entr["authors"]) > 0 and re.match(
                    f".*{first_author_lastname}", entr["authors"][0]["name"]
                ):
                    return format_bib(ret[0])
            print(f"No authors matched {authors}")
        except Exception as e:
            if len(ret) > 0:
                for entr in ret:
                    if len(entr["authors"]) > 0:
                        print(entr["authors"][0]["name"])
                    else:
                        print("<>")
            traceback.print_exc()
            print("#" * 80)
    return f"% paper: {title} is missing"


def rate_throttler(rate_queue):
    try:
        k = 0
        while True:
            if not rate_queue.full():
                rate_queue.put(0)
            time.sleep(API_CALL_LIMIT)
            k += 1
    except BrokenPipeError:
        return


def bib_from_zotero(fname, **options):
    import pandas as pd

    df = pd.read_csv(fname)

    # query the server
    pool = Pool(8)
    rate_queue = Manager().Queue(maxsize=1024)
    p = Process(target=rate_throttler, args=(rate_queue,))
    p.start()
    arg_list = list(
        zip(
            df["Title"],
            df["Author"],
            [rate_queue] * df.shape[0],
            [options] * df.shape[0],
        )
    )
    bib_out = [
        ret
        for ret in tqdm(
            pool.imap(f_lookup_title_author, arg_list),
            total=len(arg_list),
        )
    ]
    p.kill()

    # remove duplicate entries
    bib_missing = [bib for bib in bib_out if bib[0] == "%"]
    bib_entries = [bib for bib in bib_out if bib[0] != "%"]
    bib_entries = {
        bib.split("\n")[0][re.match(r"@[a-zA-Z]+\{", bib).span()[1] : -1]: bib
        for bib in bib_entries
    }
    bib_out = bib_missing + list(bib_entries.values())

    # merge and return text file bibliography
    bib_out = "\n".join(bib_out)
    return bib_out


def write_output(output, fname=sys.stdout):
    if isinstance(fname, type(sys.stdout)):
        fname.write(output)
        fname.write("\n")
    else:
        with open(Path(path), "w") as fp:
            fp.write(output)


################################################################################


################################################################################
if __name__ == "__main__":
    if len(API_KEY) == 0:
        api_path = Path(__file__).parent / "api_key.txt"
        msg = (
            "You need to paste an API key into this file at the top "
            + "or create a file at the root of repository called 'api_key.txt'"
        )
        assert api_path.exists(), msg
        API_KEY = api_path.read_text().strip()

    # parse arguments
    parser = argparse.ArgumentParser(
        epilog="Example use:" + '\n\t$ python3 semantic_scholar.py -i "attention is all you need"'
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="input, either: a (quoted) string;"
        + " a .txt file with one title per line;"
        + "a zotero .csv export",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        default=sys.stdout,
        required=False,
        help="stdout by default",
    )
    parser.add_argument("--add-url", action="store_true", default=False)
    args = parser.parse_args()

    options = dict(add_url=bool(args.add_url))

    # handle logic
    path = Path(args.input)
    if path.suffix == ".csv":  # zotero export into a csv file
        output = bib_from_zotero(path, **options)
        write_output(output, args.output_file)
    elif path.suffix == ".txt":  # text file with titles only on each line
        with open(path, "r") as fp:
            lines = [line for line in fp.read().split("\n") if len(line) > 0]
        output = []
        for title in lines:
            try:
                output.append(
                    format_bib(_lookup(filter_ascii_replace_with_space(title), **options)[0])
                )
            except Exception:
                print()
                traceback.print_exc()
                print()
                output.append(f"% paper: {title} is missing")
        write_output("\n".join(output), args.output_file)
    else:  # single title from the command line
        try:
            print(format_bib(_lookup(filter_ascii_replace_with_space(path.name), **options)[0]))
        except Exception as e:
            print()
            traceback.print_exc()
            print()
            print(f"% paper: {path.name} is missing")

################################################################################
