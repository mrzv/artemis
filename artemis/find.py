#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
                                   ..  ┌  -:  .
                                  ([]▄▄├]▄▄▄¿┐`,
    .¡                      ,. D{}▓███████████░█∩^}                       =
    ,▓¼                      .▐▓▓█████████████▓██▓▓,                     (▓
     █▌╕.                   ─@╣████████████████████▄─                   ./▀'
    :▓█▌Ç...             └ '└▓██████████████████████Ö'`            ..  '└`'┌
     \ g█████▄Ü┌        C g██████████████████████████╗─  ²   ²   t▄▓██ù- `╞
      ¡ Å╠█▌╠█▓▓▓▓▌N@▌|   ╓██████████████████████████▌  .╣▓▓▓▓▓▓▓]▐╙ÅÅ∩!
      ` ` ╫½┌▀▀▀▀▀▀░╫▌┘    ▀▀▀▀▀██████████████████▀█▀C  :╝▀▀▀▀▀▀▀.   `:
          L ─ⁿ'``' ─       ''' ─█████████████████▌─█=       ╞º'`'º──
                                    ..Å╫█╛.             ~
                                   ╔▄▄▓██▓▄¿        .
                            -   ]:├╣██▀▀▀▀▀▒Q¿.¿{  )=
                            <─Ω╚█░▓███'──h⌂▓██╡██▌Ü─4
                           `┌ ▐▓█▄▓██╟≤¡yQ▄███▓█▌▐▓M
                           ^. └▀▀▄▓██▄▒▄▄╬▄████▀ └▀╙`
                            «-'''█▓▓█▓██▓██▓▓██└``'⌐
                                 #╛ µ:▓▄;xφ(⌠ █
                                 ╗µ  ~╙'`   `┌█╣
                                 ╝Ñ. ''  '   L▀▀
                                    ~         ,
                                    ^
                                    ÷        ─.
                                    N.   ∩ts  )
                                 ∩    ²⌠  `   ─
                                   (@   ~▒▒  .
                                 ` └▀/ .>▀▀  :
                                     ⌐   ,⌐



 Artemis
 Version 0.5.1
 Copyright (c) 2016 Frostbane Ac
 Apache-2.0, APL-1.0, 0BSD Licensed. ?
 www.??.com
 ?? inspired script.

"""

from mercurial import hg, util, commands, cmdutil
import sys, os, time, random, mailbox, glob, socket, ConfigParser, re
from properties import ArtemisProperties
from artemis import Artemis

__author__ = 'frostbane'
__date__ = '2016/05/24'


class ArtemisFind:
    commands = [
        # dashed options will be resolved to underscores
        # case-sensitive => case_sensitive
        ('p', 'property', "subject", 'Issue property to match. '
                                     '[state, from, subject, date, '
                                     'priority, resolution, etc..]'),
        ('c', 'case-sensitive', None, 'Case sensitive search.'),
        ('r', 'regex', None, 'Use regular expressions. '
                             'Exact option will be ignored.'),
        ('e', 'exact', None, 'Use exact comparison. '
                             'Like comparison is used if exact is'
                             'uspecified.'),
    ]

    usage = 'hg ifind [OPTIONS] QUERY'
    ui = None
    repo = None
    opts = []

    def __init__(self):
        pass

    def __is_hit(self, query, search_string):
        opts = self.opts

        exact_comp = opts["exact"] and not opts["regex"]
        regexp_comp = opts["regex"]

        if regexp_comp:
            re_pattern = re.compile(query)
            return re_pattern.search(search_string)
        elif exact_comp:
            return query == search_string
        else:
            return query in search_string

        return False

    def __search_issues(self, query):
        ui = self.ui
        repo = self.repo
        opts = self.opts

        case_sens = opts["case_sensitive"]
        query_filter = opts["property"]

        if not case_sens:
            query = query.lower()

        hits = []

        mboxes = Artemis.get_all_mboxes(ui, repo)
        for mbox in mboxes:

            root = Artemis.find_root_key(mbox)
            # print mbox[root].get_date()
            # print mbox[root].get_info()

            search_string = mbox[root][query_filter]
            # non existing property
            if not search_string:
                continue

            if not case_sens:
                search_string = search_string.lower()

            if self.__is_hit(query, search_string):
                hits.append(mbox.issue)

        return hits

    def __show_results(self, issues):
        ui = self.ui
        repo = self.repo

        for issue in issues:
            mbox = mailbox.Maildir(issue,
                                   factory=mailbox.MaildirMessage)
            root = Artemis.find_root_key(mbox)
            # print mbox.items()
            # print mbox.keys()
            # print mbox.values()

            num_replies = str(len(mbox.keys()) - 1)
            # print mbox[root]["message-id"]
            ui.write("%s (%s) [%s]: %s\n" %
                     (
                         Artemis.get_issue_id(ui, repo, issue),
                         num_replies.rjust(3, " "),
                         mbox[root]["state"],
                         mbox[root]["subject"])
                     )

    def find(self, ui, repo, query, **opts):
        self.opts = opts
        self.ui = ui
        self.repo = repo

        issues = self.__search_issues(query)
        self.__show_results(issues)
