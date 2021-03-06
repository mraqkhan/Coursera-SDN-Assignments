'''
The log window of the GUI. This presents the debugging messages generated by NOX

@author Kyriakos Zarifis
'''

from PyQt4 import QtGui, QtCore, QtSql
from sqlite3 import *
from communication import LoggerInterface, LogHandler
import Popup
import Queue
from collections import deque

class logFilter():
    '''
    Definition of a log filter
    '''
    def __init__(self, tss, comps, verbs):
        self.timestamps = tss
        self.components = comps
        self.verbosities = verbs
                
class FilterWidget(QtGui.QWidget):
    '''
    The filter widget used to set log display filter
    '''
    def __init__(self, parent=None):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)
        
        # Configure Widget
        self.tsEdit = QtGui.QLineEdit()
        self.compEdit = QtGui.QLineEdit()
        self.verbEdit = QtGui.QLineEdit()
   
        timestampBtn = QtGui.QPushButton('&Timestamp')
        timestampBtn.setStatusTip("Filter messages by timestamp")
        componentBtn = QtGui.QPushButton('&Component')
        componentBtn.setStatusTip("Filter messages by component name")
        verbosityBtn = QtGui.QPushButton('&Verbosity')
        verbosityBtn.setStatusTip("Filter messages by verbosity level")
        clearBtn = QtGui.QPushButton("Clear filter")
        clearBtn.setStatusTip("Reset filter")
        filterBtn = QtGui.QPushButton("Filter !")
        filterBtn.setStatusTip("Filter based on selected mask")
        self.scrollBtn = QtGui.QPushButton("Autoscroll")
        self.scrollBtn.setStatusTip("Toggle autoscroll to last message")
        self.scrollBtn.setCheckable(True)
        self.scrollBtn.setChecked(True)
        self.clearLogBtn = QtGui.QPushButton("Clear Log DB")
        self.clearLogBtn.setStatusTip("Panic button. Press when things get slow.")
        
        self.myVerbComboBox = Popup.VerbComboBox(self)
        
        self.connect(timestampBtn, QtCore.SIGNAL('clicked()'),
                    self.select_ts_menu)
        self.connect(componentBtn, QtCore.SIGNAL('clicked()'),
                    self.select_comp_menu)
        self.connect(verbosityBtn, QtCore.SIGNAL('clicked()'),
                    self.select_verb_menu)
        self.connect(clearBtn, QtCore.SIGNAL('clicked()'), self.clear)
        self.connect(filterBtn, QtCore.SIGNAL('clicked()'), self._filter)
        self.connect(self.scrollBtn, QtCore.SIGNAL('clicked()'), self.togglescroll)
        self.connect(self.clearLogBtn, QtCore.SIGNAL('clicked()'), self.parent.clear_log_DB)
        self.connect(self.clearLogBtn, QtCore.SIGNAL('clicked()'), self._filter)

        self.autoScroll = True

        grid = QtGui.QGridLayout()
        grid.setSpacing(1)

        grid.addWidget(timestampBtn, 1, 0)
        grid.addWidget(componentBtn, 1, 1)
        grid.addWidget(verbosityBtn, 1, 2)
        grid.addWidget(clearBtn, 1, 3)
        grid.addWidget(self.clearLogBtn, 1, 4)
        grid.addWidget(self.tsEdit, 2, 0)
        grid.addWidget(self.compEdit, 2, 1)
        grid.addWidget(self.verbEdit, 2, 2)
        grid.addWidget(filterBtn, 2, 3)
        grid.addWidget(self.scrollBtn, 2, 4)
        
        self.setLayout(grid)
        
        self.compFilt = []
        self.verbFilt = []
        
    def _filter(self):
        if not self.tsEdit.text():
            tss = None
        else:
            tss = str(self.tsEdit.text()).replace('-',' ').split(' ')
        if not self.compEdit.text():
            comps = None
        else:
            comps = str(self.compEdit.text()).replace(',','').split(' ')
        if not self.verbEdit.text():
            verbs = None
        else:
            verbs = str(self.verbEdit.text()).replace(',','').split(' ')
        self.compFilt = str(self.compEdit.text()).split()
        self.verbFilt = str(self.verbEdit.text()).split()
        f = logFilter(tss, comps, verbs)
        
        """This should be done by emitting a signal? Fix."""
        self.parent.dbWrapper.show_filtered(f)
        
    def clear(self):
        self.tsEdit.setText('')
        self.compEdit.setText('')
        self.verbEdit.setText('')
        self._filter()
        
    def togglescroll(self):
        self.scrollBtn.setChecked = not self.scrollBtn.isChecked()
        if self.scrollBtn.isChecked():
            self.autoScroll = True
        else:
            self.autoScroll = False
        
    def select_ts_menu(self):
        popup = Popup.TsComboBox(self)
        popup.exec_()
        
    def select_comp_menu(self):
        popup = Popup.CompComboBox(self)
        popup.exec_()
        
    def select_verb_menu(self):
        self.myVerbComboBox.exec_()
        
    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Enter:
            self._filter()

class LogDisplay(QtGui.QTableView):
    '''
    The panel used to display filtered log messages    
    '''
    def __init__(self, parent):
        QtGui.QListWidget.__init__(self)
        
        # Configure Widget
        self.parent = parent
        
        # Colors
        self.setStyleSheet("background-color: black; color: green")
        # Font
        #self.setFont(QtGui.QFont("Arial", 10))
        
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        
        self.setModel(self.parent.dbWrapper.model)
        #self.resizeColumnToContents(3)
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        #self.hideColumn(2)
        #self.setSelectionBehavior(self.selectRows)
        #self.setAlternatingRowColors(True)
        self.setWordWrap(True)
        #self.setStretchLastColumn(True)
        #self.setSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Preferred)
        #self.setUpdatesEnabled(False)
              
