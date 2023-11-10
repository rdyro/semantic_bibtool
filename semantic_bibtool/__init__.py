#!/usr/bin/env python3

################################################################################
import argparse
import os
import json
import re
import string
import sys
import time
import traceback
from argparse import RawTextHelpFormatter
from multiprocessing import Manager, Pool, Process
from pathlib import Path
from typing import Dict, List

import requests
from tqdm import tqdm

API_KEY = ""  # insert your API key here
API_CALL_LIMIT = 0.1  # in seconds


# low-level utilities ##############################################################################


def author_to_bibformat(author: str) -> str:
    """Convert an author's name First- Middle- Last-name format into Last-name, First- Middle-."""
    pieces = author.split(" ")
    name = pieces[0]
    lastname = " ".join(pieces[1:])
    return f"{lastname}, {name}"


def preserve_uppercase(title: str) -> str:
    """Wrap each individual capital letter into curly braces individually (latex bib convention)."""
    return "".join(c if c not in string.ascii_uppercase else ("{" + c + "}") for c in title)


def filter_ascii(word: str) -> str:
    """Only retain ASCII characters."""
    return "".join([c for c in word if c in string.ascii_letters])


def filter_printable(word: str) -> str:
    """Only retain printable characters."""
    return "".join([c for c in word if c in string.printable])


def filter_ascii_replace_with_space(word: str) -> str:
    """Replace all non-ASCII characters with space."""
    return "".join([c if c in string.ascii_letters else " " for c in word])


# higher level utilities ###########################################################################


def _lookup(query: str, **options) -> Dict:
    """Perform the API-based lookup based on a keywords query (title + authors combined)."""
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
        fields.append("url")
    fields = ",".join(fields)
    ret = requests.get(
        url,
        params=[("query", query), ("fields", fields)],
        headers={"x-api-key": API_KEY},
        timeout=10.0,
    )
    assert ret.ok
    return json.loads(ret.text)["data"]


def format_bib(paper: Dict, **options) -> str:
    """Format a bib text from a"""
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
    if options.get("add_url", False):
        body["url"] = paper["url"]
    return "\n".join(
        [f"{preamble}{key},"] + [f"  {k} = {{{v}}}," for (k, v) in body.items()] + ["}"]
    )


def remove_duplicate_bibs(bibs: List[str]) -> List[str]:
    """Removes duplicate bibs and places missing entries on top."""

    # remove duplicate entries
    bib_missing = [bib for bib in bibs if bib[0] == "%"]
    bib_entries = [bib for bib in bibs if bib[0] != "%"]
    bib_entries = {
        bib.split("\n")[0][re.match(r"@[a-zA-Z]+\{", bib).span()[1] : -1]: bib
        for bib in bib_entries
    }
    return bib_missing + list(bib_entries.values())


def rate_throttler(rate_queue):
    """A simple utility to limit the rate of API calls."""
    try:
        k = 0
        while True:
            if not rate_queue.full():
                rate_queue.put(0)
            time.sleep(API_CALL_LIMIT)
            k += 1
    except BrokenPipeError:
        return


def write_output(output, fname=sys.stdout):
    """Write output to stdout or a file."""
    if isinstance(fname, type(sys.stdout)):
        fname.write(output)
        fname.write("\n")
    else:
        with open(Path(fname), "w") as fp:
            fp.write(output)


# txt lookup #######################################################################################


def _txt_f_lookup(args):
    query, rate_queue, options = args
    rate_queue.get()  # throttle lookup
    try:
        return format_bib(_lookup(filter_ascii_replace_with_space(query), **options)[0])
    except Exception as e:
        print()
        traceback.print_exc()
        print()
        return f"% paper: {query} is missing"


def bib_from_txt(queries: List[str], **options):
    # query the server
    pool = Pool(8)
    rate_queue = Manager().Queue(maxsize=10)
    p = Process(target=rate_throttler, args=(rate_queue,))
    p.start()
    arg_list = list(zip(queries, [rate_queue] * len(queries), [options] * len(queries)))
    bibs = [ret for ret in tqdm(pool.imap(_txt_f_lookup, arg_list), total=len(arg_list))]
    p.kill(), pool.close()
    return "\n".join(remove_duplicate_bibs(bibs))


