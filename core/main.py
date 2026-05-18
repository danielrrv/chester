"""
main.py
========

This module serves as the central entry point for the 'Autonomous Architect CLI' application.
It delegates to the CLI module to handle command-line interaction and task execution.
"""

import logging
import os
from dotenv import load_dotenv
from core.cli import main

load_dotenv()

# Configure logging for the entire application.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    main()
