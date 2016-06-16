'''\
A tool to convert command-line tools into WSGI web applications.

A large number of CLI programs that look like this:

    def main():
        parser = argparse.ArgumentParser(...)
        args = parser.parse_args()
        mycode(args)

ArgParser lets you turn programs like these into web apps by changing a
few lines of code:

    def main():
        parser = argparse.ArgumentParser(...)
        args = argparse.Namespace()
        srv = wsgiref.simple_server.make_server(
            '', 8080, ArgParser(parser, args, mycode))

ArgParser analyzes *parser* and produces an HTML form that exposes
the same parameters.  Once that form is submitted, a copy of *args* will
be filled in and passed to *mycode*.

That's the simplist way to use this, but there are other options.  For
example, you can decide at run-time whether to run as a CLI program or a
web server by added arguments to the parser.  In that case, you will
want to remove those options from the parser before you pass it to
ArgParser.  For example:

    def main():
        parser = argparse.ArgumentParser(...)
        host_action = parser.add_argument(
            '--host', '-H', default='0.0.0.0')
        port_action = parser.add_argument(
            '--port', '-P', default=8080)
        args = parser.parse_args()
        if args.host or args.port:
            parser._remove_action(host_action)
            parser._remove_action(port_action)
            srv = wsgiref.simple_server.make_server(
                args.host, args.port, ArgParser(parser, args, mycode))
        else:
            mycode(args)

There are a few caveats, most stemming from the fact that *mycode* will
be called repeatedly. First, it should not call sys.exit().  (Someday it
will intercept the SystemExit exception, but not today.) Also, it should
clean up after itself, as any resource leaks will eventually cause the
web server to crash.
'''


from datetime import datetime
import os, sys

