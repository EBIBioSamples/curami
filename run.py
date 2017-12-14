#!/usr/bin/env python
from app import app
from backend import calculations_main
import os

app.secret_key = os.urandom(24)
app.run(debug=True)
