"""Provide the Submission class."""
from six import text_type
from six.moves.urllib.parse import (urljoin,  # pylint: disable=import-error
                                    urlparse)

from ..const import API_PATH
from .comment_forest import CommentForest
from .mixins import (EditableMixin, GildableMixin, HidableMixin,
                     ModeratableMixin, ReportableMixin, SavableMixin,
                     VotableMixin)
from .redditor import Redditor
from .subreddit import Subreddit


class Submission(EditableMixin, GildableMixin, HidableMixin, ModeratableMixin,
                 ReportableMixin, SavableMixin, VotableMixin):
    """A class for submissions to reddit."""

    _methods = (('select_flair', 'AR'),)

    @staticmethod
    def id_from_url(url):
        """Return the ID contained within a submission URL.

        :param url: A url to a submission in one of the following formats (http
            urls will also work):
            * https://redd.it/2gmzqe
            * https://reddit.com/comments/2gmzqe/
            * https://www.reddit.com/r/redditdev/comments/2gmzqe/praw_https/

        Raise ``AttributeError`` if URL is not a valid submission URL.

        """
        parsed = urlparse(url)
        if not parsed.netloc:
            raise AttributeError('Invalid URL: {}'.format(url))

        parts = parsed.path.split('/')
        if 'comments' not in parts:
            submission_id = parts[-1]
        else:
            submission_id = parts[parts.index('comments') + 1]

        if not submission_id.isalnum():
            raise AttributeError('Invalid URL: {}'.format(url))
        return submission_id

    def __init__(self, reddit, id_or_url=None):
        """Initialize a Submission instance.

        :param reddit: An instance of :class:`~.Reddit`.
        :param id_or_url: Either a reddit base64 submission ID, e.g.,
            ``2gmzqe``, or a URL supported by :meth:`~.id_from_url`.

        """
        if id_or_url.isalnum():
            submission_id = id_or_url
        else:
            submission_id = self.id_from_url(id_or_url)

        super(Submission, self).__init__(reddit, API_PATH['submission']
                                         .format(id=submission_id))
        if 'id' not in self.__dict__:
            self.id = submission_id  # pylint: disable=invalid-name

    def __unicode__(self):
        """Return a string representation of the Subreddit.

        Note: The representation is truncated to a fix number of characters.
        """
        title = self.title.replace('\r\n', ' ')
        return text_type('{0} :: {1}').format(self.score, title)

    def _transform_data(self, original_data):
        assert len(original_data) == 2
        assert len(original_data[0]['data']['children']) == 1
        data = original_data[0]['data']['children'][0]['data']

        data['author'] = Redditor.from_data(self._reddit, data['author'])
        data['comments'] = CommentForest(
            self, original_data[1]['data']['children'])
        data['subreddit'] = Subreddit(self._reddit, data['subreddit'])

        return data

    def comment(self, text):
        """Comment on the submission using the specified text.

        :returns: A Comment object for the newly created comment.

        """
        return self._reddit._add_comment(self.fullname, text)

    def get_duplicates(self, *args, **kwargs):
        """Return a get_content generator for the submission's duplicates.

        :returns: get_content generator iterating over Submission objects.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` and `object_filter` parameters
        cannot be altered.

        """
        url = self._reddit.config['duplicates'].format(
            submissionid=self.id)
        return self._reddit.get_content(url, *args, object_filter=1, **kwargs)

    def get_flair_choices(self, *args, **kwargs):
        """Return available link flair choices and current flair.

        Convenience function for
        :meth:`~.AuthenticatedReddit.get_flair_choices` populating both the
        `subreddit` and `link` parameters.

        :returns: The json response from the server.

        """
        return self.subreddit.get_flair_choices(self.fullname, *args, **kwargs)

    def mark_as_nsfw(self, unmark_nsfw=False):
        """Mark as Not Safe For Work.

        Requires that the currently authenticated user is the author of the
        submission, has the modposts oauth scope or has user/password
        authentication as a mod of the subreddit.

        :returns: The json response from the server.

        """
        url = self._reddit.config['unmarknsfw' if unmark_nsfw else 'marknsfw']
        data = {'id': self.fullname}
        return self._reddit.request_json(url, data=data)

    def set_flair(self, *args, **kwargs):
        """Set flair for this submission.

        Convenience function that utilizes :meth:`.ModFlairMixin.set_flair`
        populating both the `subreddit` and `item` parameters.

        :returns: The json response from the server.

        """
        return self.subreddit.set_flair(self, *args, **kwargs)

    def set_contest_mode(self, state=True):
        """Set 'Contest Mode' for the comments of this submission.

        Contest mode have the following effects:
          * The comment thread will default to being sorted randomly.
          * Replies to top-level comments will be hidden behind
            "[show replies]" buttons.
          * Scores will be hidden from non-moderators.
          * Scores accessed through the API (mobile apps, bots) will be
            obscured to "1" for non-moderators.

        Source for effects: https://www.reddit.com/159bww/

        :returns: The json response from the server.

        """
        url = self._reddit.config['contest_mode']
        data = {'id': self.fullname, 'state': state}
        return self._reddit.request_json(url, data=data)

    def set_suggested_sort(self, sort='blank'):
        """Set 'Suggested Sort' for the comments of the submission.

        Comments can be sorted in one of (confidence, top, new, hot,
        controversial, old, random, qa, blank).

        :returns: The json response from the server.

        """
        url = self._reddit.config['suggested_sort']
        data = {'id': self.fullname, 'sort': sort}
        return self._reddit.request_json(url, data=data)

    @property
    def short_link(self):
        """Return a short link to the submission.

        For example http://redd.it/eorhm is a short link for
        https://www.reddit.com/r/announcements/comments/eorhm/reddit_30_less_typing/.

        """
        return urljoin(self._reddit.config.short_url, self.id)

    def sticky(self, bottom=True):
        """Sticky a post in its subreddit.

        If there is already a stickied post in the designated slot it will be
        unstickied.

        :param bottom: Set this as the top or bottom sticky. If no top sticky
            exists, this submission will become the top sticky regardless.

        :returns: The json response from the server

        """
        url = self._reddit.config['sticky_submission']
        data = {'id': self.fullname, 'state': True}
        if not bottom:
            data['num'] = 1
        return self._reddit.request_json(url, data=data)

    def unmark_as_nsfw(self):
        """Mark as Safe For Work.

        :returns: The json response from the server.

        """
        return self.mark_as_nsfw(unmark_nsfw=True)

    def unset_contest_mode(self):
        """Unset 'Contest Mode' for the comments of this submission.

        Contest mode have the following effects:
          * The comment thread will default to being sorted randomly.
          * Replies to top-level comments will be hidden behind
            "[show replies]" buttons.
          * Scores will be hidden from non-moderators.
          * Scores accessed through the API (mobile apps, bots) will be
            obscured to "1" for non-moderators.

        Source for effects: http://www.reddit.com/159bww/

        :returns: The json response from the server.

        """
        return self.set_contest_mode(False)

    def unsticky(self):
        """Unsticky this post.

        :returns: The json response from the server

        """
        url = self._reddit.config['sticky_submission']
        data = {'id': self.fullname, 'state': False}
        return self._reddit.request_json(url, data=data)