class WSGIdispatcher(object):
    """
    The main WSGI application. Dispatch the current request to
    the functions from above and store the regular expression
    captures in the WSGI environment as `myapp.url_args` so that
    the functions from above can access the url placeholders.

    As a convenience to developers, static files can be served by
    setting static_path to a directory.  If a matching file name can be
    found there, it is returned.  Limited support for cache control is
    provided via Last-Modified headers, however support is specifically
    excluded for multiple search directories, Etags and other cache
    control headers, and Range requests.
    
    If nothing matches, call the `not_found` function.
    """
    devfiles = set() if os.name == 'posix' else {
        'CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4',
        'LPT1', 'LPT2', 'LPT3', 'PRN', 'NUL'}

    def __init__(self, *dispatch_table, static_path=None):
        import re
        end = '' if hasattr(re, 'fullmatch') else '$'
        self.static_path = static_path
        self.dispatch_table = [
            (re.compile(pattern+end), callback)
            for pattern, callback in dispatch_table
            ]

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        path = path_info.lstrip('/')
        for regex, callback in self.dispatch_table:
            match = regex.fullmatch(path)
            if match is not None:
                environ['myapp.url_args'] = match.groups()
                return callback(environ, start_response)
        if self.static_path:
            from mimetypes import guess_type
            from os.path import join, split, splitext

            head, tail = split(path)
            root, ext = splitext(tail)
            if root.upper() in self.devfiles:
                return self.not_found(environ, start_response)
            path = join(self.static_path, tail)
            try:
                with open(path, 'rb') as myfile:
                    type, encoding = guess_type(myfile.name)
                    headers = []
                    if type:
                        headers.append(('Content-Type', type))
                    if encoding:
                        headers.append(('Content-Encoding ', encoding))
                    fs = os.fstat(myfile.fileno())
                    headers.append(('Content-Length', str(fs.st_size)))
                    if_modified_since = environ.get('HTTP_IF_MODIFIED_SINCE', '')
                    last_modified = datetime.fromtimestamp(fs.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT")
                    headers.append(('Last-Modified', last_modified))
                    if if_modified_since == last_modified:
                        start_response('304 Not Modified', headers)
                        return []
                    else:
                        start_response('200 OK', headers)
                        blksz = 65536
                        return [ myfile.read(blksz) ]

                        errors = environ['wsgi.errors']
                        if 'wsgi.file_wrapper' in environ:
##                            print('wsgi.file_wrapper', repr(myfile), file=errors)
                            return environ['wsgi.file_wrapper'](myfile, blksz)
                        else:
##                            print('iter()', repr(myfile), file=errors)
                            return iter(lambda: myfile.read(blksz), '')
            except (FileNotFoundError, IsADirectoryError, OSError):
##                print(
##                    'path = %r\nenviron = %r' % (path, environ),
##                    file=environ['wsgi.errors'])
                return self.not_found(environ, start_response)
        else:
            return self.not_found(environ, start_response)

    def not_found(self, environ, start_response):
        # per notfound.org, consider using an iframe that includes
        # https://d3o9f8o0i654j9.cloudfront.net/404/index.html
        start_response('404 Not Found', as_html)
        return [
            b'<!DOCTYPE html>',
            bytes(Html(Head(), Body(Img(alt="Not Found", src="https://http.cat/404"))))
            ]

from copy import copy
from io import StringIO
import argparse
import cgi

from htmltags import *


singular = set([None, 1, '?'])
optional = set(['?', '*'])

as_html = [('Content-Type', 'text/html')]

def popattr(*args):
    value = getattr(*args)
    try:
        delattr(*args[:2])
    except AttributeError:
        pass
    return value


class ArgParser(object):

    def __init__(self, parser, args, runapp,
                 headers=[('Content-Type', 'text/plain')],
                 skip_groups=set(),
                 submit_actions=(),
                 ):
        self.parser = parser
        self.args = args
        self.runapp = runapp
        self.skip_groups = skip_groups
        self.submit_actions = submit_actions
        self.headers = headers
        self.inputs = []
        self.outputs = []

        my_body = Body()
        my_form = Form(method='post', enctype='multipart/form-data')
        if parser.description:
            my_body += P(parser.description)
        my_body += my_form
        if parser.epilog:
            my_body += P(parser.epilog)

        for action_group in parser._action_groups:
            if not action_group._group_actions:
                continue
            if action_group.title in self.skip_groups:
                continue
            my_form += P(B(action_group.title.title())) 
            my_table = Fieldset()
            my_form += my_table 
            if action_group.description:
                my_table += P(action_group.description)
            for action in action_group._group_actions:
                try:
                    if submit_actions and isinstance(action, submit_actions):
                        continue
                    elif isinstance(action, argparse._HelpAction):
                        continue
                    elif action.nargs == 0:
                        input_tag = Input(type='checkbox')
                    elif action.choices:
                        input_tag = Select()
                        if action.nargs not in singular:
                            input_tag.setAttribute('multiple', None)
                        if action.nargs not in optional:
                            input_tag.setAttribute('required', None)
                        for option in action.choices:
                            input_tag += Option(option, value=option)
                    elif isinstance(action.type, argparse.FileType):
                        if 'r' not in action.type._mode:
                            self.outputs.append(action)
                            continue
                        self.inputs.append(action)
                        input_tag = Input(type='file')
                    else:  #if issubclass(action.type, basestring):
                        input_tag = Input(type='text')
                except TypeError as err:
                    from traceback import format_exc
                    input_tag = Pre(format_exc())
                input_tag.setAttribute('name', action.dest)
                my_table += Label(action.dest.replace('_', ' ').title(), For=action.dest)
                my_table += input_tag
                if action.help:
                    my_table += P(I(action.help))
        my_form += Input(type="submit")
        for action in submit_actions:
            my_form += Input(type="submit",
                             name=action.dest,
                             value=action.dest.title())
        self.my_doc = Html(
            Head(
                Meta(
                    name="viewport",
                    content="width=device-width, initial-scale=1")
                ),
            my_body)

    def __call__(self, environ, start_response):
        parser = self.parser
        if environ['REQUEST_METHOD'] != 'POST':
            start_response('200 OK', as_html)
            yield b'<!DOCTYPE html>'
            yield bytes(self.my_doc)
            return
        # works in Python 3, untested in Python 2
        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
        # Did the user click on a help button?
        for action in self.submit_actions:
            if action.dest in form:
                start_response('200 OK', self.headers)
                yield parser.format_help().encode()
                return
        # Only parse values that we are expecting
        new_args = copy(self.args)
        for action in self.outputs:
            setattr(new_args, action.dest, StringIO())
        for action in parser._actions:
            key = action.dest
            if key in form:
                value = form.getvalue(key)
                setattr(new_args, key, value)
        for action in self.inputs:
            input = getattr(new_args, action.dest)
            if not hasattr(input, 'read'):
                if hasattr(input, 'decode'):
                    input = input.decode()
                input = StringIO(input)
                setattr(new_args, action.dest, input)
        status_code, reason_phrase = 500, 'OK'
        try:
            assert len(self.outputs) <= 1, 'too many output files'
            if 'help' in form:
                print('help', file=new_args.output)  # TODO
                sys.exit(0)
            else:
                sys.exit(self.runapp(new_args))
        except SystemExit as err:
            if not err.code:
                start_response('200 OK', self.headers)
                for action in self.outputs:
                    output = getattr(new_args, action.dest)
                    if hasattr(output, 'getvalue'):
                        output = output.getvalue()
                    if hasattr(output, 'encode'):
                        output = output.encode()
                    yield output
                return
            status_code, reason_phrase = 400, 'Bad Request'
            tb = None
        except Exception:
            sstatus_code, reason_phrase = 500, 'Internal Server Error'
            from traceback import format_exc
            tb = format_exc()
            with open('traceback.log', 'w') as log:
                print(tb, file=log)

        start_response('%d %s' % (status_code, reason_phrase), as_html)
        yield b'<!DOCTYPE html>'
        body = Body(Img(alt=reason_phrase,
                        src="https://http.cat/%d" % status_code))
        if tb:
            body += Pre(tb)
        yield bytes(Html(Head(), body))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--i1', type=argparse.FileType('r'))
    parser.add_argument('--i2', type=argparse.FileType('r'))
    parser.add_argument('--output', type=argparse.FileType('w'))
    #parser.add_argument('--o2', type=argparse.FileType('w'))
    args = parser.parse_args()

    def mycode(args):
        import sys
        print('args =', args)
        print('success!', file=args.output)  # TODO
##        raise ZeroDivisionError()
##        sys.exit(1)

    if False:
        from wsgiref.simple_server import make_server
        srv = make_server('', 8080, ArgParser(parser, args, mycode))
        print('listening on %s:%d...' % srv.server_address)
        srv.serve_forever()
    else:
        app = ArgParser(parser, args, mycode)

        print('*** GET ***')
        for item in app({'REQUEST_METHOD': 'GET'}, print):
            print('>', item)

        class FS(dict): getvalue = dict.get
        cgi.FieldStorage = lambda **kwds: FS(i1=b'foo', i2=b'bar')

        print('*** POST ***')
        for item in app({
            'REQUEST_METHOD': 'POST',
            'wsgi.input': None,
            }, print):
            print('>', item)
