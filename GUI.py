import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtGui import QFont
from functools import partial

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Happy Wheels - Livraison du plat")

        # Main layout
        pagelayout = QVBoxLayout()
        choice_layout = QHBoxLayout()
        button_layout = QGridLayout()
        validate_layout = QHBoxLayout()

        # Label for table destination
        self.input = QLabel("Table de destination : ")
        self.input.setFont(QFont("Arial", 10))
        self.table = "À choisir"
        self.text = QLabel(self.table)
        self.text.setFont(QFont("Arial", 10))
        
        choice_layout.addWidget(self.input)
        choice_layout.addWidget(self.text)
        choice_layout.setContentsMargins(0, 0, 0, 0)

        # Discard and Confirm buttons
        self.discard = QPushButton("Annuler")
        self.discard.pressed.connect(self.exit)
        validate_layout.addWidget(self.discard)

        self.confirm = QPushButton("Valider")
        self.confirm.pressed.connect(self.close)
        validate_layout.addWidget(self.confirm)

        # Add table buttons
        for i in range(4):
            for j in range(4):
                btn = QPushButton(str(4 * i + j + 1))
                btn.pressed.connect(partial(self.select_table, 4 * i + j + 1))
                button_layout.addWidget(btn, i, j)

        # Add layouts to main layout
        pagelayout.addLayout(choice_layout)
        pagelayout.addLayout(button_layout)
        pagelayout.addLayout(validate_layout)

        # Set the central widget
        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    def select_table(self, table_number):
        """Updates the selected table label."""
        self.table = str(table_number)
        self.text.setText(self.table)

    def exit(self):
        """Sets the table to a cancel message and closes the window."""
        self.table = "Opération annulée"
        self.close()

def user_input():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(400, 300)
    window.show()
    app.exec()
    return window.table