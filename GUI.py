import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QFont, QPixmap
from PyQt6 import QtCore
from functools import partial
import time

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HAPPY WHEELS - Livraison du plat")

        # Main layout
        pagelayout = QVBoxLayout()
        choice_layout = QHBoxLayout()
        button_layout = QGridLayout()
        validate_layout = QHBoxLayout()
        return_layout = QHBoxLayout()

        # Label for table destination
        self.input = QLabel("Table de destination : ")
        self.input.setFont(QFont("Arial", 10))
        self.table = "À sélectionner"
        self.t_id = (1,1)
        self.text = QLabel(self.table)
        self.text.setFont(QFont("Arial", 10))

        # Adding logo
        self.logo = QLabel(self)
        img = QPixmap('logo_happy_wheels.png')
        # img = img.scaled(80, 80, QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)
        self.logo.setPixmap(img)
        
        choice_layout.addWidget(self.input)
        choice_layout.addWidget(self.text)
        choice_layout.addWidget(self.logo)
        choice_layout.setContentsMargins(0, 0, 0, 0)

        # Discard and Confirm buttons
        self.discard = QPushButton("Annuler")
        self.discard.pressed.connect(self.exit)
        validate_layout.addWidget(self.discard)
        self.discard.setStyleSheet("background-color : #fc6a6a;")

        self.confirm = QPushButton("Valider")
        self.confirm.pressed.connect(self.close)
        validate_layout.addWidget(self.confirm)
        self.confirm.setStyleSheet("background-color : #85de8f;")

        # Return button
        self.finished = QPushButton("Plat récupéré")
        self.finished.pressed.connect(partial(self.done))
        return_layout.addWidget(self.finished)
        self.finished.setStyleSheet("background-color : #35868c;")

        # Add table buttons
        for i in range(4):
            for j in range(4):
                btn = QPushButton(str(4 * i + j + 1))
                btn.pressed.connect(partial(self.select_table, i, j))
                button_layout.addWidget(btn, i, j)

        # Add layouts to main layout
        pagelayout.addItem(QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        pagelayout.addLayout(choice_layout)
        pagelayout.addItem(QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        pagelayout.addLayout(button_layout)
        pagelayout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        pagelayout.addLayout(validate_layout)
        pagelayout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        pagelayout.addLayout(return_layout)

        # Set the central widget
        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    def select_table(self, i, j):
        """Updates the selected table label."""
        self.table = str(4 * i + j + 1)
        self.t_id = (i + 1,j + 1)
        self.text.setText(self.table)
    
    def done(self):
        self.t_id = (1, 1)
        self.close()

    def exit(self):
        """Sets the table to a cancel message and closes the window."""
        self.table = "Opération annulée"
        self.close()

def user_input():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(350, 350)
    window.show()
    app.exec()
    return (window.t_id)


print(user_input())