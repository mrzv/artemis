#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mercurial import hg, util, commands
import sys, os, time, random, mailbox, glob, socket, ConfigParser
from properties import ArtemisProperties
from artemis import Artemis

__author__ = 'frostbane'
__date__ = '2016/03/04'


class ArtemisList:
    commands = [
        ('a', 'all', False, 'list all issues (by default only those '
                            'with state new)'),
        ('p', 'property', [], 'list issues with specific field '
                              'values (e.g., -p state=fixed); '
                              'lists all possible values of a '
                              'property if no = sign'),
        ("", "all-properties", None, "list all available properties"),
        ('o', 'order', 'new', 'order of the issues; '
                              'choices: "new" (date submitted), '
                              '"latest" (date of the last message)'),
        ('d', 'date', '', 'restrict to issues matching the date '
                          '(e.g., -d ">12/28/2007)"'),
        ('f', 'filter', '', 'restrict to pre-defined filter '
                            '(in %s/%s*)'
                            '' % (Artemis.default_issues_dir,
                                  Artemis.filter_prefix))
    ]
    usage = 'hg ilist [OPTIONS]'

    def __init__(self):
        pass

    def __get_properties(self, ui, repo):
        """get the list of all available properties
        :param ui: mercurial ui object
        :param repo: mercurial repo object
        :return: returns a list of all available properties
        """

        properties = []

        mboxes = Artemis.get_all_mboxes(ui, repo)
        for mbox in mboxes:
            root = Artemis.find_root_key(mbox)
            properties = list(set(properties + mbox[root].keys()))

        return properties

    def __read_formats(self, ui):
        formats = []

        for key, value in ui.configitems('artemis'):
            if not key.startswith('format'):
                continue
            if key == 'format':
                Artemis.default_format = value
                continue
            formats.append((key.split(':')[1], value))

        return formats

    def __format_match(self, props, formats):
        for key, value in formats:
            eq = key.split('&')
            eq = [e.split('*') for e in eq]

            for e in eq:
                # todo check if else
                if props[e[0]] != e[1]:
                    break
            else:
                return value

        return Artemis.default_format

    def __summary_line(self, mbox, root, issue, formats):
        props = ArtemisProperties(mbox[root])
        props['id'] = issue
        # number of replies (-1 for self)
        props['len'] = len(mbox) - 1

        return self.__format_match(props, formats) % props

    def __find_mbox_date(self, mbox, root, order):
        if order == 'latest':
            keys = Artemis.order_keys_date(mbox)
            msg = mbox[keys[-1]]

        else:  # new
            msg = mbox[root]

        return util.parsedate(msg['date'])

    def __find_issues(self, ui, repo):
        issues_path = Artemis.get_issues_path(ui, repo)
        if not issues_path:
            return

        issues = Artemis.get_all_issues(ui, repo)

        return issues

    def __proc_filters(self, properties, ui, repo, opts):
        if opts['filter']:
            filters = glob.glob(
                os.path.join(Artemis.get_issues_path(ui, repo),
                             Artemis.filter_prefix + '*'))
            config = ConfigParser.SafeConfigParser()
            config.read(filters)
            if not config.has_section(opts['filter']):
                ui.write('No filter %s defined\n' % opts['filter'])
            else:
                properties += config.items(opts['filter'])

        return properties

    def __list_summaries(self, issues, properties, ui, repo, opts):
        # Process options
        show_all = opts['all']
        match_date, date_match = False, lambda x: True
        if opts['date']:
            match_date, date_match = True, util.matchdate(
                opts['date'])
        order = 'new'
        if opts['order']:
            order = opts['order']

        # Formats
        formats = self.__read_formats(ui)

        cmd_properties = Artemis.get_properties(opts['property'])
        list_properties = [p[0] for p in cmd_properties if
                           len(p) == 1]
        list_properties_dict = {}
        properties += filter(lambda p: len(p) > 1, cmd_properties)

        summaries = []
        for issue in issues:
            mbox = mailbox.Maildir(issue, factory=mailbox.MaildirMessage)
            root = Artemis.find_root_key(mbox)
            if not root:
                continue

            property_match = True
            for property, value in properties:
                if value:
                    property_match = property_match and (
                        mbox[root][property] == value)
                else:
                    property_match = property_match and (
                        property not in mbox[root])

            has_property = properties or \
                           mbox[root]['State'].upper() in \
                           [f.upper() for f in Artemis.state['resolved']]

            if not show_all and (not properties or
                        not property_match) and has_property:
                continue

            if match_date and not date_match(
                    util.parsedate(mbox[root]['date'])[0]):
                continue

            if not list_properties:
                mbox_date = self.__find_mbox_date(mbox, root, order)
                sum_line = self.__summary_line(
                    mbox,
                    root,
                    Artemis.get_issue_id(ui, repo, issue),
                    formats)

                summaries.append((sum_line, mbox_date))

            else:
                for lp in list_properties:
                    if lp in mbox[root]:
                        list_properties_dict\
                            .setdefault(lp, set())\
                            .add(mbox[root][lp])

        if not list_properties:
            summaries.sort(lambda (s1, d1), (s2, d2): cmp(d2, d1))
            for s, d in summaries:
                ui.write(s + '\n')

        else:
            for lp in list_properties_dict.keys():
                ui.write("%s:\n" % lp)
                for value in sorted(list_properties_dict[lp]):
                    ui.write("  %s\n" % value)

    def list(self, ui, repo, **opts):
        """List issues associated with the project"""

        # Find issues
        issues = self.__find_issues(ui, repo)
        if not issues:
            return

        properties = []
        if opts["all_properties"]:
            properties = self.__get_properties(ui, repo)
            for property in properties:
                ui.write("%s\n" % property)

            return

        # Process filter
        properties = self.__proc_filters(properties, ui, repo, opts)

        self.__list_summaries(issues, properties, ui, repo, opts)


