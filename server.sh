#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

python compile.py #& # Fork the server so we can start testing the page immediately.
