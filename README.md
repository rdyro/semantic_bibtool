# Command Line Bib Generator via Semantic Scholar API

Automatic generation of bibs from a single title or a list of titles with
[semantic scholar](https://www.semanticscholar.org/product/api) API.

This repository is in no way affiliated with Semantic Scholar.

## Installation

1. Obtain an API key from Semantic Scholar: [here](https://www.semanticscholar.org/product/api#Partner-Form).
2. Paste the API key (a string letters and numbers) into `./semantic_bibtool/api_key.txt`
3. Install using pip: `pip install .`

## Example usage

```bash
$ semantic_bibtool -i "attention is all you need"
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
usage: semantic_bibtool [-h] -i INPUT [-o OUTPUT_FILE] [--add-url]

A tool for converting paper titles (with optional author names as keywords) to formatted latex bib format using Semantic Scholar API.

NOT AFFILIATED WITH Semantic Scholar.

You need to obtain an API key for Semantic Scholar, which you can request here: https://www.semanticscholar.org/product/api#Partner-Form

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        input, either:
                                * a (quoted) string
                                * a .txt file with one title per line
                                * a zotero .csv export
                        This tool infers data type from file extension, make sure it matches!
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        stdout by default
  --add-url

Example use:
        $ pip install .
        $ semantic_bibtool -i "attention is all you need"
        $ semantic_bibtool -i titles.txt -o references.bib
        $ semantic_bibtool -i zotero.csv
```