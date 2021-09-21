#!/usr/bin/env python3

import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen
from threading import Thread
from queue import Queue


class WatchDog:
    class Server(HTTPServer):
        class RequestHandler(BaseHTTPRequestHandler):
            def __init__(self, request, client_address, server):
                BaseHTTPRequestHandler.__init__(self, request, client_address, server)
                self.server = server
            def do_POST(self):
                print('showing main window')
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
                self.server.on_show()
        def __init__(self, host, port, on_show):
            HTTPServer.__init__(self, (host, port), WatchDog.Server.RequestHandler)
            self.host = host
            self.port = port
            self.on_show = on_show
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.on_show_callback = None
    def start(self):
        try:
            self.server = WatchDog.Server(self.host, self.port, self._call_on_show)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return True
        except OSError:
            return False
    def show(self):
        print('Watchdog already running, showing previous instance')
        with urlopen(self.get_show_url(), b'') as r:
            r.read()
    def get_show_url(self):
        return 'http://{0}:{1}/'.format(self.host, self.port)
    def _call_on_show(self):
        self.on_show_callback()
    def observe(self, on_show):
        self.on_show_callback = on_show


HOST = 'localhost'
PORT = 5650
dog = WatchDog(HOST, PORT)
if not dog.start():
    dog.show()
    sys.exit()

import logging
import re
import bz2
from os import makedirs
from os.path import dirname, exists
from urllib.parse import urlparse

from subprocess import check_output
from requests import get
from bs4 import BeautifulSoup

from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QVBoxLayout,
                             QWidget, QDesktopWidget, QCompleter, QTextBrowser,
                             QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtGui import QIcon, QFont, QStandardItemModel, QKeyEvent
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QRegExp, QTimer, QObject, QEvent
from PyQt5.QtCore import pyqtSignal, pyqtSlot

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


WINDOW_WIDTH = 1300
WINDOW_HEIGHT = 800
UPDATE_DELAY = 500
ICON_FILENAME = dirname(__file__) + '/ordbok_uib_no.png'
RX_SPACES = re.compile(r'\s+')
ADD_TO_FONT_SIZE = 6

STYLE = '''
<style>
th {
    font-family: "Trebuchet MS", Verdana, Arial, Helvetica, sans-serif;
    font-weight: bold;
    color: #557FBD;
    border-right: 1px solid #557FBD;
    border-bottom: 1px solid #557FBD;
    border-top: 1px solid #557FBD;
    text-align: center;
    padding: 6px 6px 6px 12px;
}
td {
    font-family: "Trebuchet MS", Verdana, Arial, Helvetica, sans-serif;
    color: #557FBD;
    border-right: 1px solid #557FBD;
    border-bottom: 1px solid #557FBD;
    background: #fff;
    padding: 6px 6px 6px 12px;
    text-align: center;
}
</style>
'''
HTML = '''
<div id="41772"><table class="paradigmetabell" cellspacing="0" style="margin: 25px;"><tbody><tr><th class="nobgnola"><span class="grunnord">liv</span></th><th class="nola" colspan="2">Entall</th><th class="nola" colspan="2">Flertall</th></tr><tr><th class="nobg">&nbsp;&nbsp;</th><th>Ubestemt form</th><th>Bestemt form</th><th>Ubestemt form</th><th>Bestemt form</th></tr><tr id="41772_1"><td class="ledetekst">n1</td><td class="vanlig">et liv</td><td class="vanlig">livet</td><td class="vanlig">liv</td><td class="vanlig">liva</td></tr><tr id="41772_2"><td class="ledetekst">n1</td><td class="vanlig">et liv</td><td class="vanlig">livet</td><td class="vanlig">liv</td><td class="vanlig">livene</td></tr></tbody></table></div>
'''

class HttpClient:
    def get(self, url):
        logging.info('http get "%s"', url)
        result = get(url)
        result.raise_for_status()
        return result.text


class CachedHttpClient:
    def __init__(self, client, dirname):
        self.client = client
        self.dirname = dirname

    def get(self, url):
        path = self.get_path(self.get_key(url))
        content = slurp(bz2.open, path)
        if content is None:
            logging.info('cache miss: "%s"', url)
            content = self.client.get(url)
            spit(bz2.open, path, content)
        return content

    def get_path(self, key):
        return '{0}/{1}/{2}'.format(dirname(__file__), self.dirname, key)

    def cleanup(self, url):
        return re.sub(r'[^a-zA-Z0-9-_]', '', url)

    def get_key(self, url):
        parsed = urlparse(url)
        return self.cleanup(parsed.query)


def slurp(do_open, filename):
    try:
        with do_open(filename, 'rb') as file_:
            return file_.read().decode()
    except:
        return None


def spit(do_open, filename, content):
    dir = dirname(filename)
    if not exists(dir):
        makedirs(dir)
    with do_open(filename, 'wb') as file_:
        file_.write(content.encode())