# zotero csv lookup ################################################################################


def _zotero_f_lookup_title_author(args):
    """Look up a paper using keywords representing the title and the authors combined."""
    title, authors, rate_queue, options = args
    rate_queue.get()
    if isinstance(title, str) and isinstance(authors, str):
        first_author_lastname = authors.split("; ")[0].split(", ")[0]
        try:
            ret = ""
            ret = _lookup(filter_ascii_replace_with_space(title), **options)
            # attempt to match authors up, fail if can't match authors
            for entr in ret:
                if len(entr["authors"]) > 0 and re.match(
                    f".*{first_author_lastname}", entr["authors"][0]["name"]
                ):
                    return format_bib(ret[0], **options)
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


def bib_from_zotero(fname, **options):
    """Read the Zotero provided CSV dump and create a bibliography from it."""
    import pandas as pd

    df = pd.read_csv(fname)

    # query the server
    pool = Pool(8)
    rate_queue = Manager().Queue(maxsize=10)
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
    bibs = [
        ret
        for ret in tqdm(
            pool.imap(_zotero_f_lookup_title_author, arg_list),
            total=len(arg_list),
        )
    ]
    p.kill(), pool.close()
    return "\n".join(remove_duplicate_bibs(bibs))


# main loop ########################################################################################


def main():
    # parse arguments
    parser = argparse.ArgumentParser(
        description="A tool for converting paper titles"
        + " (with optional author names as keywords) to"
        + " formatted latex bib format using Semantic Scholar API."
        + "\n\nNOT AFFILIATED WITH Semantic Scholar."
        + "\n\nYou need to obtain an API key for Semantic Scholar, which you can"
        + " request here: https://www.semanticscholar.org/product/api#Partner-Form"
        + ' Export it in your environment as `export SEMANTIC_SCHOLAR_API_KEY="..."`',
        epilog="Example use:"
        + "\n\t$ pip install ."
        + '\n\t$ semantic_bibtool "attention is all you need"'
        + "\n\t$ semantic_bibtool titles.txt -o references.bib"
        + "\n\t$ semantic_bibtool zotero.csv",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "input",
        type=str,
        help="input, either:"
        + "\n\t* a (quoted) string"
        + "\n\t* a .txt file with one title per line"
        + "\n\t* a zotero .csv export"
        + "\nThis tool infers data type from file extension, make sure it matches!",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        default=sys.stdout,
        required=False,
        help="stdout by default",
    )
    parser.add_argument(
        "--add-url",
        action="store_true",
        default=False,
        help="whether to add the url to the paper in the bib file",
    )
    args = parser.parse_args()

    global API_KEY
    if os.environ.get("SEMANTIC_SCHOLAR_API_KEY", None) is not None:
        API_KEY = os.environ["SEMANTIC_SCHOLAR_API_KEY"].strip()
    if len(API_KEY) == 0:
        api_path = Path(__file__).absolute().parent / "api_key.txt"
        msg = (
            "You need to paste an API key into this file at the top"
            + " or create a file 'api_key.txt' in ./semantic_bibtool folder (next to __init__.py)."
        )
        assert api_path.exists(), msg
        API_KEY = api_path.read_text().strip()

    options = dict(add_url=bool(args.add_url))

    # handle logic
    path = Path(args.input)
    if path.suffix == ".csv":  # zotero export into a csv file
        output = bib_from_zotero(path, **options)
        write_output(output, args.output_file)
    elif path.suffix == ".txt":  # text file with titles only on each line
        with open(path, "r") as fp:
            lines = [line for line in fp.read().split("\n") if len(line) > 0]
        write_output(bib_from_txt(lines, **options), args.output_file)
    else:  # single title from the command line
        try:
            output = format_bib(_lookup(filter_ascii_replace_with_space(path.name), **options)[0])
            write_output(output, args.output_file)
        except Exception as e:
            print()
            traceback.print_exc()
            print()
            write_output(f"% paper: {path.name} is missing", args.output_file)


if __name__ == "__main__":
    main()
