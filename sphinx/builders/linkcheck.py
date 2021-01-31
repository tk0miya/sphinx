"""
    sphinx.builders.linkcheck
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    The CheckExternalLinksBuilder class.

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import json
import queue
import re
import socket
import threading
import time
import warnings
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from os import path
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple, cast
from urllib.parse import unquote, urlparse

from docutils import nodes
from docutils.nodes import Element
from requests import Response
from requests.exceptions import HTTPError, TooManyRedirects

from sphinx.application import Sphinx
from sphinx.builders.dummy import DummyBuilder
from sphinx.deprecation import RemovedInSphinx50Warning
from sphinx.locale import __
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import encode_uri, logging, requests
from sphinx.util.console import darkgray, darkgreen, purple, red, turquoise  # type: ignore
from sphinx.util.nodes import get_node_line

logger = logging.getLogger(__name__)

uri_re = re.compile('([a-z]+:)?//')  # matches to foo:// and // (a protocol relative URL)

Hyperlink = NamedTuple('Hyperlink', (('next_check', float),
                                     ('uri', Optional[str]),
                                     ('docname', Optional[str]),
                                     ('lineno', Optional[int])))
RateLimit = NamedTuple('RateLimit', (('delay', float), ('next_check', float)))

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
}
CHECK_IMMEDIATELY = 0
QUEUE_POLL_SECS = 1
DEFAULT_DELAY = 60.0


def node_line_or_0(node: Element) -> int:
    """
    PriorityQueue items must be comparable. The line number is part of the
    tuple used by the PriorityQueue, keep an homogeneous type for comparison.
    """
    warnings.warn('node_line_or_0() is deprecated.',
                  RemovedInSphinx50Warning, stacklevel=2)
    return get_node_line(node) or 0


class AnchorCheckParser(HTMLParser):
    """Specialized HTML parser that looks for a specific anchor."""

    def __init__(self, search_anchor: str) -> None:
        super().__init__()

        self.search_anchor = search_anchor
        self.found = False

    def handle_starttag(self, tag: Any, attrs: Any) -> None:
        for key, value in attrs:
            if key in ('id', 'name') and value == self.search_anchor:
                self.found = True
                break


def check_anchor(response: requests.requests.Response, anchor: str) -> bool:
    """Reads HTML data from a response object `response` searching for `anchor`.
    Returns True if anchor was found, False otherwise.
    """
    parser = AnchorCheckParser(anchor)
    # Read file in chunks. If we find a matching anchor, we break
    # the loop early in hopes not to have to download the whole thing.
    for chunk in response.iter_content(chunk_size=4096, decode_unicode=True):
        if isinstance(chunk, bytes):    # requests failed to decode
            chunk = chunk.decode()      # manually try to decode it

        parser.feed(chunk)
        if parser.found:
            break
    parser.close()
    return parser.found


class CheckExternalLinksBuilder(DummyBuilder):
    """
    Checks for broken external links.
    """
    name = 'linkcheck'
    epilog = __('Look for any errors in the above output or in '
                '%(outdir)s/output.txt')

    def init(self) -> None:
        self.hyperlinks = {}    # type: Dict[str, Hyperlink]
        self.to_ignore = [re.compile(x) for x in self.app.config.linkcheck_ignore]
        self.anchors_ignore = [re.compile(x)
                               for x in self.app.config.linkcheck_anchors_ignore]
        self.auth = [(re.compile(pattern), auth_info) for pattern, auth_info
                     in self.app.config.linkcheck_auth]
        self._good = set()       # type: Set[str]
        self._broken = {}        # type: Dict[str, str]
        self._redirected = {}    # type: Dict[str, Tuple[str, int]]
        # set a timeout for non-responding servers
        socket.setdefaulttimeout(5.0)

        # create queues and worker threads
        self.rate_limits = {}  # type: Dict[str, RateLimit]
        self.wqueue = queue.PriorityQueue()  # type: queue.PriorityQueue
        self.rqueue = queue.Queue()  # type: queue.Queue
        self.workers = []  # type: List[threading.Thread]
        for i in range(self.app.config.linkcheck_workers):
            thread = threading.Thread(target=self.check_thread, daemon=True)
            thread.start()
            self.workers.append(thread)

    def is_ignored_uri(self, uri: str) -> bool:
        return any(pat.match(uri) for pat in self.to_ignore)

    @property
    def good(self):
        warnings.warn(
            "%s.%s is deprecated." % (self.__class__.__name__, "good"),
            RemovedInSphinx50Warning,
            stacklevel=2,
        )
        return self._good

    @property
    def broken(self):
        warnings.warn(
            "%s.%s is deprecated." % (self.__class__.__name__, "broken"),
            RemovedInSphinx50Warning,
            stacklevel=2,
        )
        return self._broken

    @property
    def redirected(self):
        warnings.warn(
            "%s.%s is deprecated." % (self.__class__.__name__, "redirected"),
            RemovedInSphinx50Warning,
            stacklevel=2,
        )
        return self._redirected

    def check_thread(self) -> None:
        kwargs = {}
        if self.app.config.linkcheck_timeout:
            kwargs['timeout'] = self.app.config.linkcheck_timeout

        def get_request_headers() -> Dict:
            url = urlparse(uri)
            candidates = ["%s://%s" % (url.scheme, url.netloc),
                          "%s://%s/" % (url.scheme, url.netloc),
                          uri,
                          "*"]

            for u in candidates:
                if u in self.config.linkcheck_request_headers:
                    headers = dict(DEFAULT_REQUEST_HEADERS)
                    headers.update(self.config.linkcheck_request_headers[u])
                    return headers

            return {}

        def check_uri() -> Tuple[str, str, int]:
            # split off anchor
            if '#' in uri:
                req_url, anchor = uri.split('#', 1)
                for rex in self.anchors_ignore:
                    if rex.match(anchor):
                        anchor = None
                        break
            else:
                req_url = uri
                anchor = None

            # handle non-ASCII URIs
            try:
                req_url.encode('ascii')
            except UnicodeError:
                req_url = encode_uri(req_url)

            # Get auth info, if any
            for pattern, auth_info in self.auth:
                if pattern.match(uri):
                    break
            else:
                auth_info = None

            # update request headers for the URL
            kwargs['headers'] = get_request_headers()

            try:
                if anchor and self.app.config.linkcheck_anchors:
                    # Read the whole document and see if #anchor exists
                    response = requests.get(req_url, stream=True, config=self.app.config,
                                            auth=auth_info, **kwargs)
                    response.raise_for_status()
                    found = check_anchor(response, unquote(anchor))

                    if not found:
                        raise Exception(__("Anchor '%s' not found") % anchor)
                else:
                    try:
                        # try a HEAD request first, which should be easier on
                        # the server and the network
                        response = requests.head(req_url, allow_redirects=True,
                                                 config=self.app.config, auth=auth_info,
                                                 **kwargs)
                        response.raise_for_status()
                    except (HTTPError, TooManyRedirects) as err:
                        if isinstance(err, HTTPError) and err.response.status_code == 429:
                            raise
                        # retry with GET request if that fails, some servers
                        # don't like HEAD requests.
                        response = requests.get(req_url, stream=True,
                                                config=self.app.config,
                                                auth=auth_info, **kwargs)
                        response.raise_for_status()
            except HTTPError as err:
                if err.response.status_code == 401:
                    # We'll take "Unauthorized" as working.
                    return 'working', ' - unauthorized', 0
                elif err.response.status_code == 429:
                    next_check = self.limit_rate(err.response)
                    if next_check is not None:
                        self.wqueue.put((next_check, uri, docname, lineno), False)
                        return 'rate-limited', '', 0
                    return 'broken', str(err), 0
                elif err.response.status_code == 503:
                    # We'll take "Service Unavailable" as ignored.
                    return 'ignored', str(err), 0
                else:
                    return 'broken', str(err), 0
            except Exception as err:
                return 'broken', str(err), 0
            else:
                netloc = urlparse(req_url).netloc
                try:
                    del self.rate_limits[netloc]
                except KeyError:
                    pass
            if response.url.rstrip('/') == req_url.rstrip('/'):
                return 'working', '', 0
            else:
                new_url = response.url
                if anchor:
                    new_url += '#' + anchor
                # history contains any redirects, get last
                if response.history:
                    code = response.history[-1].status_code
                    return 'redirected', new_url, code
                else:
                    return 'redirected', new_url, 0

        def check(docname: str) -> Tuple[str, str, int]:
            # check for various conditions without bothering the network
            if len(uri) == 0 or uri.startswith(('#', 'mailto:', 'tel:')):
                return 'unchecked', '', 0
            elif not uri.startswith(('http:', 'https:')):
                if uri_re.match(uri):
                    # non supported URI schemes (ex. ftp)
                    return 'unchecked', '', 0
                else:
                    srcdir = path.dirname(self.env.doc2path(docname))
                    if path.exists(path.join(srcdir, uri)):
                        return 'working', '', 0
                    else:
                        self._broken[uri] = ''
                        return 'broken', '', 0
            elif uri in self._good:
                return 'working', 'old', 0
            elif uri in self._broken:
                return 'broken', self._broken[uri], 0
            elif uri in self._redirected:
                return 'redirected', self._redirected[uri][0], self._redirected[uri][1]

            # need to actually check the URI
            for _ in range(self.app.config.linkcheck_retries):
                status, info, code = check_uri()
                if status != "broken":
                    break

            if status == "working":
                self._good.add(uri)
            elif status == "broken":
                self._broken[uri] = info
            elif status == "redirected":
                self._redirected[uri] = (info, code)

            return (status, info, code)

        while True:
            next_check, uri, docname, lineno = self.wqueue.get()
            if uri is None:
                break
            netloc = urlparse(uri).netloc
            try:
                # Refresh rate limit.
                # When there are many links in the queue, workers are all stuck waiting
                # for responses, but the builder keeps queuing. Links in the queue may
                # have been queued before rate limits were discovered.
                next_check = self.rate_limits[netloc].next_check
            except KeyError:
                pass
            if next_check > time.time():
                # Sleep before putting message back in the queue to avoid
                # waking up other threads.
                time.sleep(QUEUE_POLL_SECS)
                self.wqueue.put((next_check, uri, docname, lineno), False)
                self.wqueue.task_done()
                continue
            status, info, code = check(docname)
            if status == 'rate-limited':
                logger.info(darkgray('-rate limited-   ') + uri + darkgray(' | sleeping...'))
            else:
                self.rqueue.put((uri, docname, lineno, status, info, code))
            self.wqueue.task_done()

    def limit_rate(self, response: Response) -> Optional[float]:
        next_check = None
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                # Integer: time to wait before next attempt.
                delay = float(retry_after)
            except ValueError:
                try:
                    # An HTTP-date: time of next attempt.
                    until = parsedate_to_datetime(retry_after)
                except (TypeError, ValueError):
                    # TypeError: Invalid date format.
                    # ValueError: Invalid date, e.g. Oct 52th.
                    pass
                else:
                    next_check = datetime.timestamp(until)
                    delay = (until - datetime.now(timezone.utc)).total_seconds()
            else:
                next_check = time.time() + delay
        netloc = urlparse(response.url).netloc
        if next_check is None:
            max_delay = self.app.config.linkcheck_rate_limit_timeout
            try:
                rate_limit = self.rate_limits[netloc]
            except KeyError:
                delay = DEFAULT_DELAY
            else:
                last_wait_time = rate_limit.delay
                delay = 2.0 * last_wait_time
                if delay > max_delay and last_wait_time < max_delay:
                    delay = max_delay
            if delay > max_delay:
                return None
            next_check = time.time() + delay
        self.rate_limits[netloc] = RateLimit(delay, next_check)
        return next_check

    def process_result(self, result: Tuple[str, str, int, str, str, int]) -> None:
        uri, docname, lineno, status, info, code = result

        filename = self.env.doc2path(docname, None)
        linkstat = dict(filename=filename, lineno=lineno,
                        status=status, code=code, uri=uri,
                        info=info)
        if status == 'unchecked':
            self.write_linkstat(linkstat)
            return
        if status == 'working' and info == 'old':
            self.write_linkstat(linkstat)
            return
        if lineno:
            logger.info('(line %4d) ', lineno, nonl=True)
        if status == 'ignored':
            if info:
                logger.info(darkgray('-ignored- ') + uri + ': ' + info)
            else:
                logger.info(darkgray('-ignored- ') + uri)
            self.write_linkstat(linkstat)
        elif status == 'local':
            logger.info(darkgray('-local-   ') + uri)
            self.write_entry('local', docname, filename, lineno, uri)
            self.write_linkstat(linkstat)
        elif status == 'working':
            logger.info(darkgreen('ok        ') + uri + info)
            self.write_linkstat(linkstat)
        elif status == 'broken':
            if self.app.quiet or self.app.warningiserror:
                logger.warning(__('broken link: %s (%s)'), uri, info,
                               location=(filename, lineno))
            else:
                logger.info(red('broken    ') + uri + red(' - ' + info))
            self.write_entry('broken', docname, filename, lineno, uri + ': ' + info)
            self.write_linkstat(linkstat)
        elif status == 'redirected':
            try:
                text, color = {
                    301: ('permanently', purple),
                    302: ('with Found', purple),
                    303: ('with See Other', purple),
                    307: ('temporarily', turquoise),
                    308: ('permanently', purple),
                }[code]
            except KeyError:
                text, color = ('with unknown code', purple)
            linkstat['text'] = text
            logger.info(color('redirect  ') + uri + color(' - ' + text + ' to ' + info))
            self.write_entry('redirected ' + text, docname, filename,
                             lineno, uri + ' to ' + info)
            self.write_linkstat(linkstat)
        else:
            raise ValueError("Unknown status %s." % status)

    def write_entry(self, what: str, docname: str, filename: str, line: int,
                    uri: str) -> None:
        self.txt_outfile.write("%s:%s: [%s] %s\n" % (filename, line, what, uri))

    def write_linkstat(self, data: dict) -> None:
        self.json_outfile.write(json.dumps(data))
        self.json_outfile.write('\n')

    def finish(self) -> None:
        logger.info('')

        with open(path.join(self.outdir, 'output.txt'), 'w') as self.txt_outfile,\
             open(path.join(self.outdir, 'output.json'), 'w') as self.json_outfile:
            total_links = 0
            for hyperlink in self.hyperlinks.values():
                if self.is_ignored_uri(hyperlink.uri):
                    self.process_result((hyperlink.uri, hyperlink.docname, hyperlink.lineno,
                                         'ignored', '', 0))
                else:
                    self.wqueue.put(hyperlink, False)
                    total_links += 1

            done = 0
            while done < total_links:
                self.process_result(self.rqueue.get())
                done += 1

        if self._broken:
            self.app.statuscode = 1

        self.wqueue.join()
        # Shutdown threads.
        for worker in self.workers:
            self.wqueue.put((CHECK_IMMEDIATELY, None, None, None), False)


class HyperlinkCollector(SphinxPostTransform):
    builders = ('linkcheck',)
    default_priority = 800

    def run(self, **kwargs: Any) -> None:
        builder = cast(CheckExternalLinksBuilder, self.app.builder)
        hyperlinks = builder.hyperlinks

        # reference nodes
        for refnode in self.document.traverse(nodes.reference):
            if 'refuri' not in refnode:
                continue
            uri = refnode['refuri']
            lineno = get_node_line(refnode)
            uri_info = Hyperlink(CHECK_IMMEDIATELY, uri, self.env.docname, lineno)
            if uri not in hyperlinks:
                hyperlinks[uri] = uri_info

        # image nodes
        for imgnode in self.document.traverse(nodes.image):
            uri = imgnode['candidates'].get('?')
            if uri and '://' in uri:
                lineno = get_node_line(imgnode)
                uri_info = Hyperlink(CHECK_IMMEDIATELY, uri, self.env.docname, lineno)
                if uri not in hyperlinks:
                    hyperlinks[uri] = uri_info


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_builder(CheckExternalLinksBuilder)
    app.add_post_transform(HyperlinkCollector)

    app.add_config_value('linkcheck_ignore', [], None)
    app.add_config_value('linkcheck_auth', [], None)
    app.add_config_value('linkcheck_request_headers', {}, None)
    app.add_config_value('linkcheck_retries', 1, None)
    app.add_config_value('linkcheck_timeout', None, None, [int])
    app.add_config_value('linkcheck_workers', 5, None)
    app.add_config_value('linkcheck_anchors', True, None)
    # Anchors starting with ! are ignored since they are
    # commonly used for dynamic pages
    app.add_config_value('linkcheck_anchors_ignore', ["^!"], None)
    app.add_config_value('linkcheck_rate_limit_timeout', 300.0, None)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