class Suggestions:
    pass
    # https://ordbok.uib.no/perl/lage_ordliste_liten_nr2000.cgi?spr=bokmaal&query=gam
#
# {query:'gam',
# suggestions:["gaman","gamasje","gambe","gambier","gambisk","gambit","gamble","gambler","game","game","gamet","gametofytt","gamla","gamle-","gamleby","gamlefar","gamleheim","gamlehjem","gamlekjжreste","gamlemor","gamlen","gamlestev","gamletid","gamleеr","gamling","gamma","gammaglobulin","gammal","gammaldags","gammaldans","gammaldansk","gammaldansk","gammalengelsk","gammalgresk","gammalkjent","gammalkjжreste","gammalkommunist","gammalmannsaktig","gammalmodig","gammalnorsk","gammalnorsk","gammalost","gammalrosa","gammalstev","gammaltestamentlig","gammaltid","gammalvoren","gammastrеle","gammastrеling","gamme","gammel","gammel jomfru","gammel norsk mil","gammel som alle haugene","gammeldags","gammeldans","gammeldansk","gammeldansk","gammelengelsk","gammelgresk","gammelkjent","gammelkjжreste","gammelkommunist","gammelmannsaktig","gammelmodig","gammelnorsk","gammelnorsk","gammelost","gammelrosa","gammelstev","gammeltestamentlig","gammeltid","gammelvoren","gammen","gamp","gampe"],
# data:["gaman","gamasje","gambe","gambier","gambisk","gambit","gamble","gambler","game","game","gamet","gametofytt","gamla","gamle-","gamleby","gamlefar","gamleheim","gamlehjem","gamlekjжreste","gamlemor","gamlen","gamlestev","gamletid","gamleеr","gamling","gamma","gammaglobulin","gammal","gammaldags","gammaldans","gammaldansk","gammaldansk","gammalengelsk","gammalgresk","gammalkjent","gammalkjжreste","gammalkommunist","gammalmannsaktig","gammalmodig","gammalnorsk","gammalnorsk","gammalost","gammalrosa","gammalstev","gammaltestamentlig","gammaltid","gammalvoren","gammastrеle","gammastrеling","gamme","gammel","gammel jomfru","gammel norsk mil","gammel som alle haugene","gammeldags","gammeldans","gammeldansk","gammeldansk","gammelengelsk","gammelgresk","gammelkjent","gammelkjжreste","gammelkommunist","gammelmannsaktig","gammelmodig","gammelnorsk","gammelnorsk","gammelost","gammelrosa","gammelstev","gammeltestamentlig","gammeltid","gammelvoren","gammen","gamp","gampe"]
# }

class Inflection:
    # https://ordbok.uib.no/perl/bob_hente_paradigme.cgi?lid=41772
    #  <div id="41772"><table class="paradigmetabell" cellspacing="0" style="margin: 25px;"><tr><th class="nobgnola"><span class="grunnord">liv</span></th><th class="nola" colspan="2">Entall</th><th class="nola" colspan="2">Flertall</th></tr><tr><th class="nobg">&nbsp;&nbsp;</th><th>Ubestemt form</th><th>Bestemt form</th><th>Ubestemt form</th><th>Bestemt form</th></tr><tr id="41772_1"><td class="ledetekst">n1</td><td class="vanlig">et liv</td><td class="vanlig">livet</td><td class="vanlig">liv</td><td class="vanlig">liva</td></tr><tr id="41772_2"><td class="ledetekst">n1</td><td class="vanlig">et liv</td><td class="vanlig">livet</td><td class="vanlig">liv</td><td class="vanlig">livene</td></tr></table></div>
    def __init__(self, client, lid):
        self.lid = lid
        self.html = self.cleanup(client.get(self.get_url(lid)))

    def cleanup(self, text):
        return re.sub(r'style="margin:[^"]*"', 'style="margin: 3px;"', text)

    def get_url(self, lid):
        return 'https://ordbok.uib.no/perl/bob_hente_paradigme.cgi?lid={0}'.format(lid)

    def __repr__(self):
        return f'Inflection(lid={self.lid})'

class PartOfSpeech:
    # <span class="oppsgramordklasse" onclick="vise_fullformer(&quot;8225&quot;,'bob')">adj.</span>
    def __init__(self, client, soup):
        self.name = soup.text
        self.lid = None
        self.inflection = None
        m = re.search(r'\d+', soup['onclick'])
        if m:
            self.lid = m.group(0)
            self.inflection = Inflection(client, self.lid)

    def __repr__(self):
        return f'PartOfSpeech(name="{self.name}", lid={self.lid}, inflection={self.inflection})'


def to_text(html):
    return BeautifulSoup(html, features='lxml').text


def uniq(items, key):
    seen = set()
    return [x for x in items if not (key(x) in seen or seen.add(key(x)))]


