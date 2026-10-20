// Gibt den Text eines PDFs aus (für live.py). Aufruf: swift pdftext.swift datei.pdf
import PDFKit
let d = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
for i in 0..<d.pageCount { print(d.page(at: i)?.string ?? "") }
