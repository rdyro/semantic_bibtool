# Command Line Bib Generator via Semantic Scholar API

Automatic generation of bibs from a single title or a list of titles with
[semantic scholar](https://www.semanticscholar.org/product/api) API.

This repository is in no way affiliated with Semantic Scholar.

## Installation

1. Obtain an API key from Semantic Scholar: [here](https://www.semanticscholar.org/product/api#Partner-Form).
2. place your API key (a string letters and numbers) into the environment
   variable `export SEMANTIC_SCHOLAR_API_KEY="..."`.
3. Install using pip: `pip install semantic_bibtool`

## Example usage

```bash
$ semantic_bibtool "attention is all you need"
```
prints
```
@inproceedings{vaswani2017attention,
  author = {Vaswani, Ashish and M. Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and N. Gomez, Aidan and Kaiser, Lukasz and Polosukhin, Illia},
  title = {{A}ttention is {A}ll you {N}eed},
  booktitle = {{N}{I}{P}{S}},
  year = {2017},
}
```

## Help
```
usage: semantic_bibtool [-h] [-o OUTPUT_FILE] [--add-url] input

A tool for converting paper titles (with optional author names as keywords) to formatted latex bib format using Semantic Scholar API.

NOT AFFILIATED WITH Semantic Scholar.

You need to obtain an API key for Semantic Scholar, which you can request here: https://www.semanticscholar.org/product/api#Partner-Form Export it in your environment as `export SEMANTIC_SCHOLAR_API_KEY="..."`

positional arguments:
  input                 input, either:
                                * a (quoted) string
                                * a .txt file with one title per line
                                * a zotero .csv export
                        This tool infers data type from file extension, make sure it matches!

options:
  -h, --help            show this help message and exit
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        stdout by default
  --add-url             whether to add the url to the paper in the bib file

Example use:
        $ pip install .
        $ semantic_bibtool "attention is all you need"
        $ semantic_bibtool titles.txt -o references.bib
        $ semantic_bibtool zotero.csv
```