class Article:
    def __init__(self, client, word):
        soup = BeautifulSoup(client.get(self.get_url(word)), features='lxml')
        parts = soup.find_all('span', {"class": "oppsgramordklasse"})
        parts = [PartOfSpeech(client, x) for x in parts]
        logging.info('parts: %s', parts)

        self.parts = parts
        self.html = ''.join(uniq([x.inflection.html for x in self.parts], to_text))

    def get_url(self, word: str) -> str:
        return 'https://ordbok.uib.no/perl/ordbok.cgi?OPP={0}&ant_bokmaal=5&ant_nynorsk=5&bokmaal=+&ordbok=bokmaal'.format(word)

    def __repr__(self):
        return f'Article(parts={self.parts})'
    # https://ordbok.uib.no/perl/ordbok.cgi?OPP=bra&ant_bokmaal=5&ant_nynorsk=5&bokmaal=+&ordbok=bokmaal
    # <span class="oppslagsord b" id="22720">gi</span>
    # <span class="oppsgramordklasse" onclick="vise_fullformer(&quot;8225&quot;,'bob')">adj.</span>


class FetchResult:
    def __init__(self, word, article):
        self.word = word
        self.article = article

class AsyncFetch(QObject):
    ready = pyqtSignal(FetchResult)
    def __init__(self, client):
        super(AsyncFetch, self).__init__()
        self.client = client
        self.queue = Queue()
        self.thread = Thread(target=self._serve, daemon=True)
        self.thread.start()
    def add(self, word):
        self.queue.put(word)
    def _serve(self):
        while True:
            word = self.queue.get()
            logging.info('fetch "%s"', word)
            article = Article(self.client, word)
            print(article)
            self.ready.emit(FetchResult(word, article))


class MainWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.async_fetch = AsyncFetch(CachedHttpClient(HttpClient(), 'cache'))
        self.async_fetch.ready.connect(self.on_fetch_ready)

        self.comboxBox = QComboBox(self)
        self.comboxBox.setEditable(True)
        self.comboxBox.setMaximumWidth(WINDOW_WIDTH)
        self.comboxBox.setCurrentText('')
        self.comboxBox.currentTextChanged.connect(self.onTextChanged)

        font = QFont()
        font.setPointSize(font.pointSize() + ADD_TO_FONT_SIZE)
        self.comboxBox.setFont(font)

        self.browser = QTextBrowser(self)
        self.browser.setText(STYLE + HTML)
        self.browser.setMinimumWidth(WINDOW_WIDTH)
        self.browser.setMinimumHeight(WINDOW_HEIGHT)
        self.browser.show()

        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(self.comboxBox)
        mainLayout.addWidget(self.browser)
        self.setLayout(mainLayout)

        self.setWindowTitle('OrdbokUibNo')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowIcon(QIcon(ICON_FILENAME))

        QTimer.singleShot(1, self.center)

        self.center()
        self.show()

    def activate(self):
        self.center()
        self.show()
        self.raise_()
        self.activateWindow()
        self.comboxBox.lineEdit().selectAll()
        self.comboxBox.setFocus()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def set_text(self, text):
        self.browser.setText(STYLE + text)

    def onTextChanged(self, text):
        if text != '':
            QTimer.singleShot(UPDATE_DELAY, lambda: self.update(text))

    def update(self, old_text):
        if self.same_text(old_text):
            self.fetch(old_text)

    @pyqtSlot(FetchResult)
    def on_fetch_ready(self, result: FetchResult):
        if not self.same_text(result.word):
            return
        if result.article.parts:
            self.set_text(result.article.html)

    def fetch(self, word):
        self.async_fetch.add(word)

    def onTrayActivated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()

    def same_text(self, word):
        return word == self.text()

    def text(self):
        return self.comboxBox.currentText()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.hide()
        elif (e.key() == Qt.Key_Q) and (e.modifiers() == Qt.ControlModifier):
            self.close()
        elif (e.key() == Qt.Key_L) and (e.modifiers() == Qt.ControlModifier):
            self.comboxBox.lineEdit().selectAll()
            self.comboxBox.setFocus()
        elif e.key() == Qt.Key_Return:
            self.fetch(self.text())



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(app)

    tray = QSystemTrayIcon(QIcon(dirname(__file__)+'/ordbok_uib_no.png'), app)
    menu = QMenu()
    show = QAction('Show')
    hide = QAction('Hide')
    quit = QAction('Quit')
    show.triggered.connect(window.show)
    hide.triggered.connect(window.hide)
    quit.triggered.connect(window.close)
    menu.addAction(show)
    menu.addAction(hide)
    menu.addAction(quit)
    tray.setContextMenu(menu)
    tray.activated.connect(window.onTrayActivated)
    tray.show()

    dog.observe(window.activate)

    result = app.exec()
