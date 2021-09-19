#!/usr/bin/env python

import sys
# print('EARLY')
# sys.exit(1)

import logging
import re
import bz2
from os import makedirs
from os.path import dirname, exists
from urllib.parse import urlparse

from subprocess import check_output
from requests import get
from bs4 import BeautifulSoup

#import PyQt5
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QVBoxLayout,
                             QWidget, QDesktopWidget, QCompleter, QTextBrowser,
                             QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtGui import QIcon, QFont, QStandardItemModel
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QRegExp, QTimer, QObject

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 30
MIN_HEIGHT = 500
MAX_TICKET_LEN = 6
# CANDIDATES_FILENAME = '/mnt/big_ext4/btsync/prg/completebox/rt.candidates.tsv'
# ICON_FILENAME = '/mnt/big_ext4/btsync/prg/completebox/completebox.png'
CANDIDATES_FILENAME = dirname(__file__) + '/rt.candidates.tsv'
ICON_FILENAME = dirname(__file__) + '/ordbok_uib_no.png'
RX_SPACES = re.compile(r'\s+')
ADD_TO_FONT_SIZE = 6

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


def slurp_lines(filename):
    lines = []
    with open(filename) as file_:
        for line in file_.readlines():
            # Take 2 first columns max separated by Tab
            line = ' '.join(line.strip().split('\t')[:2])
            lines.append(line)
    return lines


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
        self.html = client.get(self.get_url(lid))

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


class Article:
    def __init__(self, client, word):
        soup = BeautifulSoup(client.get(self.get_url(word)), features='lxml')
        parts = soup.find_all('span', {"class": "oppsgramordklasse"})
        parts = [PartOfSpeech(client, x) for x in parts]
        logging.info('parts: %s', parts)

        self.parts = parts

    def get_url(self, word: str) -> str:
        return 'https://ordbok.uib.no/perl/ordbok.cgi?OPP={0}&ant_bokmaal=5&ant_nynorsk=5&bokmaal=+&ordbok=bokmaal'.format(word)

    def __repr__(self):
        return f'Article(parts={self.parts})'
    # https://ordbok.uib.no/perl/ordbok.cgi?OPP=bra&ant_bokmaal=5&ant_nynorsk=5&bokmaal=+&ordbok=bokmaal
    # <span class="oppslagsord b" id="22720">gi</span>
    # <span class="oppsgramordklasse" onclick="vise_fullformer(&quot;8225&quot;,'bob')">adj.</span>

class ExactMultipartFilterModel(QSortFilterProxyModel):
    """
    This model is used to filter view by a pattern that contains words,
    separated with spaces. Each word of the pattern should be present in a row.
    """

    def __init__(self, parent):
        super(ExactMultipartFilterModel, self).__init__(parent)
        self._filteringRegExp = None

    def setFilterString(self, text):
        # pattern = text.toLower().replace(QRegExp(r"\s+"), ".*")
        pattern = RX_SPACES.sub('.*', text)
        # pattern = text.lower().replace(QRegExp(r"\s+"), ".*")
        # self._filteringRegExp = QRegExp(pattern, Qt.CaseInsensitive)
        self._filteringRegExp = re.compile(pattern, re.IGNORECASE)
        logging.info('new pattern: %s', pattern)
        self.invalidateFilter()

    def filterAcceptsRow(self, intSourceRow, sourceParent):
        if self._filteringRegExp is None:
            return False

        index0 = self.sourceModel().index(intSourceRow, 0, sourceParent)
        data = self.sourceModel().data(index0)
        # logging.info('data line: %s', data)
        # data = self.sourceModel().data(index0).toString()
        # return data.contains(self._filteringRegExp)
        found = self._filteringRegExp.search(data) != None
        # if found:
        # logging.info('found: %s', data)
        return found


class MainWindow(QWidget):
    def __init__(self, app):
        super().__init__()

        self.ticket = None
        self.app = app

        self.comboxBox = QComboBox(self)
        self.comboxBox.setEditable(True)
        #self.comboxBox.addItems(slurp_lines(CANDIDATES_FILENAME))
        self.comboxBox.setMaximumWidth(WINDOW_WIDTH)
        self.comboxBox.setCurrentText('')

        # self.custom_filter = ExactMultipartFilterModel(self)
        # self.custom_filter.setSourceModel(self.comboxBox.model())
        # self.comboxBox.lineEdit().textEdited.connect(
        #     self.custom_filter.setFilterString)

        font = QFont()
        font.setPointSize(font.pointSize() + ADD_TO_FONT_SIZE)
        self.comboxBox.setFont(font)

        # self.completer = QCompleter(self.comboxBox.model(), self.comboxBox)
        # self.completer.setModel(self.custom_filter)
        # self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        # self.completer.popup().setFont(font)
        #
        # self.comboxBox.setCompleter(self.completer)

        self.browser = QTextBrowser(self)
        self.browser.setText(HTML)
        self.browser.setMinimumHeight(MIN_HEIGHT)
        self.browser.show()

        mainLayout = QVBoxLayout(self)
        # mainLayout.addStretch(1)
        mainLayout.setSpacing(0)
        # mainLayout.setMargin(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        # mainLayout.setMar
        mainLayout.addWidget(self.comboxBox)
        mainLayout.addWidget(self.browser)
        self.setLayout(mainLayout)

        self.setWindowTitle('OrdbokUibNo')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowIcon(QIcon(ICON_FILENAME))

        QTimer.singleShot(1, self.center)

        self.center()
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def set_text(self, text):
        self.browser.setText(text)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.hide()
        elif e.key() == Qt.Key_Return:
            self.word = self.comboxBox.currentText()
            logging.info('fetch "%s"', self.word)

            client = CachedHttpClient(HttpClient(), 'cache')
            article = Article(client, self.word)
            print(article)

            if article.parts:
                first = article.parts[0]
                self.set_text(first.inflection.html)

    def onTrayActivated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()


class XdoTool:
    def get_active_window(self):
        output = check_output(['xdotool', 'getactivewindow'])
        return output.decode('utf8').strip()

    def send_text(self, window, text):
        check_output(['xdotool', 'windowfocus',
                      '--sync', window, 'type', text])


if __name__ == '__main__':
    logging.info('START')

    xdo = XdoTool()
    active_window = xdo.get_active_window()
    logging.info('active window: >%s<', active_window)

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

    result = app.exec()
