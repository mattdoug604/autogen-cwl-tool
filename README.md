# cwl-helper
Parse the help text of a given program and output a barebones CWL tool description.

**NOTE**: This is still under developlment and the output CWL will likely need to some manual adjustment (typically the input types and output).

# Usage
help text can be read from stdin directly...
```
grep --help | cwl-helper
```

...or from a a file:
```
grep --help > help.txt && cwl-helper -i help.txt
```

help text output to stderr will need to be redirected
```
samtools view -h 2>&1 | cwl-helper
```