class recordCreator(QtCore.QThread):
    '''
    Thread used to read/write from/to the log database
    '''
    def __init__(self,parent,message):
        QtCore.QThread.__init__(self,parent)
        self.parent = parent
        self.m = str(message)
        
    def parse_logmsg(self):
        '''
        Parses a log message string. Expected in standard format:
        (timestamp|component|verbosity:message)
        '''
        # Strip 's and "s.
        self.m = self.m.replace("\"", "").replace("\'", "")
        split = self.m.rsplit("|")
        timestamp = split[0]
        component = split[1]
        ver_mes = split[2]
        delim = ver_mes.index(':')
        verbosity = ver_mes[0:delim]
        message = ver_mes[delim+1:len(ver_mes)]
        
        return timestamp, verbosity, component, message    
        
    def run(self):
        # Parse log message
        ts, verb, comp, msg = self.parse_logmsg()
        
        # Create record
        record = QtSql.QSqlRecord()
        record.append(QtSql.QSqlField("timestamp"))
        record.append(QtSql.QSqlField("component"))
        record.append(QtSql.QSqlField("verbosity"))
        record.append(QtSql.QSqlField("message"))
        record.setValue(0,ts)
        record.setValue(1,comp)
        record.setValue(2,verb)
        record.setValue(3,msg)
        
        # Insert record
        self.parent.insertRecordSignal.emit(record)
        
class dbWrapper(QtCore.QThread):
    
    insertRecordSignal = QtCore.pyqtSignal(object)
    logMsgRcvdSignal = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        QtCore.QThread.__init__(self)
        self.parent = parent
        
        # Connect to sqlite DB
        self.db = QtSql.QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName("log.db");
        self.db.open()
        self.q = QtSql.QSqlQuery()
        # Reset table (from last gui execution)
        self.q.exec_("DROP TABLE IF EXISTS messages") 
        self.q.exec_("CREATE TABLE messages (timestamp TEXT PRIMARY KEY, component TEXT, verbosity TEXT, message TEXT)")
        
        self.model = QtSql.QSqlTableModel(None,self.db)
        self.model.setTable('messages')
        self.model.setEditStrategy(self.model.OnManualSubmit)
        self.model.select()
        
        # Signal from recordCreator that new record is ready to be inserted
        self.insertRecordSignal.connect(self.insert_record)
        
        # Signal from logWidget that the filter has changed
        #self.filterChangedSignal.connect(self.filterChanged)
        
        '''
        # Submit to DB every 1 sec
        self.submitTimer = QtCore.QTimer()
        self.connect(self.submitTimer, QtCore.SIGNAL("timeout()"), self.model.submitAll)
        self.submitTimer.start(5000)
        '''
    def run(self):
        # Connect the logMsgRcvdSignal signal to a slot.
        self.logMsgRcvdSignal[str].connect(self.handle_message)
        
    def handle_message(self, message):
        th = recordCreator(self,message)
        th.start()
        
    def insert_record(self, r):
        self.model.insertRecord(-1,r)
        
        #self.model.submitAll()
        #self.model.select()
        if self.parent.filterWidget.autoScroll:
            self.parent.logDisplay.scrollToBottom()
        
    def show_filtered(self, logfilter):
        ''' 
        Displayes log message output filtered by given filter
        '''
        # Form SELECT
        prefix = False
        filt = ""
        if logfilter.timestamps:
            filt = filt + "("
            filt = filt + "timestamp > \'"+logfilter.timestamps[0]+"\' AND "
            filt = filt + "timestamp < \'"+logfilter.timestamps[1]+"\'"
            filt = filt + ") "
            prefix = True
        if logfilter.components:
            if prefix:
                filt = filt + "AND ("
            for comp in logfilter.components:
                filt = filt + "component=\'"+comp+"\' OR "
            filt = filt[0:len(filt)-3]
            if prefix:
                filt = filt + ")"
            prefix = True
        if logfilter.verbosities:
            if prefix:
                filt = filt + "AND ("
            for verb in logfilter.verbosities:
                filt = filt + "verbosity=\'"+verb+"\' OR "
            filt = filt[0:len(filt)-3]
            if prefix:
                filt = filt + ")"
                
        self.model.setFilter(filt)
        self.model.select()
            
class LogWidget(QtGui.QWidget):#, QtCore.QThread):
    '''
    The left panel of the GUI, which holds a logDisplay and a filterWidget
    '''    
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)  
          
        self.dbWrapper = dbWrapper(self)
        self.dbWrapper.start()
        
        self.logInterface = LoggerInterface(self)
        self.logInterface.start()
        
        
        self.filterWidget = FilterWidget(self)
        self.logDisplay = LogDisplay(self)
        
        vbox = QtGui.QVBoxLayout()
        
        vbox.addWidget(self.logDisplay)
        vbox.addWidget(self.filterWidget)

        self.setLayout(vbox)
        self.resize(300, 150)
        
	def __del__(self):
	    self.wait()
	    #self.logInterface.stop()
	    
    def clear_log_DB(self):
        '''
        Clears the log database
        '''
        self.dbWrapper.q.exec_("DELETE FROM messages")
        #self.dbWrapper.model.clear()
        #self.dbWrapper.model.select()
        
