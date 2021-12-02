from django.conf import settings
from django.db import models, transaction
from django.contrib.auth.models import User

import git
import json
from pathlib import Path
from time import sleep


# Create your models here.
class SiteInfoUpdate(models.Model):
    # Information kept for historical purposes
    user_updated = models.ForeignKey(User, on_delete=models.RESTRICT)
    datetime_updated = models.DateTimeField(auto_now=True)

    # Standard fields that we expect for every site
    site_id = models.CharField(max_length=2)
    long_name = models.CharField(max_length=32)
    release_lag = models.PositiveIntegerField(help_text='Number of days to withhold data')
    location = models.CharField(max_length=256, help_text='Where the TCCON site is located (e.g. institution, city, state/province, country)')
    contact = models.CharField(max_length=256, help_text='Point of contact for the TCCON site. Must be formatted "Name &lt;email&gt;". Separate multiple contacts with a semicolon, e.g. "Name1 &lt;email1&gt;; Name2 &lt;email2&gt;"')

    # blank = True needed to allow the form to have no input there
    site_reference = models.TextField(default='', blank=True, help_text='Citation to use for the TCCON site itself. Optional')
    data_doi = models.TextField()
    data_reference = models.TextField(default='', blank=True, help_text='Citation to use for the data from this TCCON site. Optional')
    data_revision = models.CharField(max_length=8)

    # Allow for arbitrary extra fields
    #extra_fields = models.JSONField(default=dict)

    @staticmethod
    def standard_fields():
        return ('long_name', 'release_lag', 'location', 'contact', 'site_reference',
                'data_doi', 'data_reference', 'data_revision')

    def to_dict(self):
        std_fields = {k: getattr(self, k) for k in self.standard_fields}
        #the_dict = copy(self.extra_fields)
        the_dict = dict()
        the_dict.update(std_fields)
        return the_dict


class LockManager(models.Manager):
    def execute(self, filepath, callback, delay=0):
        """Execute a callback if/when a lock on a file is acquired

        Parameters
        ----------
        filepath : str or Path
            Path to the file being written

        callback : callable
            A function that takes 0 or 1 positional arguments; if it takes one argument, it will be passed the
            lock object. This function should handle any reading/writing to the file.

        delay : int
            Number of seconds to wait before acquiring the lock. Mostly for testing.
        """
        filepath = str(Path(filepath).resolve())
        with transaction.atomic():
            while delay > 0:
                print('Waiting {} seconds'.format(delay))
                sleep(1)
                delay -= 1

            # select_for_update should block any other requests to access this row in the table
            try:
                obj = self.select_for_update().get(filepath=filepath)
            except InfoFileLocks.DoesNotExist:
                # I don't actually check locked anywhere because select_for_update should do the job of blocking
                # access. But I will keep it just to know if a file is being accessed, might be useful.
                obj = self.select_for_update().create(filepath=filepath, locked=True)
                obj.save()
            else:
                obj.locked = True
                obj.save()

            try:
                result = callback(obj)
            except TypeError:
                result = callback()

            obj.locked = False
            obj.save()
            return result


class InfoFileLocks(models.Model):
    filepath = models.TextField()
    starttime = models.DateTimeField(auto_now=True)
    locked = models.BooleanField()

    objects = LockManager()

    @classmethod
    def read_json_file(cls, json_file):
        def callback():
            with open(json_file) as f:
                return json.load(f)

        return cls.objects.execute(json_file, callback)

    @classmethod
    def write_json_file(cls, json_file, json_data, **kwargs):
        def callback():
            with open(json_file, 'w') as f:
                json.dump(json_data, f, **kwargs)

        return cls.objects.execute(json_file, callback)

    @classmethod
    def read_metadata_file(cls, metadata_file, allow_missing=True):
        def callback():
            json_file = settings.METADATA_DIR / metadata_file
            if not json_file.exists() and allow_missing:
                return dict()

            with open(json_file) as f:
                return json.load(f)

        return cls.objects.execute(settings.METADATA_DIR, callback)

    @classmethod
    def update_metadata_repo(cls, metadata_file, metadata_dict, username, **kwargs):
        # TODO: handle case where no files have changed, i.e. if the user submits the same info.
        #   Option 1: catch the GitCommandError/check if no files changed and don't commit
        #   Option 2: always change the file, i.e. have a "last updated" comment in each site. <- did this in views
        def callback():
            if has_file_changed():
                pre_commit_msg = f'Commit state of {metadata_file} before change submitted by {username}'
                commit_metadata_changes(pre_commit_msg)

            json_file = settings.METADATA_DIR / metadata_file
            with open(json_file, 'w') as f:
                json.dump(metadata_dict, f, **kwargs)

            post_commit_msg = f'Commit change to {metadata_file} submitted by {username}'
            commit_metadata_changes(post_commit_msg)

        def commit_metadata_changes(message):
            try:
                repo = git.Repo(settings.METADATA_DIR)
            except git.InvalidGitRepositoryError:
                print('WARNING: cannot commit changes to metadata; metadata directory is not a Git repo!')
                return

            repo.git.add(metadata_file)
            repo.git.commit(message=message)

        def has_file_changed():
            try:
                repo = git.Repo(settings.METADATA_DIR)
            except git.InvalidGitRepositoryError:
                print('WARNING: cannot commit changes to metadata; metadata directory is not a Git repo!')
                return

            # Difference the working directory against the index, checking for only our
            # file.
            return len(repo.index.diff(None, paths=metadata_file)) > 0

        return cls.objects.execute(settings.METADATA_DIR, callback)

