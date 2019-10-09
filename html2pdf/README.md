# html2pdf

Converts a HTML file to PDF using Selenium and `chromedriver`

See `html2pdf.py -h` for help.

Currently requires Linux because of dependency on inotify to wait for file to be created.

## MathJax-enabled HTML example

```sh
html2pdf.py path/to/document.html --print-script 'MathJax.Hub.Register.StartupHook("End",function() { window.print(); });'
```
