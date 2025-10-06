# The MIT License (MIT)
#
# Copyright (c) 2013, 2014 micropython-lib contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# this is a slightly modified version taken from
# https://github.com/micropython/micropython-lib/blob/master/python-ecosys/requests/requests/__init__.py

import socket


class Response:
    def __init__(self, f):
        self.raw = f
        self.encoding = "utf-8"
        self._cached = None

    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None
        self._cached = None

    @property
    def content(self):
        if self._cached is None:
            try:
                self._cached = self.raw.read()
            finally:
                self.raw.close()
                self.raw = None
        return self._cached

    @property
    def text(self):
        return str(self.content, self.encoding)

    def json(self):
        import json

        return json.loads(self.content)


def request(
    method,
    url,
    data=None,
    json=None,
    headers=None,
    stream=None,
    auth=None,
    timeout=None,
    parse_headers=True,
):
    if headers is None:
        headers = {}
    else:
        headers = headers.copy()

    redirect = None  # redirection url, None means no redirection
    chunked_data = data and getattr(data, "__next__", None) and not getattr(data, "__len__", None)

    if auth is not None:
        import binascii

        username, password = auth
        formated = b"{}:{}".format(username, password)
        formated = str(binascii.b2a_base64(formated)[:-1], "ascii")
        headers["Authorization"] = "Basic {}".format(formated)

    print("requesting", url)

    try:
        proto, dummy, host, path = url.split("/", 3)
    except ValueError:
        proto, dummy, host = url.split("/", 2)
        path = ""
    if proto == "http:":
        port = 80
    elif proto == "https:":
        import tls

        port = 443
    else:
        raise ValueError("Unsupported protocol: " + proto)

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    ai = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    ai = ai[0]

    resp_d = None
    if parse_headers is not False:
        resp_d = {}

    s = socket.socket(ai[0], socket.SOCK_STREAM, ai[2])

    if timeout is not None:
        # Note: settimeout is not supported on all platforms, will raise
        # an AttributeError if not available.
        s.settimeout(timeout)

    try:
        s.connect(ai[-1])
        if proto == "https:":
            context = tls.SSLContext(tls.PROTOCOL_TLS_CLIENT)
            context.verify_mode = tls.CERT_NONE
            s = context.wrap_socket(s, server_hostname=host)
        s.write(b"%s /%s HTTP/1.0\r\n" % (method, path))

        if "Host" not in headers:
            headers["Host"] = host

        if json is not None:
            assert data is None
            from json import dumps

            data = dumps(json)

            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        if data:
            if chunked_data:
                if "Transfer-Encoding" not in headers and "Content-Length" not in headers:
                    headers["Transfer-Encoding"] = "chunked"
            elif "Content-Length" not in headers:
                headers["Content-Length"] = str(len(data))

        if "Connection" not in headers:
            headers["Connection"] = "close"

        # Iterate over keys to avoid tuple alloc
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")

        s.write(b"\r\n")

        if data:
            if chunked_data:
                if headers.get("Transfer-Encoding", None) == "chunked":
                    for chunk in data:
                        s.write(b"%x\r\n" % len(chunk))
                        s.write(chunk)
                        s.write(b"\r\n")
                    s.write("0\r\n\r\n")
                else:
                    for chunk in data:
                        s.write(chunk)
            else:
                s.write(data)

        # this line causes stuck when this is a redirect url
        l = s.readline()

        # print(l)
        l = l.split(None, 2)
        if len(l) < 2:
            # Invalid response
            raise ValueError("HTTP error: BadStatusLine:\n%s" % l)
        status = int(l[1])
        reason = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline()
            if not l or l == b"\r\n":
                break
            # print(l)
            if l.startswith(b"Transfer-Encoding:"):
                if b"chunked" in l:
                    raise ValueError("Unsupported " + str(l, "utf-8"))
            elif l.startswith(b"Location:") and not 200 <= status <= 299:
                if status in [301, 302, 303, 307, 308]:
                    redirect = str(l[10:-2], "utf-8")
                else:
                    raise NotImplementedError("Redirect %d not yet supported" % status)
            if parse_headers is False:
                pass
            elif parse_headers is True:
                l = str(l, "utf-8")
                k, v = l.split(":", 1)
                resp_d[k] = v.strip()
            else:
                parse_headers(l, resp_d)
    except OSError:
        s.close()
        raise

    if redirect:
        if redirect[0] == '/':
            # temporal fix
            redirect = "https://sv.dut.udn.vn" + redirect

        url = redirect

        # disable redirect because it does not work properly
        redirect = None
        if status in [301, 302, 303]:
            status = 200

    if redirect:
        s.close()
        # Use the host specified in the redirect URL, as it may not be the same as the original URL.
        headers.pop("Host", None)
        if status in [301, 302, 303]:
            return request("GET", redirect, None, None, headers, stream)
        else:
            return request(method, redirect, data, json, headers, stream)
    else:
        resp = Response(s)
        resp.status_code = status
        resp.reason = reason
        resp.url = url
        if resp_d is not None:
            resp.headers = resp_d
        return resp


def head(url, **kw):
    return request("HEAD", url, **kw)


def get(url, **kw):
    return request("GET", url, **kw)


def post(url, **kw):
    return request("POST", url, **kw)


def put(url, **kw):
    return request("PUT", url, **kw)


def patch(url, **kw):
    return request("PATCH", url, **kw)


def delete(url, **kw):
    return request("DELETE", url, **kw)
