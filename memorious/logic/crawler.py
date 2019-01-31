import os
import io
import yaml
import logging
from datetime import timedelta, datetime

from memorious import settings
from memorious.model import Event, Crawl, Queue
from memorious.logic.stage import CrawlerStage

log = logging.getLogger(__name__)


class Crawler(object):
    """A processing graph that constitutes a crawler."""
    SCHEDULES = {
        'hourly': timedelta(hours=1),
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(weeks=4)
    }

    def __init__(self, manager, source_file):
        self.manager = manager
        self.source_file = source_file
        with io.open(source_file, encoding='utf-8') as fh:
            self.config_yaml = fh.read()
            self.config = yaml.load(self.config_yaml)

        self.name = os.path.basename(source_file)
        self.name = self.config.get('name', self.name)
        self.description = self.config.get('description', self.name)
        self.category = self.config.get('category', 'scrape')
        self.schedule = self.config.get('schedule')
        self.disabled = self.config.get('disabled', False)
        self.init_stage = self.config.get('init', 'init')
        self.delta = Crawler.SCHEDULES.get(self.schedule)
        self.delay = int(self.config.get('delay', 0))
        self.expire = int(self.config.get('expire', settings.EXPIRE)) * 84600
        self.stealthy = self.config.get('stealthy', False)

        self.stages = {}
        for name, stage in self.config.get('pipeline', {}).items():
            self.stages[name] = CrawlerStage(self, name, stage)

    def check_due(self):
        """Check if the last execution of this crawler is older than
        the scheduled interval."""
        if self.disabled:
            return False
        if self.is_running:
            return False
        if self.delta is None:
            return False
        last_run = self.last_run
        if last_run is None:
            return True
        now = datetime.utcnow()
        if now > last_run + self.delta:
            return True
        return False

    def flush(self):
        """Delete all run-time data generated by this crawler."""
        Queue.flush(self)
        Event.delete(self)
        Crawl.flush(self)

    def flush_events(self):
        Event.delete(self)

    def cancel(self):
        Crawl.abort_all(self)
        Queue.flush(self)

    def run(self, incremental=None, run_id=None):
        """Queue the execution of a particular crawler."""
        state = {
            'crawler': self.name,
            'run_id': run_id,
            'incremental': settings.INCREMENTAL
        }
        if incremental is not None:
            state['incremental'] = incremental

        # Cancel previous runs:
        self.cancel()
        # Flush out previous events:
        Event.delete(self)
        Queue.queue(self.init_stage, state, {})

    @property
    def is_running(self):
        """Is the crawler currently running?"""
        return Queue.is_running(self)

    @property
    def last_run(self):
        return Crawl.last_run(self)

    @property
    def op_count(self):
        """Total operations performed for this crawler"""
        return Crawl.op_count(self)

    @property
    def runs(self):
        return Crawl.runs(self)

    @property
    def latest_runid(self):
        return Crawl.latest_runid(self)

    def get(self, name):
        return self.stages.get(name)

    def __str__(self):
        return self.name

    def __iter__(self):
        return iter(self.stages.values())

    def __repr__(self):
        return '<Crawler(%s)>' % self.name
