import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6 import QtCore
from functools import partial
import zenoh

from message import NextWaypoint


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
        self.input = QLabel("Sommet de destination : ")
        self.input.setFont(QFont("Arial", 10))
        self.input.setStyleSheet("QLabel { color : #000000; }")
        self.sommet = "À sélectionner"
        self.sommet_id = (1, 1)
        self.text = QLabel(self.sommet)
        self.text.setFont(QFont("Arial", 10))
        self.text.setStyleSheet("QLabel { color : #000000; }")

        config = zenoh.Config.from_file("host_zenoh.json")
        self.session = zenoh.open(config)

        self.pub_sommet = self.session.declare_publisher("happywheels/next_waypoint")

        # Adding logo
        self.logo = QLabel(self)
        img = QPixmap("docs/src/logo_happy_wheels_GUI.png")
        # img = img.scaled(80, 80, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.logo.setPixmap(img)

        choice_layout.addWidget(self.input)
        choice_layout.addWidget(self.text)
        choice_layout.addWidget(self.logo)
        choice_layout.setContentsMargins(1, 1, 1, 1)

        # Discard and Confirm buttons
        self.discard = QPushButton("Annuler")
        self.discard.pressed.connect(self.exit)
        validate_layout.addWidget(self.discard)
        self.discard.setStyleSheet("background-color : #fc6a6a; color : #000000;")

        self.confirm = QPushButton("Valider")
        self.confirm.pressed.connect(self.send_table)
        validate_layout.addWidget(self.confirm)
        self.confirm.setStyleSheet("background-color : #85de8f; color : #000000;")

        # Return button
        self.finished = QPushButton("Plat récupéré")
        self.finished.pressed.connect(partial(self.done))
        return_layout.addWidget(self.finished)
        self.finished.setStyleSheet("background-color : #ffb2a0; color : #000000;")

        # Add table buttons
        for i in range(5):
            for j in range(5):
                btn = QPushButton( "(" + str (i + 1) + ","  + str(j + 1) + ")")
                btn.pressed.connect(partial(self.select_table, i, j))
                btn.setStyleSheet("background-color : #C5dfe0; color : #000000;")
                button_layout.addWidget(btn, i, j)

        # Add layouts to main layout
        pagelayout.addItem(
            QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        pagelayout.addLayout(choice_layout)
        pagelayout.addItem(
            QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        pagelayout.addLayout(button_layout)
        pagelayout.addItem(
            QSpacerItem(
                10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
        )
        pagelayout.addLayout(validate_layout)
        pagelayout.addItem(
            QSpacerItem(
                10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
        )
        pagelayout.addLayout(return_layout)

        # Set background color for the central widget
        widget = QWidget()
        widget.setLayout(pagelayout)
        widget.setStyleSheet("background-color : #35868c;")
        self.setCentralWidget(widget)

    def select_table(self, i, j):
        """Updates the selected table label."""
        self.sommet = "(" + str (i + 1) + ","  + str(j + 1) + ")"
        self.sommet_id = (i + 1, j + 1)
        self.text.setText(self.sommet)

    def send_table(self):
        """Sends the table to the kitchen."""

        print(self.sommet_id)
        self.pub_sommet.put(
            NextWaypoint.serialize(
                NextWaypoint(i=self.sommet_id[0], j=self.sommet_id[1])
            )
        )
        print("Table envoyée")

    def done(self):
        """Sends the table to the kitchen."""
        self.pub_sommet.put(NextWaypoint.serialize(NextWaypoint(i=1, j=1)))
        print("Retour")

    def exit(self):
        """Sets the table to a cancel message and closes the window."""
        self.sommet = "Opération annulée"
        self.close()


app = QApplication(sys.argv)
window = MainWindow()
window.resize(350, 350)
window.show()
app.exec()
