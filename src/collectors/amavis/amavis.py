# coding=utf-8

"""
Collector that reports amavis metrics as reported by amavisd-agent

#### Dependencies

* amavisd-agent must be present in PATH

"""

import os
import subprocess
import re

import diamond.collector
import diamond.convertor


class AmavisCollector(diamond.collector.Collector):
    # From the source of amavisd-agent and it seems like the three interesting
    # formats are these:  ("x y/h", "xMB yMB/h", "x s y s/msg"),
    # so this, ugly as it is to hardcode it this way, it should be right.
    #
    # The other option would be to directly read and decode amavis' berkeley
    # db, and I don't even want to get there

    matchers = [
        re.compile(r'^\s*(?P<name>sysUpTime)\s+TimeTicks\s+(?P<time>\d+)\s+'
                   r'\([\w:\., ]+\)\s*$'),
        re.compile(r'^\s*(?P<name>[\w]+)\s+(?P<count>[\d]+) s\s+'
                   r'(?P<frequency>[\d.]+) s/msg\s+\([\w]+\)\s*$'),
        re.compile(r'^\s*(?P<name>[\w.-]+)\s+(?P<count>[\d]+)(MB)?\s+'
                   r'(?P<frequency>[\d.]+)(MB)?/h\s+(?P<percentage>[\d.]+) %'
                   r'\s\([\w]+\)\s*$'),
    ]

    def get_default_config_help(self):
        config_help = super(AmavisCollector, self).get_default_config_help()
        config_help.update({
            'amavisd_exe': 'The path to amavisd-agent',
        })
        return config_help

    def get_default_config(self):
        config = super(AmavisCollector, self).get_default_config()
        config.update({
            'amavisd_exe': '/usr/sbin/amavisd-agent',
        })
        return config

    def collect(self):
        """
        Collect memory stats
        """
        try:
            cmdline = [self.config['amavisd_exe'], '-c', '1']
            agent_out = subprocess.check_output(cmdline)
            lines = agent_out.strip().split(os.linesep)
            for line in lines:
                for rex in self.matchers:
                    res = rex.match(line)
                    if res:
                        groups = res.groupdict()
                        name = groups['name']
                        for metric, value in groups.items():
                            if metric == 'name':
                                continue
                            mtype = 'GAUGE'
                            if metric in ('count', 'time'):
                                mtype = 'COUNTER'
                            self.publish("{}.{}".format(name, metric),
                                         value, metric_type=mtype)

        except OSError as err:
            self.log.error("Could not run %s: %s",
                           self.config['amavisd_exe'],
                           err)
            return None

        return True
