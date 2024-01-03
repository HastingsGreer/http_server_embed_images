import http.server
import contextlib
import os
import urllib
import html
import sys
import io
from http import HTTPStatus

from functools import partial
import watchdog.events
import watchdog.observers

modified_counter = 1
goto_path = None
class LambdaEventHandler(watchdog.events.FileSystemEventHandler):
    def on_any_event(self, event):
        if "package_versions.txt" in event.src_path and type(event) == watchdog.events.FileCreatedEvent:
            global goto_path
            goto_path = event.src_path.split("package_versions.txt")[0][1:]
        global modified_counter
        modified_counter += 1

handler = LambdaEventHandler()
observer = watchdog.observers.Observer()
observer.schedule(handler, ".", recursive=True)
observer.start()

class PreviewHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/lastModified":
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        goto_adendum = ",\"goto_path\":\"" + str(goto_path) + "\"" if goto_path else ""
        response = "{\"modified_counter\":" + str(modified_counter) + goto_adendum + "}"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        
        self.wfile.write(response.encode())
    def translate_path(self, path):
        global goto_path
        if path == goto_path:
            goto_path = None

        if path == "/reloader.js":
            path = __file__.split("/server.py")[0] + "/reloader.js"
        else: 
            path = super().translate_path(path)
        return path
    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(
                HTTPStatus.NOT_FOUND,
                "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path,
                                               errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = 'Directory listing for %s' % displaypath
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % enc)
        r.append('<script src=/reloader.js></script>\n')
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n<h1>%s</h1>' % title)
        r.append('<hr>\n<ul>')
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            image_extesions = [".jpg", ".png", ".gif", ".jpeg"]
            ignore_extensions = [".swp", ".swo", "__pycache__", ".ipynb_checkpoints", ".git", ".ipynb"]
            if any(name.endswith(ex) for ex in image_extesions):
                r.append('<li>%s<br><img src="%s"></li>'  
                    %(
                       html.escape(displayname, quote=False),  urllib.parse.quote(linkname,
                                          errors='surrogatepass') + "?mtime=" + str(modified_counter)))
            elif any(name.endswith(ex) for ex in ignore_extensions):
                pass
            else:
                r.append('<li><a href="%s">%s</a></li>'
                        % (urllib.parse.quote(linkname,
                                              errors='surrogatepass'),
                           html.escape(displayname, quote=False)))
        r.append('</ul>\n<hr>\n</body>\n</html>\n')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Specify alternative directory '
                        '[default:current directory]')
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    handler_class = partial(PreviewHTTPRequestHandler,
                                directory=args.directory)

    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(http.server.ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    http.server.test(
        HandlerClass=handler_class,
        ServerClass=DualStackServer,
        port=args.port,
        bind=args.bind,
    )
