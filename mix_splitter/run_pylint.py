#!/usr/bin/env python3

# Copyright (c) 2017 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

if __name__ == "__main__":
    from pylint import epylint as lint

    lint.lint(filename="mix_splitter.py",
              options=["--disable=logging-format-interpolation",
                       "--disable=locally-disabled"])
