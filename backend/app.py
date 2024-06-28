import webview

from server import app as server

if __name__ == "__main__":
    webview.create_window("title",  server)
    webview.start(debug=False)
