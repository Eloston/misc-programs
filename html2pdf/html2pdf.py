#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generates a PDF of an HTML via Selenium and chromedriver"""

import argparse
from pathlib import Path

import pyinotify
from selenium import webdriver

_PRINTING_APPSTATE = Path(__file__).resolve().parent / 'printing_appstate.html2pdf.json'

def write_pdf(input_path: Path, output_dir: Path, print_script: str = 'window.print();'):
    """Writes a PDF to the same directory as the HTML document at input_path"""
    input_url = f'file://{input_path.resolve().as_posix()}'
    if output_dir:
        output_path = output_dir.resolve() / input_path.name
    else:
        output_path = input_path.resolve()
    output_path = output_path.with_suffix('.pdf')

    chrome_options = webdriver.chrome.options.Options()
    # Enable silent printing
    chrome_options.add_argument('--kiosk-printing')
    prefs = {
        # Set printing settings
        'printing.print_preview_sticky_settings.appState': _PRINTING_APPSTATE.read_text(),
        # Printing directory is the same as file saving directory
        'savefile.default_directory': str(output_path.parent),
        'savefile.type': 0,
    }
    # add_experimental_option() essentially sets a property on the underlying
    # chromeOptions object.
    # See https://chromedriver.chromium.org/capabilities under "chromeOptions object"
    # for all valid properties
    chrome_options.add_experimental_option('prefs', prefs)
    #local_state = dict()
    #chrome_options.add_experimental_option('localState', local_state)
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(input_url)

        # Remove old file
        if output_path.exists():
            output_path.unlink()

        # Setup inotify for printing
        watch_manager = pyinotify.WatchManager()
        class PrintingEventHandler(pyinotify.ProcessEvent):
            '''Exit when the output file has been written'''
            def process_IN_CLOSE(self, event):
                if event.name:
                    if event.name == output_path.name:
                        # Hack to abort loop cleanly
                        raise KeyboardInterrupt()
                    else:
                        print('DEBUG: Closed file:', event.name)
        notifier = pyinotify.Notifier(watch_manager, PrintingEventHandler())

        # Begin watching for file changes
        watch_manager.add_watch(
            str(output_path.parent),
            mask=pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CLOSE_NOWRITE,
            quiet=False,
        )

        # Print file. This is non-blocking
        driver.execute_script(print_script)

        # Block until the output file is created and written
        # This will automatically cleanup inotify once it exits
        notifier.loop()
    finally:
        # Cleanup chromedriver
        driver.quit()

# Not using Firefox because print.always_print_silent doesn't work since 58.x
#def write_pdf(input_url, output_path):
#    profile = webdriver.FirefoxProfile()
#    profile.set_preference("print.always_print_silent", True)
#    profile.set_preference("print_printer", "Print to File")
#    profile.set_preference("print.print_resolution", 600)
#    profile.set_preference("print.print_shrink_to_fit", True)
#    profile.set_preference("print.print_to_filename", str(output_path.absolute()))
#    profile.set_preference("print.print_paper_height", " 11.00")
#    profile.set_preference("print.print_paper_width", "  8.50")
#    profile.set_preference("print.print_paper_size_type", 1)
#    profile.set_preference("print.print_paper_size_unit", 0)
#    profile.set_preference("print.print_paper_name", "na_letter")
#    profile.set_preference("print.print_page_delay", 0)
#    profile.set_preference("print.save_print_settings", False)
#    profile.set_preference("print.show_print_progress", False)
#    profile.set_preference("print.show_print_progress", False)
#    #profile.set_preference("print.print_scaling", "  1.00")
#    profile.set_preference("print.print_to_file", False)
#    #profile.set_preference("print.print_footerleft", "")
#    #profile.set_preference("print.print_footerright", "")
#    #profile.set_preference("print.print_headerleft", "")
#    #profile.set_preference("print.print_headerright", "")
#    #profile.set_preference("print.print_in_color", True)
#    profile.set_preference("print.print_unwriteable_margin_bottom", 0)
#    profile.set_preference("print.print_unwriteable_margin_left", 0)
#    profile.set_preference("print.print_unwriteable_margin_right", 0)
#    profile.set_preference("print.print_unwriteable_margin_top", 0)
#    profile.set_preference("print.print_oddpages", True)
#    profile.set_preference("print.print_evenpages", True)
#    #profile.set_preference("print.print_orientation", 0)
#    #profile.set_preference("print.print_paper_data", 0)
#    # _GECKODRIVER is the path to the geckodriver binary
#    driver = webdriver.Firefox(
#        profile,  # Optional argument, if not specified will search path.
#        executable_path=str(_GECKODRIVER.absolute()),
#        service_log_path=None, # Logging for geckodriver
#    )
#    driver.get(input_url);
#    driver.execute_script("window.print();")
#    #driver.quit()

def main():
    """Entrypoint"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',
        help='Output directory path. Default is same directory as input.')
    parser.add_argument('--print-script', default='window.print();', help='JavaScript for print command')
    parser.add_argument('html_file', type=Path, help='Filesystem path to HTML file')
    args = parser.parse_args()
    if not args.html_file.exists():
        parser.error(f'HTML file does not exist: {args.html_file}')
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.exists():
            parser.error(f'Path is not a directory or does not exist: {args.output_dir}')

    write_pdf(args.html_file, output_dir, args.print_script)

if __name__ == '__main__':
    main()
