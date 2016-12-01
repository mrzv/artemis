# Artemis #
-----------

> [Artemis](http://www.mrzv.org/software/artemis/) is a lightweight distributed issue tracking extension for [Mercurial](http://www.selenic.com/mercurial/).

* [Setup](#markdown-header-setup)
* [Example](#markdown-header-example)
* [Commands](#markdown-header-commands)
* [Filters](#markdown-header-filters)
* [Format](#markdown-header-format)


Individual issues are stored in directories in an `.issues` subdirectory (overridable in a config file). Each one is a `Maildir` and each one is assumed to have a single root message. Various properties of an issue are stored in the headers of that message.

One can obtain Artemis by cloning its [repository](http://hg.mrzv.org/Artemis/):

```
    $ hg clone http://hg.mrzv.org/Artemis/
```

or downloading the entire repository as a [tarball](http://hg.mrzv.org/Artemis/archive/tip.tar.gz).



## Setup ##
-----------

In the `[extensions]` section of your `~/.hgrc` add:

```
    artemis = /path/to/Artemis/artemis
```

Optionally, provide a section `[artemis]` in your `~/.hgrc` file or the repository local `.hg/hgrc` file, and specify an alternative path for the issues subdirectory (instead of the default `.issues`):

```
    [artemis]
    issues = _issues
```

Additionally, one can specify [filters](#markdown-header-filters) and output [formats](#markdown-header-format).

### Windows ###
---------------

The TortoiseHg for windows comes with a sandboxed Python, that means that thg will not be using the Python installed in the system.

If you get a `No module named mailbox!` error find the `mailbox.py` under `%PYTHON_PATH%\Lib` and add it to the `%HG_PATH%\lib\library.zip`. 


[↑ back to top](#markdown-header-artemis)


## Example ##
-------------

**Create an issue:**

```
    $ hg iadd
    ... enter some text in an editor ...
```
.
```
    Added new issue 907ab57e04502afd
```

**List the issues:**

```
    $ hg ilist
    907ab57e04502afd (  0) [new]: New issue
```

**Show an issue:**

```
    $ hg ishow 907ab57e04502afd
    ======================================================================
    From: ...
    Date: ...
    Subject: New issue
    State: new

    Detailed description.

    ----------------------------------------------------------------------
```

**Add a comment to the issue:**

```
    $ hg iadd 907ab57e04502afd
    ... enter the comment text
```
.
```
    ======================================================================
    From: ...
    [snip]
    Detailed description.

    ----------------------------------------------------------------------
    Comments:
      1: [dmitriy] Some comment
    ----------------------------------------------------------------------
```

**And a comment to the comment:**

```
    $ hg iadd 907ab57e04502afd -i 1
    ... enter the comment text ...
```
.
```
    ======================================================================
    From: ...
    [snip]
    Detailed description.

    ----------------------------------------------------------------------
    Comments:
      1: [dmitriy] Some comment
        2: [dmitriy] Comment on a comment
    ----------------------------------------------------------------------
```

**Close the issue:**

```
    $ hg iadd 907ab57e04502afd -p state=resolved -p resolution=fixed -n
```
.
```
    ======================================================================
    From: ...
    [snip]
    Detailed description.

    ----------------------------------------------------------------------
    Comments:
      1: [dmitriy] Some comment
        2: [dmitriy] Comment on a comment
      3: [dmitriy] changed properties (state=resolved, resolution=fixed)
    ----------------------------------------------------------------------
```

**No more new issues, and one resolved issue:**

```
    $ hg ilist
    $ hg ilist -a
    907ab57e04502afd (  3) [resolved=fixed]: New issue
```

The fact that issues are Maildirs, allows one to look at them in, for example, `mutt` with predictable results:

```
    mutt -Rf .issues/907ab57e04502afd
```

**Search the issues:**

Search a property using regular expressions
```
    hg ifind -p state -r "fix(ed)?|resolve(d)?"
    907ab57e04502afd (  3) [resolved]: New issue
    baca6256d98fb593 (  1) [resolved]: Another issue
```

Search the message for a string
```
    hg ifind -mn "comment" 
    907ab57e04502afd (  3) [resolved]: New issue
    baca6256d98fb593 (  1) [resolved]: Another issue
    ba564b23fcff6358 (  1) [new]: New issue
```



[↑ back to top](#markdown-header-artemis)

## Commands ##
--------------

**hg iadd [OPTIONS] [ID]**

> Adds a new issue, or comment to an existing issue ID or its comment COMMENT


options:

|     |                       | description                           |
|-----|-----------------------|---------------------------------------|
| -a  | --attach VALUE [+]    | attach file(s)                        |
|     |                       | (e.g., -a filename1 -a filename2)     |
| -p  | --property VALUE [+]  | update properties                     |
|     |                       | (e.g. -p state=fixed,                 |
|     |                       | -p state=resolved                     |
|     |                       | -p resolution=fixed)                  |
| -n  | --no-property-comment | do not add a comment about changed    |
|     |                       | properties                            |
| -m  | --message VALUE       | use <text> as an issue subject        |
| -i  | --index VALUE         | 0 based index of the message to show  |
|     |                       | (default: 0)                          |
| -c  | --commit              | perform a commit after the addition   |

[+] marked option can be specified multiple times





**hg ilist [OPTIONS]**

> List issues associated with the project

options:

|     |                      | description                            |
|-----|----------------------|----------------------------------------|
| -a  | --all                | list all issues                        |
|     |                      | (by default only those with state new) |
| -p  | --property VALUE [+] | list issues with specific field values |
|     |                      | (e.g., -p state=fixed,                 |
|     |                      | -p state=resolved -p category=doc);    |
|     |                      | lists all possible values of a         |
|     |                      | property if no = sign is provided.     |
|     |                      | (e.g. -p category)                     |
|     | --all-properties     | list all available properties          |
| -o  | --order VALUE        | order of the issues; choices: "new"    |
|     |                      | (date submitted), "latest"             |
|     |                      | (date of the last message)             |
|     |                      | (default: new)                         |
| -d  | --date VALUE         | restrict to issues matching the date   |
|     |                      | (e.g., -d ">12/28/2007)"               |
| -f  | --filter VALUE       | restrict to pre-defined filter         |
|     |                      | (in .issues/.filter*)                  |

[+] marked option can be specified multiple times



**hg ishow [OPTIONS] ID**

> Shows issue ID, or possibly its comment COMMENT

options:

|     |                     | description                             |
|-----|---------------------|-----------------------------------------|
| -a  | --all               | list all comments                       |
| -s  | --skip VALUE        | skip lines starting with a substring    |
|     |                     | (default: >)                            |
| -x  | --extract VALUE [+] | extract attachments                     |
|     |                     | (provide attachment number as argument) |
| -i  | --index VALUE       | 0 based index of the message to show    |
|     |                     | (default: 0)                            |
| -o  | --output VALUE      | extract output directory                |
|     | --mutt              | use mutt to show issue                  |

[+] marked option can be specified multiple times



**hg ifind [OPTIONS] QUERY**

> Shows a list of issues matching the specified QUERY

options:

|     |                   | description                               |
|-----|-------------------|-------------------------------------------|
| -p  | --property VALUE  | issue property to match                   |
|     |                   | [state, from, subject, date, priority,    |
|     |                   | [resolution, ticket, etc..]               |
|     |                   | (default: subject)                        |
| -n  | --no-property     | Do not match the property. Use with       |
|     |                   | --message to search only the message. The |
|     |                   | --property will be ignored.               |
| -m  | --message         | Search the message. If no match is found  |
|     |                   | it will then search the property for a    |
|     |                   | match. Use a blank property to ignore the | 
|     |                   | property search.                          | 
| -c  | --case-sensitive  | case sensitive search                     |
| -r  | --regex           | use regular expressions                   |
|     |                   | (exact option will be ignored)            |
| -e  | --exact           | use exact comparison                      |
|     |                   | like comparison is used if uspecified     |

[+] marked option can be specified multiple times







[↑ back to top](#markdown-header-artemis)


## Filters ##
-------------

Artemis scans all files of the form `.issues/.filter*`, and processes them as config files. Section names become filter names, and the individual settings become properties. For example the following:

```
    [olddoc]
    category=documentation
    state=resolved
```

placed in a file `.issues/.filterMyCustom` creates a filter `olddoc` which can be invoked with the `ilist` command:

```
    hg ilist -f olddoc
```


[↑ back to top](#markdown-header-artemis)



## Format ##
------------

One can specify the output format for the `ilist` command in the global hg configuration `~/.hgrc` or the repository local configuration `.hg/hgrc`.

```
    hg config --edit
```

The default looks like:

```
    [artemis]
    format = %(id)s (%(len)3d) [%(state)s]: %(subject)s
```

Artemis passes a dictionary with the issue properties to the format string. (Plus `id` contains the issue id, and `len` contains the number of replies.)

It's possible to specify different output formats depending on the properties of the issue. The conditions are encoded in the config variable names as follows:

```
    format:state*resolved&resolution*fixed  = %(id)s (%(len)3d) [fixed]: %(Subject)s
    format:state*resolved                   = %(id)s (%(len)3d) [%(state)s=%(resolution)s]: %(Subject)s
```

The first rule matches issues with the state property set to resolved and resolution set to fixed; it abridges the output. The secod rule matches all the resolved issues (not matched by the first rule); it annotates the issue's state with its resolution.

Finally, the dictionary passed to the format string contains a subset of [ANSI codes](http://en.wikipedia.org/wiki/ANSI_escape_code), so one could color the summary lines:

```
    format:state*new = %(red)s%(bold)s%(id)s (%(len)3d) [%(state)s]: %(Subject)s%(reset)s
```


[↑ back to top](#markdown-header-artemis)



--------------------------------------------------------------------

[http://www.mrzv.org/software/artemis/](http://www.mrzv.org/software/artemis/)
