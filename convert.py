import sys
import os
import subprocess

def convert_using_win32com(input_path, output_path):
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        doc = word.Documents.Open(os.path.abspath(input_path))
        doc.SaveAs(os.path.abspath(output_path), FileFormat=17)
        doc.Close()
        word.Quit()
        return True
    except Exception as e:
        print(f"win32com failed: {e}", file=sys.stderr)
        return False

def convert_using_docx2pdf(input_path, output_path):
    try:
        from docx2pdf import convert
        convert(input_path, output_path)
        return True
    except Exception as e:
        print(f"docx2pdf failed: {e}", file=sys.stderr)
        return False

def convert_using_libreoffice(input_path, output_dir):
    try:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, os.path.abspath(input_path)], check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"LibreOffice failed: {e}", file=sys.stderr)
        return False

def main():
    input_file = "resume.docx"
    output_file = "resume.pdf"
    output_dir = "."
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found", file=sys.stderr)
        sys.exit(1)
    # 尝试 win32com
    if convert_using_win32com(input_file, output_file):
        print("Converted using win32com")
        sys.exit(0)
    # 尝试 docx2pdf
    if convert_using_docx2pdf(input_file, output_file):
        print("Converted using docx2pdf")
        sys.exit(0)
    # 尝试 LibreOffice
    if convert_using_libreoffice(input_file, output_dir):
        print("Converted using LibreOffice")
        sys.exit(0)
    print("All conversion methods failed. Please install win32com (pywin32), docx2pdf, or LibreOffice.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()