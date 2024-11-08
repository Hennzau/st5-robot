import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedLayout
from PyQt6.QtGui import QFont
from layout_colorwidget import Color
from functools import partial

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Happy Wheels - Livraison du plat")

        pagelayout = QVBoxLayout()
        choice_layout = QHBoxLayout()
        button_layout = QGridLayout()
        validate_layout = QHBoxLayout()

        self.vSpace = QLabel()

        # pagelayout.addWidget(self.vSpace)
        pagelayout.addLayout(choice_layout)
        # pagelayout.addWidget(self.vSpace)
        pagelayout.addLayout(button_layout)
        # pagelayout.addWidget(self.vSpace)
        pagelayout.addLayout(validate_layout)

        self.input = QLabel("Table de destination : ")
        self.input.setFont(QFont("Arial", 10))
        self.table = "À choisir"
        self.text = QLabel(self.table)
        self.text.setFont(QFont("Arial", 10))
        choice_layout.addWidget(self.input)
        choice_layout.addWidget(self.text)

        choice_layout.setContentsMargins(0,0,0,0)

        self.discard = QPushButton("Annuler")
        self.discard.pressed.connect(self.exit)
        validate_layout.addWidget(self.discard)

        self.confirm = QPushButton("Valider")
        self.discard.pressed.connect(self.close)
        validate_layout.addWidget(self.confirm)
        
        
        btn = QPushButton("0")

        for i in range(4):
            for j in range(4):
                btn = QPushButton(str (4*i+j+1))
                prsd = "table_choice" + str(4*i+j+1)
                btn.pressed.connect(partial(self.prsd, i, j))
                button_layout.addWidget(btn, i, j)

        # btn = QPushButton("1")
        # btn.pressed.connect(self.activate_tab_1)
        # button_layout.addWidget(btn, 0, 0)
        # self.stacklayout.addWidget(Color("red"))

        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    for i in range(4):
        for j in range(4):
            prsd = "table_choice" + str(4*i+j+1)
            def prsd(self,i,j):
                self.table = str(4*i+j+1)
                self.text.setText(self.table)
    
    def exit(self):
        self.table = "Opération annulée"
        self.close()



def user_input():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(400,300)
    window.show()
    app.exec()
    return window.table


print(user_input())