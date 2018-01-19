import logging
import sys
import re

import PyQt5
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QVBoxLayout,
                             QWidget, QDesktopWidget, QCompleter)
from PyQt5.QtGui import QIcon, QFont, QStandardItemModel
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QRegExp

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 30
MAX_TICKET_LEN = 6
RX_SPACES = re.compile(r'\s+')


def slurp_lines(filename):
    lines = []
    with open(filename) as file_:
        for line in file_.readlines():
            # Take 2 first columns max separated by Tab
            line = ' '.join(line.strip().split('\t')[:2])
            lines.append(line)
    return lines


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

        self.app = app

        self.comboxBox = QComboBox(self)
        self.comboxBox.setEditable(True)
        # self.comboxBox.setCom
        self.comboxBox.addItems(slurp_lines('./rt.candidates.tsv'))
        self.comboxBox.setMaximumWidth(WINDOW_WIDTH)
        self.comboxBox.setCurrentText('')

        # self.completer.setCaseSensitivity(Qt.CaseInsensitive)

        self.custom_filter = ExactMultipartFilterModel(self)
        self.custom_filter.setSourceModel(self.comboxBox.model())
        self.comboxBox.lineEdit().textEdited.connect(
            self.custom_filter.setFilterString)

        font = QFont()
        font.setPointSize(font.pointSize() + 10)
        self.comboxBox.setFont(font)

        self.completer = QCompleter(self.comboxBox.model(), self.comboxBox)
        self.completer.setModel(self.custom_filter)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.completer.popup().setFont(font)

        self.comboxBox.setCompleter(self.completer)

        mainLayout = QVBoxLayout(self)
        # mainLayout.addStretch(1)
        mainLayout.setSpacing(0)
        # mainLayout.setMargin(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        # mainLayout.setMar
        mainLayout.addWidget(self.comboxBox)
        self.setLayout(mainLayout)

        self.setWindowTitle('CompleteBox')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowIcon(QIcon('completebox.png'))

        self.center()
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def extractTicketNumber(self):
        return self.comboxBox.currentText()[:MAX_TICKET_LEN]

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        elif e.key() == Qt.Key_Return:
            ticket = self.extractTicketNumber()
            logging.info('ticket: %s', ticket)
            self.close()


if __name__ == '__main__':
    logging.info('START')

    app = QApplication(sys.argv)
    window = MainWindow(app)
    result = app.exec()

    logging.info('DONE: %s', result)
